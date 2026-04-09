"""
HandKinematics.py

Kinematic model of the right hand. Stores joint angles and IMU-integrated
orientations for the wrist and each finger, and exposes them in forms
suitable for both the data display labels and the 3D renderer.

Classes:
    Finger      — Represents one finger: joint flex angles + relative orientation.
    RightHand   — Aggregate hand model; owns five Finger instances plus
                  wrist-level orientation integration.

Coordinate conventions:
    - Gyro values arrive here already filtered and in rad/s (wrist) or raw
      rad/s (fingers), converted upstream by SensorDataProcessor.
    - Orientations are integrated as scipy Rotation quaternions, which avoid
      gimbal lock and are compact for interpolation.
    - Euler angles are extracted in 'zyx' order (yaw-pitch-roll) and wrapped
      to [0, 360) for display.
    - Finger orientations stored in each Finger object are RELATIVE to the
      wrist: wrist Euler angles are subtracted after independent integration.
"""

import numpy as np                              # matrix/vector math for gyro correction model
from scipy.spatial.transform import Rotation   # quaternion integration and conversion


# ---------------------------------------------------------------------------
# Finger
# ---------------------------------------------------------------------------

class Finger:
    """
    Represents one finger on the hand.

    Replaces the original five near-identical classes (Thumb, Pointer, Middle,
    Ring, Pinky) with a single parameterised class. The only meaningful
    difference between the thumb and the other fingers is that the thumb has
    two segments (and therefore one fewer joint), controlled by has_middle_joint.

    Stores:
        - J1 flex angle (degrees): the proximal joint — between the palm
          knuckle and the first finger segment.
        - J2 flex angle (degrees): the middle joint — between segment 1 and 2.
          Only meaningful for the four non-thumb fingers.
        - Orientation [X, Y, Z] in degrees, relative to the wrist frame.
          Set by RightHand after computing wrist-relative Euler angles.

    Args:
        segment_lengths:    tuple of floats (inches), proximal → distal.
                            2 values for thumb, 3 values for other fingers.
        has_middle_joint:   True for pointer/middle/ring/pinky; False for thumb.
    """

    def __init__(self, segment_lengths, has_middle_joint=True):
        self.segment_lengths  = segment_lengths   # stored for reference; not used in math here
        self.has_middle_joint = has_middle_joint

        self.j1_flex = 0.0   # proximal joint angle in degrees; updated each frame
        self.j2_flex = 0.0   # middle joint angle in degrees; 0 and unused for thumb

        # Orientation of this finger relative to the wrist, in degrees [X, Y, Z].
        # Updated by RightHand.update_orientation_fingers() each frame.
        self._orientation = [0.0, 0.0, 0.0]

    # --- Joint flex ---------------------------------------------------------

    def set_j1_flex(self, angle):
        """Set the proximal joint angle (degrees)."""
        self.j1_flex = angle

    def set_j2_flex(self, angle):
        """
        Set the middle joint angle (degrees).
        Silently ignored for the thumb (has_middle_joint=False).
        """
        if self.has_middle_joint:
            self.j2_flex = angle

    def get_j1_flex(self):
        return self.j1_flex

    def get_j2_flex(self):
        return self.j2_flex   # always 0.0 for the thumb

    # --- Relative orientation -----------------------------------------------

    def set_orientation(self, x, y, z):
        """Set the finger's orientation relative to the wrist frame (degrees)."""
        self._orientation = [x, y, z]

    def get_orientation(self):
        """Return [X, Y, Z] orientation relative to the wrist (degrees)."""
        return list(self._orientation)   # return a copy to prevent external mutation

    def zero_orientation(self):
        """Reset relative orientation to [0, 0, 0] (re-zeroed from current pose)."""
        self._orientation = [0.0, 0.0, 0.0]


# ---------------------------------------------------------------------------
# RightHand
# ---------------------------------------------------------------------------

