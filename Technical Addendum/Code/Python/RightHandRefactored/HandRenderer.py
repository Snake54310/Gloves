"""
HandRenderer.py

Qt3D-based 3D rendering of the right hand. Displays a simplified cylindrical
model of the palm and five fingers, updated in real time with joint angles
and IMU-derived orientations supplied by GloveMonitorWindow each frame.

The scene is built as a hierarchy of Qt3D entities. Child entities inherit
their parent's transform, so rotating the palm automatically moves all fingers,
and rotating a proximal segment automatically moves the middle and distal segments
attached to it.

Coordinate system conventions:
    - Z is up in this scene (camera upVector = (0, 0, 1)).
    - Qt3D cylinders are created along the Y axis by default.
    - The palm cylinder's rest rotation is +90° around X, tipping it so its
      flat face (the back of the hand) points upward (+Z).
    - Finger proximal segments are parented to the palm and given a -90° X
      rotation at rest, so they extend forward (+Z from the palm face).
    - Finger curl (flex) is applied as a rotation around the -X axis on the
      middle and distal segment transforms. Positive angle = curls toward palm.
    - setOrientationPalm applies a +90° X offset before applying the incoming
      quaternion, to align the HandKinematics coordinate frame with this scene frame.

Public interface (called by GloveMonitorWindow each animation frame):
    setAnglesPointer(middle_angle, distal_angle)
    setAnglesMiddle(middle_angle, distal_angle)
    setAnglesRing(middle_angle, distal_angle)
    setAnglesPinky(middle_angle, distal_angle)
    setAngleThumb(distal_angle)
    setOrientationPalm(qx, qy, qz, qw)
    setOrientationFingers(j0AnglesQ)
    show()
    close()
"""

from PySide6.Qt3DCore import Qt3DCore
from PySide6.Qt3DExtras import Qt3DExtras
from PySide6.Qt3DRender import Qt3DRender
from PySide6.QtGui import QColor, QVector3D, QQuaternion


