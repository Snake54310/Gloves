"""
LeftHandKinematics.py

Kinematic model of the LEFT hand.  Structurally identical to
RightHandKinematics.py.  The gyro correction matrices (A_opt, B_opt, b_opt)
and axis remaps below are placeholders — replace them with values derived
from left-glove calibration once available.

See RightHandKinematics.py / the original HandKinematics.py for full
algorithm documentation.
"""

import numpy as np
from scipy.spatial.transform import Rotation


class Finger:
    def __init__(self, segment_lengths, has_middle_joint=True):
        self.segment_lengths  = segment_lengths
        self.has_middle_joint = has_middle_joint
        self.j1_flex = 0.0
        self.j2_flex = 0.0
        self._orientation = [0.0, 0.0, 0.0]

    def set_j1_flex(self, angle):
        self.j1_flex = angle

    def set_j2_flex(self, angle):
        if self.has_middle_joint:
            self.j2_flex = angle

    def get_j1_flex(self):
        return self.j1_flex

    def get_j2_flex(self):
        return self.j2_flex

    def set_orientation(self, x, y, z):
        self._orientation = [x, y, z]

    def get_orientation(self):
        return list(self._orientation)

    def zero_orientation(self):
        self._orientation = [0.0, 0.0, 0.0]


class LeftHand:
    """
    Kinematic model of the left hand.
    Gyro correction matrices below should be replaced with left-glove
    calibration values once available.  Currently initialised to the
    right-glove values as a neutral starting point.
    """

    def __init__(self):
        self.thumb   = Finger((1.625, 1.4375),          has_middle_joint=False)
        self.pointer = Finger((2.0,   1.25,  1.0))
        self.middle  = Finger((2.5,   1.375, 1.0))
        self.ring    = Finger((2.25,  1.375, 1.0))
        self.pinky   = Finger((1.375, 1.0,   1.0))
        self._fingers = [self.thumb, self.pointer, self.middle, self.ring, self.pinky]

        self.sample_rate = 10.0

        self._wrist_q     = Rotation.identity()
        self._wrist_euler = [0.0, 0.0, 0.0]
        self._wrist_qw    = 1.0

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

        # ---- LEFT-GLOVE gyro correction matrices ----
        # TODO: replace these with values from left-glove calibration.
        # Currently copied from the right glove as a neutral starting point.
        self._A_opt = np.array([
            [9.98791334e-01,  2.34524782e-04, -3.79903705e-04],
            [2.30295547e-04,  1.00132572e+00,  1.97823448e-03],
            [6.89860538e-04, -1.80518166e-03, -9.97348518e-01],
        ])
        self._B_opt = np.array([
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ])
        self._b_opt = np.array([-0.01162013, 0.00015419, -0.00104846])

    # ------------------------------------------------------------------ #
    # Sample rate                                                          #
    # ------------------------------------------------------------------ #

    def update_sample_rate(self, new_rate):
        self.sample_rate = new_rate

    # ------------------------------------------------------------------ #
    # Joint flex angles                                                    #
    # ------------------------------------------------------------------ #

    def set_j1_angles(self, thumb, pointer, middle, ring, pinky):
        for finger, angle in zip(self._fingers, [thumb, pointer, middle, ring, pinky]):
            finger.set_j1_flex(angle)

    def set_j2_angles(self, pointer, middle, ring, pinky):
        for finger, angle in zip(self._fingers[1:], [pointer, middle, ring, pinky]):
            finger.set_j2_flex(angle)

    def get_j1_angles(self):
        return [f.get_j1_flex() for f in self._fingers]

    def get_j2_angles(self):
        return [f.get_j2_flex() for f in self._fingers[1:]]

    # ------------------------------------------------------------------ #
    # Wrist orientation integration                                        #
    # ------------------------------------------------------------------ #

    def update_orientation(self, gyro_x, gyro_y, gyro_z):
        gyro_raw = np.array([gyro_x, gyro_y, gyro_z])
        gyro_corrected = (
            self._A_opt @ gyro_raw
            + self._B_opt @ (gyro_raw ** 2)
            + self._b_opt.flatten()
        )
        # TODO: verify axis remap sign conventions against left-glove mounting.
        gyro_body = np.array([
            -gyro_corrected[0],
            -gyro_corrected[2],
            -gyro_corrected[1],
        ])
        delta_rot = Rotation.from_rotvec(gyro_body / self.sample_rate)
        self._wrist_q = self._wrist_q * delta_rot
        euler = self._wrist_q.as_euler('zyx', degrees=True)
        self._wrist_euler = [euler[2] % 360, euler[1] % 360, euler[0] % 360]
        q = self._wrist_q.as_quat()
        self._wrist_qw = q[3]

    # ------------------------------------------------------------------ #
    # Finger orientation integration                                       #
    # ------------------------------------------------------------------ #

    def update_orientation_fingers(self,
                                   thumb_x,   thumb_y,   thumb_z,
                                   pointer_x, pointer_y, pointer_z,
                                   middle_x,  middle_y,  middle_z,
                                   ring_x,    ring_y,    ring_z,
                                   pinky_x,   pinky_y,   pinky_z):

        def integrate_finger(q, x, y, z):
            gyro_body = np.array([-y, x, z])
            delta = Rotation.from_rotvec(gyro_body / self.sample_rate)
            return q * delta

        def extract_euler(q):
            e = q.as_euler('zyx', degrees=True)
            return [e[2] % 360, e[1] % 360, e[0] % 360]

        self._thumb_q   = integrate_finger(self._thumb_q,   thumb_x,   thumb_y,   thumb_z)
        self._pointer_q = integrate_finger(self._pointer_q, pointer_x, pointer_y, pointer_z)
        self._middle_q  = integrate_finger(self._middle_q,  middle_x,  middle_y,  middle_z)
        self._ring_q    = integrate_finger(self._ring_q,    ring_x,    ring_y,    ring_z)
        self._pinky_q   = integrate_finger(self._pinky_q,   pinky_x,   pinky_y,   pinky_z)

        all_qs = [self._thumb_q, self._pointer_q, self._middle_q, self._ring_q, self._pinky_q]
        eulers = [extract_euler(q) for q in all_qs]
        (self._thumb_euler, self._pointer_euler, self._middle_euler,
         self._ring_euler,  self._pinky_euler) = eulers

        wx, wy, wz = self._wrist_euler
        for finger, euler in zip(self._fingers, eulers):
            fx, fy, fz = euler
            relative = [
                (fx - wx + 360) % 360,
                (fy + wz + 360) % 360,
                (fz - wy + 360) % 360,
            ]
            finger.set_orientation(*relative)

    # ------------------------------------------------------------------ #
    # Zero / reset                                                         #
    # ------------------------------------------------------------------ #

    def zero_orientation(self):
        self._wrist_q     = Rotation.identity()
        self._wrist_euler = [0.0, 0.0, 0.0]
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
        for finger in self._fingers:
            finger.zero_orientation()

    # ------------------------------------------------------------------ #
    # Orientation getters                                                  #
    # ------------------------------------------------------------------ #

    def get_orientation(self):
        return list(self._wrist_euler)

    def get_orientation_q(self):
        q = self._wrist_q.as_quat()
        return [q[0], q[1], q[2], q[3]]

    def get_relative_orientations(self):
        result = []
        for finger in self._fingers:
            result.extend(finger.get_orientation())
        return result

    def get_relative_orientations_q(self):
        R_remap = Rotation.from_euler('x', -90, degrees=True)
        wrist_remapped = self._wrist_q.inv() * R_remap

        def relative_q(finger_q, j1=0.0, j2=0.0):
            rel = wrist_remapped * finger_q
            flex_correction = Rotation.from_euler('x', j1 + j2, degrees=True)
            corrected = rel * flex_correction
            q = corrected.as_quat()
            return [q[0], q[1], q[2], q[3]]

        finger_qs = [self._thumb_q, self._pointer_q, self._middle_q, self._ring_q, self._pinky_q]
        result = []
        for finger, fq in zip(self._fingers, finger_qs):
            result.extend(relative_q(fq, finger.get_j1_flex(), finger.get_j2_flex()))
        return result

    def get_j0_angles(self):
        rel = self.get_relative_orientations()
        t  = rel[0:3]
        po = rel[3:6]
        m  = rel[6:9]
        r  = rel[9:12]
        pi = rel[12:15]

        def j0_x(rel_x, j1, j2=0.0):
            return (rel_x - j1 - j2 + 360) % 360

        return [
            j0_x(t[0],  self.thumb.get_j1_flex()),                                  t[1],  t[2],
            j0_x(po[0], self.pointer.get_j1_flex(), self.pointer.get_j2_flex()),     po[1], po[2],
            j0_x(m[0],  self.middle.get_j1_flex(),  self.middle.get_j2_flex()),      m[1],  m[2],
            j0_x(r[0],  self.ring.get_j1_flex(),    self.ring.get_j2_flex()),        r[1],  r[2],
            j0_x(pi[0], self.pinky.get_j1_flex(),   self.pinky.get_j2_flex()),       pi[1], pi[2],
        ]