class RightHand:
    """
    Full kinematic model of the right hand.

    Responsibilities:
        1. Own five Finger instances (thumb + four fingers) with anatomically-
           proportioned segment lengths.
        2. Integrate wrist IMU gyro data into a running orientation quaternion.
        3. Integrate per-finger IMU gyro data into per-finger orientation quaternions,
           then compute each finger's orientation relative to the wrist.
        4. Expose joint angles and orientations in formats used by both the
           display labels (Euler angles) and the 3D renderer (quaternions).

    Wrist gyro correction model:
        Raw wrist gyro values are corrected for bias and cross-axis sensitivity
        before integration using a calibrated polynomial model:
            gyro_corrected = A_opt @ gyro + B_opt @ (gyro²) + b_opt
        where A_opt, B_opt, and b_opt were determined offline via optimisation
        against a reference motion capture system.

    Public interface (called by GloveMonitorWindow):
        update_sample_rate(rate)
        update_orientation(gx, gy, gz)
        update_orientation_fingers(tx, ty, tz, px, py, pz, ...)
        zero_orientation()
        get_orientation()           → [X, Y, Z] wrist Euler (deg)
        get_orientation_q()         → [x, y, z, w] wrist quaternion
        get_relative_orientations() → flat list, 3 values per finger (15 total)
        get_relative_orientations_q() → flat list, 4 values per finger (20 total)
        get_j0_angles()             → flat list, 3 values per finger (15 total)
        get_j1_angles()             → list of 5 J1 flex angles
        get_j2_angles()             → list of 4 J2 flex angles (no thumb)
        set_j1_angles(thumb, pointer, middle, ring, pinky)
        set_j2_angles(pointer, middle, ring, pinky)
    """

    def __init__(self):
        # --- Finger objects with anatomical segment lengths (inches) ---
        # Lengths are proximal → distal and were measured from the physical glove.
        self.thumb   = Finger((1.625, 1.4375),          has_middle_joint=False)
        self.pointer = Finger((2.0,   1.25,  1.0))
        self.middle  = Finger((2.5,   1.375, 1.0))
        self.ring    = Finger((2.25,  1.375, 1.0))
        self.pinky   = Finger((1.375, 1.0,   1.0))

        # Collected into a list for operations that apply uniformly to all fingers.
        self._fingers = [self.thumb, self.pointer, self.middle, self.ring, self.pinky]

        # Current sample rate estimate in Hz; updated from SensorProcessor each frame.
        # Used to scale gyro vectors when converting from angular velocity to rotation.
        self.sample_rate = 10.0

        # --- Wrist orientation state ---
        # Stored as a scipy Rotation quaternion (avoids gimbal lock) plus extracted
        # Euler angles for display. The quaternion is the ground truth; Euler is derived.
        self._wrist_q     = Rotation.identity()   # unit quaternion = no rotation
        self._wrist_euler = [0.0, 0.0, 0.0]       # [X, Y, Z] degrees, wrapped to [0, 360)
        self._wrist_qw    = 1.0                    # scalar part of quaternion, cached for renderer

        # --- Per-finger absolute orientation quaternions ---
        # Each finger has its own running quaternion, integrated independently
        # from that finger's IMU gyro. "Absolute" means relative to the lab frame,
        # not relative to the wrist — relative orientations are computed separately.
        self._thumb_q   = Rotation.identity()
        self._pointer_q = Rotation.identity()
        self._middle_q  = Rotation.identity()
        self._ring_q    = Rotation.identity()
        self._pinky_q   = Rotation.identity()

        # Per-finger absolute Euler angles [X, Y, Z] degrees.
        # Extracted from the quaternions after each integration step.
        self._thumb_euler   = [0.0, 0.0, 0.0]
        self._pointer_euler = [0.0, 0.0, 0.0]
        self._middle_euler  = [0.0, 0.0, 0.0]
        self._ring_euler    = [0.0, 0.0, 0.0]
        self._pinky_euler   = [0.0, 0.0, 0.0]

        # --- Wrist gyro polynomial correction model ---
        # Corrects for cross-axis sensitivity (A_opt), quadratic nonlinearity (B_opt),
        # and constant bias (b_opt). Determined offline via calibration optimisation.
        # Applied in update_orientation() before quaternion integration.
        self._A_opt = np.array([
            [9.98791334e-01, 2.34524782e-04, -3.79903705e-04],
             [2.30295547e-04, 1.00132572e+00,  1.97823448e-03],
            [6.89860538e-04, -1.80518166e-03, -9.97348518e-01],
        ])
        self._B_opt = np.array([
            [2.32722834e-03, -7.29753373e-04, -3.71819721e-03],
             [-1.44601592e-03, 8.47894592e-04, -3.91379674e-03],
            [2.11357366e-03, 3.44647834e-03, -2.06356445e-05],
        ])
        self._b_opt = np.array([-0.01162013, 0.00015419, -0.00104846])

    # -----------------------------------------------------------------------
    # Sample rate
    # -----------------------------------------------------------------------

    def update_sample_rate(self, new_rate):
        """
        Update the sample rate used to scale gyro integration.
        Called each frame by GloveMonitorWindow with SensorProcessor's estimate.
        The gyro rotation vector is divided by sample_rate to convert from
        angular velocity (rad/s) to a rotation angle (radians) for one time step.
        """
        self.sample_rate = new_rate

    # -----------------------------------------------------------------------
    # Joint flex angles
    # -----------------------------------------------------------------------

    def set_j1_angles(self, thumb, pointer, middle, ring, pinky):
        """
        Set the J1 (proximal) joint angle for all five fingers (degrees).
        Called each frame by GloveMonitorWindow with angles derived from
        the flex sensor polynomial conversions.
        """
        for finger, angle in zip(self._fingers, [thumb, pointer, middle, ring, pinky]):
            finger.set_j1_flex(angle)

    def set_j2_angles(self, pointer, middle, ring, pinky):
        """
        Set the J2 (middle) joint angle for the four non-thumb fingers (degrees).
        The thumb is excluded because it only has one forward joint.
        """
        for finger, angle in zip(self._fingers[1:], [pointer, middle, ring, pinky]):
            finger.set_j2_flex(angle)

    def get_j1_angles(self):
        """Return [thumb_j1, pointer_j1, middle_j1, ring_j1, pinky_j1] in degrees."""
        return [f.get_j1_flex() for f in self._fingers]

    def get_j2_angles(self):
        """Return [pointer_j2, middle_j2, ring_j2, pinky_j2] in degrees (no thumb)."""
        return [f.get_j2_flex() for f in self._fingers[1:]]

    # -----------------------------------------------------------------------
    # Wrist orientation integration
    # -----------------------------------------------------------------------

    def update_orientation(self, gyro_x, gyro_y, gyro_z):
        """
        Integrate one wrist gyro sample into the running wrist quaternion.

        Called each frame by GloveMonitorWindow with the filtered, rad/s wrist
        gyro values from SensorDataProcessor.

        Integration steps:
            1. Apply polynomial correction (A_opt, B_opt, b_opt) to remove
               cross-axis contamination and bias from the raw gyro reading.
            2. Remap axes from the IMU's physical orientation on the glove to the
               body frame convention expected by the renderer.
            3. Form a small-angle rotation vector (gyro / sample_rate) representing
               the angle rotated during one time step.
            4. Convert to a Rotation and compose (multiply) it onto the running
               quaternion. Composition = chaining rotations together over time.
            5. Extract Euler angles for the display labels.

        Args:
            gyro_x/y/z: filtered wrist gyro in rad/s (from SensorDataProcessor).
        """
        gyro_raw = np.array([gyro_x, gyro_y, gyro_z])

        # Apply polynomial correction model.
        # A_opt corrects linear cross-axis sensitivity (e.g. X rotation bleeding into Y reading).
        # B_opt corrects quadratic nonlinearity in the gyro's response.
        # b_opt corrects constant bias (non-zero output when stationary).
        gyro_corrected = (
            self._A_opt @ gyro_raw                  # linear correction
            + self._B_opt @ (gyro_raw ** 2)         # quadratic correction
            + self._b_opt.flatten()                 # bias correction
        )

        # Axis remap: reorder and negate axes so the corrected gyro aligns with
        # the body frame used by the 3D renderer. The specific signs and order
        # were determined empirically when mounting the IMU on the glove.
        gyro_body = np.array([
            -gyro_corrected[0],   # negate X
            -gyro_corrected[2],   # swap Z → Y position, and negate
            -gyro_corrected[1],   # swap Y → Z position, and negate
        ])

        # Rotation vector = angular velocity × time step.
        # Dividing by sample_rate converts rad/s into radians-per-sample.
        # Rotation.from_rotvec treats the vector's direction as the rotation axis
        # and its magnitude as the rotation angle in radians.
        delta_rot = Rotation.from_rotvec(gyro_body / self.sample_rate)

        # Compose: multiply the new small rotation onto the right of the current
        # quaternion. Right-multiplication means the new rotation is applied in
        # the body frame (the frame that's moving), which is correct for IMU integration.
        self._wrist_q = self._wrist_q * delta_rot

        # Extract Euler angles ('zyx' = yaw first, then pitch, then roll).
        # The order of the three output values from as_euler('zyx') is [yaw, pitch, roll],
        # so we index [2]=roll→X, [1]=pitch→Y, [0]=yaw→Z.
        # Wrapping to [0, 360) avoids the sign flip at ±180°.
        euler = self._wrist_q.as_euler('zyx', degrees=True)
        self._wrist_euler = [euler[2] % 360, euler[1] % 360, euler[0] % 360]

        # Cache the scalar (w) component of the quaternion for get_orientation_q().
        q = self._wrist_q.as_quat()   # scipy format: [x, y, z, w]
        self._wrist_qw = q[3]

    # -----------------------------------------------------------------------
    # Finger orientation integration
    # -----------------------------------------------------------------------

    def update_orientation_fingers(self,
                                   thumb_x,   thumb_y,   thumb_z,
                                   pointer_x, pointer_y, pointer_z,
                                   middle_x,  middle_y,  middle_z,
                                   ring_x,    ring_y,    ring_z,
                                   pinky_x,   pinky_y,   pinky_z):
        """
        Integrate one gyro sample per finger into each finger's orientation quaternion,
        then compute each finger's orientation relative to the wrist.

        Called each frame by GloveMonitorWindow with filtered gyro values.
        All inputs are in rad/s.

        Integration uses a different axis remap than the wrist:
            gyro_body = [-y, x, z]
        This remap was determined empirically for the finger IMU mounting orientation.

        Relative orientation is computed by subtracting the wrist Euler angles
        from each finger's absolute Euler angles (with an axis remap for consistency):
            relative_X = (finger_X - wrist_X) % 360
            relative_Y = (finger_Y + wrist_Z) % 360   ← note: + wrist_Z, not - wrist_Y
            relative_Z = (finger_Z - wrist_Y) % 360
        The mixed signs reflect the axis remapping between the wrist and finger
        IMU mounting orientations.
        """

        def integrate_finger(q, x, y, z):
            """
            Integrate one angular velocity sample into quaternion q.
            Axis remap for finger IMUs: gyro_body = [-y, x, z].
            """
            gyro_body = np.array([-y, x, z])                        # finger-specific axis remap
            delta = Rotation.from_rotvec(gyro_body / self.sample_rate)  # angle for one time step
            return q * delta                                          # compose onto running quaternion

        def extract_euler(q):
            """
            Extract Euler angles from quaternion q, wrapped to [0, 360).
            Returns [X, Y, Z] in degrees.
            """
            e = q.as_euler('zyx', degrees=True)   # returns [yaw, pitch, roll]
            return [e[2] % 360, e[1] % 360, e[0] % 360]   # reorder to [X, Y, Z]

        # Integrate each finger's quaternion independently.
        self._thumb_q   = integrate_finger(self._thumb_q,   thumb_x,   thumb_y,   thumb_z)
        self._pointer_q = integrate_finger(self._pointer_q, pointer_x, pointer_y, pointer_z)
        self._middle_q  = integrate_finger(self._middle_q,  middle_x,  middle_y,  middle_z)
        self._ring_q    = integrate_finger(self._ring_q,    ring_x,    ring_y,    ring_z)
        self._pinky_q   = integrate_finger(self._pinky_q,   pinky_x,   pinky_y,   pinky_z)

        all_qs = [self._thumb_q, self._pointer_q, self._middle_q, self._ring_q, self._pinky_q]

        # Extract absolute Euler angles for all fingers in one pass.
        eulers = [extract_euler(q) for q in all_qs]
        (self._thumb_euler, self._pointer_euler, self._middle_euler,
         self._ring_euler,  self._pinky_euler) = eulers

        # Compute relative orientation for each finger and store it in the Finger object.
        wx, wy, wz = self._wrist_euler   # wrist Euler angles for subtraction
        for finger, euler in zip(self._fingers, eulers):
            fx, fy, fz = euler
            relative = [
                (fx - wx + 360) % 360,   # finger X relative to wrist X
                (fy + wz + 360) % 360,   # finger Y relative to wrist Z (axis remap)
                (fz - wy + 360) % 360,   # finger Z relative to wrist Y (axis remap)
            ]
            finger.set_orientation(*relative)

    # -----------------------------------------------------------------------
    # Zero / reset
    # -----------------------------------------------------------------------

    def zero_orientation(self):
        """
        Reset all wrist and finger quaternions to identity.

        This re-zeroes the orientation reference frame from the hand's current
        physical pose. After calling this, all subsequent orientations are
        expressed relative to the pose at the moment of zeroing.
        Called when the user presses the "Zero Gyro" button.
        """
        # Reset wrist quaternion and derived values
        self._wrist_q     = Rotation.identity()
        self._wrist_euler = [0.0, 0.0, 0.0]

        # Reset all finger quaternions and their derived Euler angles
        self._thumb_q   = Rotation.identity()
        self._pointer_q = Rotation.identity()
        self._middle_q  = Rotation.identity()
        self._ring_q    = Rotation.identity()
        self._pinky_q   = Rotation.identity()

        self._thumb_euler   = [0.0, 0.0, 0.0]
        self._pointer_euler = [0.0, 0.0, 0.0]
        self._middle_euler  = [0.0, 0.0, 0.0]
        self._ring_euler    = [0.0, 0.0, 0.0]
        self._pinky_euler   = [0.0, 0.0, 0.0]

        # Reset relative orientations stored in each Finger object
        for finger in self._fingers:
            finger.zero_orientation()

    # -----------------------------------------------------------------------
    # Orientation getters
    # -----------------------------------------------------------------------

    def get_orientation(self):
        """
        Return the wrist's current orientation as [X, Y, Z] in degrees,
        wrapped to [0, 360). Used by the Wrist view display labels.
        """
        return list(self._wrist_euler)

    def get_orientation_q(self):
        """
        Return the wrist's current orientation as a quaternion [x, y, z, w].
        Used by HandRenderer.setOrientationPalm() to rotate the entire 3D hand.
        """
        q = self._wrist_q.as_quat()   # scipy format: [x, y, z, w]
        return [q[0], q[1], q[2], q[3]]

    def get_relative_orientations(self):
        """
        Return all five fingers' relative orientations as a flat list of 15 values:
        [thumb_X, thumb_Y, thumb_Z, pointer_X, ..., pinky_Z].
        Used internally by get_j0_angles() and get_relative_orientations_q().
        """
        result = []
        for finger in self._fingers:
            result.extend(finger.get_orientation())   # extend adds 3 values per finger
        return result

    def get_relative_orientations_q(self):
        """
        Return per-finger orientations relative to the wrist as quaternions,
        with each finger's forward-joint flex correction applied.

        Returns a flat list of 20 values: [x, y, z, w] × 5 fingers,
        in order thumb → pointer → middle → ring → pinky.

        Used by HandRenderer.setOrientationFingers() to orient each finger's
        proximal segment independently (capturing abduction/adduction).

        The wrist quaternion is inverted and composed with a -90° X rotation
        to align the HandKinematics coordinate frame with the Qt3D scene frame.
        Each finger's J1+J2 flex is then removed as a correction so the proximal
        segment only shows base rotation, not the fold from forward joints.
        """
        # Build the reference frame transform: wrist_inv composed with a -90° X offset.
        # This converts from "orientation relative to lab frame" to
        # "orientation relative to the back of the hand in the 3D scene".
        R_remap = Rotation.from_euler('x', -90, degrees=True)
        wrist_remapped = self._wrist_q.inv() * R_remap

        def relative_q(finger_q, j1=0.0, j2=0.0):
            """
            Compute the proximal-segment quaternion for one finger.

            Args:
                finger_q: the finger's absolute orientation quaternion.
                j1, j2:   the finger's known forward-joint flex angles (degrees).
                           These are subtracted so the proximal transform only
                           represents base rotation (J0).
            """
            rel = wrist_remapped * finger_q   # finger orientation in wrist-relative frame
            # Remove the cumulative forward-joint flex from the orientation.
            # Without this, the proximal segment would "double-count" the curl
            # that's already represented by the middle/distal segment transforms.
            flex_correction = Rotation.from_euler('x', j1 + j2, degrees=True)
            corrected = rel * flex_correction
            q = corrected.as_quat()   # [x, y, z, w]
            return [q[0], q[1], q[2], q[3]]

        finger_qs = [self._thumb_q, self._pointer_q, self._middle_q, self._ring_q, self._pinky_q]
        result = []
        for finger, fq in zip(self._fingers, finger_qs):
            # Pass each finger's J1 and J2 for flex correction.
            # Thumb's J2 is always 0 (has_middle_joint=False), which is harmless.
            result.extend(relative_q(fq, finger.get_j1_flex(), finger.get_j2_flex()))
        return result

    def get_j0_angles(self):
        """
        Compute the base-segment (metacarpal / J0) rotation angles for each finger.

        The J0 angle represents how far the base segment has rotated relative to
        the wrist plane — this is the component of finger orientation that is NOT
        accounted for by the forward joints (J1 and J2).

        Derivation:
            The finger's integrated relative orientation represents the total
            rotation of the distal segment in the wrist frame. The total rotation
            equals J0 + J1 + J2 (assuming all joints rotate around the same axis).
            Therefore: J0_X = relative_X - J1 - J2.
            The Y and Z components are passed through unchanged (they represent
            side-to-side and twist motion which are not decomposed further here).

        Returns a flat list of 15 values: [X, Y, Z] per finger × 5 fingers,
        in the same order as get_relative_orientations().
        """
        rel = self.get_relative_orientations()

        # Unpack the flat list into per-finger 3-tuples for readability.
        t  = rel[0:3]    # thumb
        po = rel[3:6]    # pointer
        m  = rel[6:9]    # middle
        r  = rel[9:12]   # ring
        pi = rel[12:15]  # pinky

        def j0_x(rel_x, j1, j2=0.0):
            """Subtract forward-joint flex from relative X to isolate base rotation."""
            return (rel_x - j1 - j2 + 360) % 360   # +360 before % prevents negative results

        # Build the result: for each finger, J0_X is computed; Y and Z pass through.
        result = [
            j0_x(t[0],  self.thumb.get_j1_flex()),                                     t[1],  t[2],
            j0_x(po[0], self.pointer.get_j1_flex(), self.pointer.get_j2_flex()),        po[1], po[2],
            j0_x(m[0],  self.middle.get_j1_flex(),  self.middle.get_j2_flex()),         m[1],  m[2],
            j0_x(r[0],  self.ring.get_j1_flex(),    self.ring.get_j2_flex()),           r[1],  r[2],
            j0_x(pi[0], self.pinky.get_j1_flex(),   self.pinky.get_j2_flex()),          pi[1], pi[2],
        ]
        return result