class AnimationWindow(Qt3DExtras.Qt3DWindow):
    """
    Qt3DWindow subclass that renders a simplified right-hand model.

    Scene entity hierarchy:
        rootEntity
        └── entity_Palm  (flat cylinder = back of hand)
            ├── proximal_Pointer → middle_Pointer → distal_Pointer
            ├── proximal_Middle  → middle_Middle  → distal_Middle
            ├── proximal_Ring    → middle_Ring    → distal_Ring
            ├── proximal_Pinky   → middle_Pinky   → distal_Pinky
            └── proximal_Thumb   → distal_Thumb   (no middle segment)

    Parenting all finger proximal entities to entity_Palm means the entire
    hand rotates as a unit when setOrientationPalm() is called.
    """

    def __init__(self):
        super().__init__()
        self.setTitle("Hand Display")
        self.resize(900, 700)

        # rootEntity is the top of the Qt3D scene graph. Every other entity
        # is a descendant of this one (directly or through a chain of parents).
        self.rootEntity = Qt3DCore.QEntity()

        self._setup_camera()
        self._setup_material()
        self._setup_lighting()
        self._build_scene()

        # Register the root entity with the window so Qt3D can render it.
        self.setRootEntity(self.rootEntity)

    # -----------------------------------------------------------------------
    # Scene setup
    # -----------------------------------------------------------------------

    def _setup_camera(self):
        """
        Configure the perspective camera and attach an orbit controller so
        the user can rotate the view with the mouse.
        """
        camera = self.camera()

        # Perspective projection: 45° vertical field of view, 16:9 aspect ratio,
        # near clip plane at 0.1 units, far clip plane at 1000 units.
        camera.lens().setPerspectiveProjection(45.0, 16.0 / 9.0, 0.1, 1000.0)

        # Position the camera above and in front of the hand model.
        # The hand sits near the origin; this angle gives a good overview.
        camera.setPosition(QVector3D(5, -30, 50))
        camera.setViewCenter(QVector3D(5, 0, 0))   # look toward the hand
        camera.setUpVector(QVector3D(0, 0, 1))      # Z is "up" in this scene

        # QOrbitCameraController lets the user rotate, pan, and zoom with the mouse.
        controller = Qt3DExtras.QOrbitCameraController(self.rootEntity)
        controller.setLinearSpeed(50.0)    # units per second for pan/zoom
        controller.setLookSpeed(180.0)     # degrees per second for rotation
        controller.setCamera(camera)

    def _setup_material(self):
        """
        Create the single Phong shading material shared by all geometry.
        Using one material instance for all segments is more efficient than
        creating one per entity.
        """
        self.material = Qt3DExtras.QPhongMaterial(self.rootEntity)
        self.material.setDiffuse(QColor(100, 150, 200))    # blue-grey base colour
        self.material.setAmbient(QColor(50, 75, 100))      # dark blue ambient (shadow colour)
        self.material.setSpecular(QColor(255, 255, 255))   # white specular highlights
        self.material.setShininess(50.0)                   # moderately sharp highlights

    def _setup_lighting(self):
        """
        Add two point lights to give the hand model depth through shading.
        A primary light from the upper-right and a dimmer fill light from the left.
        """
        self._add_point_light(QVector3D(10, 10, 10),   intensity=1.0)   # key light
        self._add_point_light(QVector3D(-10, 10, 10),  intensity=0.5)   # fill light

    def _add_point_light(self, position, intensity):
        """
        Create a point light (radiates equally in all directions) at the given
        scene position with the given brightness.

        Args:
            position:  QVector3D — light position in scene units.
            intensity: float — brightness multiplier (1.0 = full).
        """
        entity = Qt3DCore.QEntity(self.rootEntity)   # lights need an entity to attach to

        light = Qt3DRender.QPointLight(entity)
        light.setColor(QColor(255, 255, 255))   # white light
        light.setIntensity(intensity)

        transform = Qt3DCore.QTransform(entity)
        transform.setTranslation(position)   # move the light entity to the desired position

        entity.addComponent(light)
        entity.addComponent(transform)

    def _build_scene(self):
        """
        Top-level scene construction. Called once during __init__.
        Builds the palm, the four three-segment fingers, and the thumb.
        """
        self._build_palm()
        self._build_four_fingers()
        self._build_thumb()

    # -----------------------------------------------------------------------
    # Scene construction helpers
    # -----------------------------------------------------------------------

    def _make_segment_entity(self, parent, radius, length):
        """
        Build one finger-segment entity consisting of a cylinder mesh,
        a transform, and the shared material, all attached to *parent*.

        The cylinder is created along the Y axis by default (Qt3D convention).
        Its position and orientation are set by the caller via the returned transform.

        Args:
            parent: the Qt3D QEntity this segment should be a child of.
            radius: cylinder radius in scene units.
            length: cylinder length in scene units.

        Returns:
            (entity, transform): the entity and its QTransform component,
            so the caller can set translation and rotation.
        """
        entity = Qt3DCore.QEntity(parent)

        # Create a cylinder mesh and configure its dimensions and smoothness.
        mesh = Qt3DExtras.QCylinderMesh(entity)
        mesh.setRadius(radius)
        mesh.setLength(length)
        mesh.setRings(20)    # subdivisions along the length (more = smoother endcaps)
        mesh.setSlices(32)   # subdivisions around the circumference (more = rounder)

        transform = Qt3DCore.QTransform(entity)

        entity.addComponent(mesh)
        entity.addComponent(transform)
        entity.addComponent(self.material)   # shared material — no per-entity colour

        return entity, transform

    def _build_palm(self):
        """
        Build the palm: a wide, short cylinder representing the back of the hand.

        Positioned slightly offset from origin (+5 X, -10 Y) to roughly centre
        the hand model in the scene. Rotated +90° around X so its flat face
        points upward (+Z), which is the "back of the hand" orientation.
        The palm entity is the parent of all finger proximal segments.
        """
        PALM_RADIUS = 8   # wide enough to span all four fingers
        PALM_LENGTH = 4   # thin, representing hand thickness

        self.entity_Palm, self.transform_Palm = self._make_segment_entity(
            self.rootEntity, PALM_RADIUS, PALM_LENGTH
        )
        self.transform_Palm.setTranslation(QVector3D(5, -10, 0))
        # +90° X rotation: cylinder created along Y, rotation tips it so the
        # circular faces point up (+Z) and down (-Z) — flat "hand" orientation.
        self.transform_Palm.setRotation(
            QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), 90)
        )

        self._palm_radius = PALM_RADIUS   # stored so finger positions can be computed relative to it

    def _build_three_segment_finger(self, parent, proximal_len, middle_len, distal_len,
                                    proximal_radii, x_offset):
        """
        Build a three-segment finger (proximal → middle → distal) as a
        parent-child chain attached to *parent*.

        The proximal segment is positioned so its base sits at the edge of
        the palm cylinder, offset laterally by x_offset. It is rotated -90°
        around X to point forward (+Z direction from the palm face).

        Middle and distal segments are children of the segment before them,
        so their transforms are cumulative. Each child's translation places
        it so its base aligns with the tip of its parent segment — this
        defines the joint pivot point (the base of the cylinder being rotated).

        Args:
            parent:        the entity to attach the proximal segment to (entity_Palm).
            proximal_len:  length of the base segment (scene units).
            middle_len:    length of the middle segment.
            distal_len:    length of the distal (tip) segment.
            proximal_radii: (r_proximal, r_middle, r_distal) — cylinder radii,
                            tapering toward the fingertip.
            x_offset:      lateral position along the palm's X axis.

        Returns:
            (proximal_transform, middle_transform, distal_transform)
            proximal_transform: used by setOrientationFingers() to rotate the whole finger.
            middle_transform:   used by setAngles*() to apply J1 flex curl.
            distal_transform:   used by setAngles*() to apply J2 flex curl.
        """
        r_proximal, r_middle, r_distal = proximal_radii

        # --- Proximal (base) segment ---
        # Parented to entity_Palm (the entire palm entity).
        # Positioned so its centre is at the palm edge + half its own length outward.
        # Rotated -90° around X: default Y-axis cylinder now points along +Z (forward).
        proximal_entity, proximal_transform = self._make_segment_entity(
            parent, r_proximal, proximal_len
        )
        proximal_transform.setTranslation(
            # -(palm_radius + half_proximal_len) puts the cylinder's base at the palm edge.
            QVector3D(x_offset, 0, -(self._palm_radius + proximal_len / 2))
        )
        proximal_transform.setRotation(
            QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), 90)
            # -90° around X: the cylinder's +Y end now points in the -Z direction,
            # which is "away from the palm" in the scene (finger extends outward).
        )

        # --- Middle segment ---
        # Parented to proximal_entity, so it inherits the proximal segment's transform.
        # Its Y-translation (in proximal's local space) positions its base at the
        # tip of the proximal cylinder. This point is the J1 joint pivot.
        # When middle_transform's rotation is changed, the curl originates from this point.
        middle_entity, middle_transform = self._make_segment_entity(
            proximal_entity, r_middle, middle_len
        )
        middle_transform.setTranslation(
            # In proximal's local space, the tip is at +Y = half proximal length.
            # The middle cylinder's centre must be at tip + half middle length.
            QVector3D(0, proximal_len / 2 + middle_len / 2, 0)
        )

        # --- Distal segment ---
        # Parented to middle_entity. Same pivot logic as above, but using middle's length.
        # When distal_transform's rotation changes, curl originates from the middle/distal joint.
        distal_entity, distal_transform = self._make_segment_entity(
            middle_entity, r_distal, distal_len
        )
        distal_transform.setTranslation(
            QVector3D(0, middle_len / 2 + distal_len / 2, 0)
        )

        return proximal_transform, middle_transform, distal_transform

    def _build_four_fingers(self):
        """
        Build the pointer, middle, ring, and pinky fingers using the shared
        three-segment helper, then store their transforms as instance attributes
        so the public setAngles*() methods can access them.

        Finger positions along the palm X axis:
            Pointer:  x = -4  (index side of hand)
            Middle:   x =  0  (centre)
            Ring:     x = +4
            Pinky:    x = +8  (pinky side of hand)

        Finger geometry (scene units, proportional to anatomy):
            Pointer:  proximal=8,  middle=5,   distal=4
            Middle:   proximal=10, middle=5.5, distal=4
            Ring:     proximal=9,  middle=5,   distal=4
            Pinky:    proximal=5,  middle=4,   distal=4

        All four use radii (proximal=1.3, middle=1.1, distal=0.9), tapering
        slightly toward the fingertip.
        """
        RADII = (1.3, 1.1, 0.9)   # shared taper profile for all four fingers

        finger_specs = [
            # (name,     prox_len, mid_len, dist_len, x_offset)
            ('Pointer',  8.0,      5.0,     4.0,      -4),
            ('Middle',   10.0,     5.5,     4.0,       0),
            ('Ring',     9.0,      5.0,     4.0,       4),
            ('Pinky',    5.0,      4.0,     4.0,       8),
        ]

        for name, prox_len, mid_len, dist_len, x_off in finger_specs:
            prox_t, mid_t, dist_t = self._build_three_segment_finger(
                self.entity_Palm, prox_len, mid_len, dist_len, RADII, x_off
            )
            # Store transforms under predictable names so setAngles*() methods
            # can look them up by finger name (e.g. self.middle_transform_Pointer).
            setattr(self, f'proximal_transform_{name}', prox_t)
            setattr(self, f'middle_transform_{name}',   mid_t)
            setattr(self, f'distal_transform_{name}',   dist_t)

    def _build_thumb(self):
        """
        Build the thumb as a two-segment finger (proximal + distal only — no middle).

        The thumb is positioned to the side of the palm (x = -10) and its Z
        offset is reduced by 10 units relative to the other fingers, placing it
        alongside the palm rather than directly above its edge.

        Geometry: proximal=6.5, distal=5.75; radii (proximal=1.5, distal=1.6).
        The distal segment is slightly wider than the proximal — this is
        intentional to match the physical thumb shape.
        """
        PROX_LEN = 6.5
        DIST_LEN = 5.75

        proximal_entity, self.proximal_transform_Thumb = self._make_segment_entity(
            self.entity_Palm, 1.5, PROX_LEN
        )
        self.proximal_transform_Thumb.setTranslation(
            # The -10 offset in Z (compared to the four fingers) positions the thumb
            # beside the palm rather than directly above its far edge.
            QVector3D(-10, 0, -(self._palm_radius + PROX_LEN / 2 - 10))
        )
        self.proximal_transform_Thumb.setRotation(
            QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), 90)
        )

        # Distal segment — parented to proximal_entity, same chain logic as four-segment fingers.
        # The thumb has no middle segment, so the distal pivot is directly at the proximal tip.
        # Note: translation uses DIST_LEN / 2 (not PROX_LEN / 2 + DIST_LEN / 2) — this matches
        # the original code and places the distal segment slightly differently than the four fingers.
        distal_entity, self.distal_transform_Thumb = self._make_segment_entity(
            proximal_entity, 1.6, DIST_LEN
        )
        self.distal_transform_Thumb.setTranslation(
            QVector3D(0, DIST_LEN / 2, 0)
        )

    # -----------------------------------------------------------------------
    # Internal flex helper
    # -----------------------------------------------------------------------

    def _apply_flex(self, middle_transform, distal_transform, middle_angle, distal_angle):
        """
        Apply curl angles to a finger's middle and distal joint transforms.

        Rotation is around the -X axis. In the local coordinate space of each
        segment (where Y points along the finger's extension direction), rotating
        around -X tilts the cylinder's tip downward — i.e., toward the palm.
        Positive angle = more curl.

        Args:
            middle_transform: QTransform of the segment at the J1 joint.
            distal_transform: QTransform of the segment at the J2 joint.
            middle_angle:     J1 flex angle in degrees.
            distal_angle:     J2 flex angle in degrees.
        """
        middle_transform.setRotation(
            QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), middle_angle)
        )
        distal_transform.setRotation(
            QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), distal_angle)
        )

    # -----------------------------------------------------------------------
    # Public angle setters
    # -----------------------------------------------------------------------

    def setAnglesPointer(self, middle_angle: float, distal_angle: float):
        """
        Set the flex angles for the pointer finger's J1 (middle segment) and
        J2 (distal segment) joints. Called by GloveMonitorWindow each animation frame.

        Args:
            middle_angle: J1 flex angle in degrees (0 = straight, positive = curled).
            distal_angle: J2 flex angle in degrees.
        """
        self._apply_flex(self.middle_transform_Pointer, self.distal_transform_Pointer,
                         middle_angle, distal_angle)

    def setAnglesMiddle(self, middle_angle: float, distal_angle: float):
        """Set flex angles for the middle finger's J1 and J2 joints (degrees)."""
        self._apply_flex(self.middle_transform_Middle, self.distal_transform_Middle,
                         middle_angle, distal_angle)

    def setAnglesRing(self, middle_angle: float, distal_angle: float):
        """Set flex angles for the ring finger's J1 and J2 joints (degrees)."""
        self._apply_flex(self.middle_transform_Ring, self.distal_transform_Ring,
                         middle_angle, distal_angle)

    def setAnglesPinky(self, middle_angle: float, distal_angle: float):
        """Set flex angles for the pinky finger's J1 and J2 joints (degrees)."""
        self._apply_flex(self.middle_transform_Pinky, self.distal_transform_Pinky,
                         middle_angle, distal_angle)

    def setAngleThumb(self, distal_angle: float):
        """
        Set the flex angle for the thumb's single joint (the distal segment).
        The thumb has no middle segment, so only one angle is needed.

        Args:
            distal_angle: flex angle in degrees (0 = straight, positive = curled).
        """
        self.distal_transform_Thumb.setRotation(
            QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), distal_angle)
        )

    # -----------------------------------------------------------------------
    # Public orientation setters
    # -----------------------------------------------------------------------

    def setOrientationPalm(self, qx: float, qy: float, qz: float, qw: float):
        """
        Apply the wrist orientation quaternion to the palm transform, rotating
        the entire hand (palm + all parented fingers) as a unit.

        A +90° X-axis offset is applied before the incoming quaternion. This
        corrects for the difference between the HandKinematics coordinate frame
        (where the quaternion was integrated) and the Qt3D scene frame (where Z
        is up and the palm face points +Z). Without this offset the hand would
        start in a sideways orientation.

        Args:
            qx, qy, qz, qw: components of the wrist quaternion from HandKinematics.
                             Note: QQuaternion constructor takes (w, x, y, z).
        """
        q_offset = QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), 90)  # scene alignment offset
        wrist_rotation = q_offset * QQuaternion(qw, qx, qy, qz)          # prepend offset
        self.transform_Palm.setRotation(wrist_rotation)

    def setOrientationFingers(self, j0AnglesQ: list):
        """
        Apply per-finger base-segment (proximal) quaternions to orient each
        finger independently. This captures abduction/adduction (side-to-side
        spreading) and twist, which the flex angles alone cannot represent.

        Each proximal segment's transform is set directly — its rotation
        overrides the default -90° X rest rotation and replaces it with the
        full computed orientation from HandKinematics.get_relative_orientations_q().

        Args:
            j0AnglesQ: flat list of 20 floats — [x, y, z, w] per finger,
                       in order: thumb (0:4), pointer (4:8), middle (8:12),
                       ring (12:16), pinky (16:20).
        """
        # q_rest is identity rotation (0° offset) — included to match the original
        # code structure, where it was present as a placeholder for future corrections.
        q_rest = QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), 0)

        def make_rotation(qx, qy, qz, qw):
            """Combine q_rest with the incoming quaternion. q_rest is currently identity."""
            return q_rest * QQuaternion(qw, qx, qy, qz)

        # Slice the flat 20-element list into per-finger [x, y, z, w] groups
        # and apply each to the corresponding proximal segment transform.
        self.proximal_transform_Thumb.setRotation(   make_rotation(*j0AnglesQ[0:4]))
        self.proximal_transform_Pointer.setRotation( make_rotation(*j0AnglesQ[4:8]))
        self.proximal_transform_Middle.setRotation(  make_rotation(*j0AnglesQ[8:12]))
        self.proximal_transform_Ring.setRotation(    make_rotation(*j0AnglesQ[12:16]))
        self.proximal_transform_Pinky.setRotation(   make_rotation(*j0AnglesQ[16:20]))
