"""
HandRenderer.py

Qt3D rendering of both hands (right and left) in a single AnimationWindow.
Each hand is an independent sub-hierarchy under rootEntity.

Right hand  — exact original coordinates; thumb on the left side of the palm.
Left hand   — X-mirrored so its thumb is on the right side (inward), palm
              placed to the right of the right hand with a small gap.

Separation between hands is controlled by LEFT_PALM_X at the top of this file.

Public interface (called by GloveMonitorWindow each animation frame):
    # Right hand
    setAnglesPointer_R / setAnglesMiddle_R / setAnglesRing_R /
    setAnglesPinky_R / setAngleThumb_R
    setOrientationPalm_R(qx, qy, qz, qw)
    setOrientationFingers_R(j0AnglesQ)

    # Left hand
    setAnglesPointer_L / setAnglesMiddle_L / setAnglesRing_L /
    setAnglesPinky_L / setAngleThumb_L
    setOrientationPalm_L(qx, qy, qz, qw)
    setOrientationFingers_L(j0AnglesQ)

    show()
    close()
"""

from PySide6.Qt3DCore    import Qt3DCore
from PySide6.Qt3DExtras  import Qt3DExtras
from PySide6.Qt3DRender  import Qt3DRender
from PySide6.QtGui       import QColor, QVector3D, QQuaternion


# ---------------------------------------------------------------------------
# Layout constants
#
# RIGHT_PALM_X  — palm centre X for the right hand (original value).
# LEFT_PALM_X   — palm centre X for the left hand.  Increase to add more
#                 space between the hands; decrease to bring them closer.
#                 At LEFT_PALM_X = 25 the inner edges of both palms are
#                 separated by ~2 scene units.
# ---------------------------------------------------------------------------
RIGHT_PALM_X = 35
LEFT_PALM_X  = -5   # adjust this value to change hand separation


class AnimationWindow(Qt3DExtras.Qt3DWindow):
    """
    Single Qt3DWindow containing both a right-hand and a left-hand model.

    The right hand is built exactly as in the original single-hand version.
    The left hand is a mirror image: every child X offset within the palm
    is negated so that the thumb appears on the right (inner) side of that
    palm, matching anatomical left-hand orientation.
    """

    def __init__(self):
        super().__init__()
        self.setTitle("Dual Hand Display")
        self.resize(900, 700)

        self.rootEntity = Qt3DCore.QEntity()

        self._setup_camera()
        self._setup_materials()
        self._setup_lighting()
        self._build_scene()

        self.setRootEntity(self.rootEntity)

    # ------------------------------------------------------------------ #
    # Scene setup                                                          #
    # ------------------------------------------------------------------ #

    def _setup_camera(self):
        """
        Camera positioned to frame both hands.
        Centred between the two palms on X, pulled back on Y and up on Z.
        """
        camera = self.camera()
        camera.lens().setPerspectiveProjection(45.0, 16.0 / 9.0, 0.1, 1000.0)

        mid_x = (RIGHT_PALM_X + LEFT_PALM_X) / 2   # centre between the two palms
        camera.setPosition(QVector3D(mid_x, -40, 80))
        camera.setViewCenter(QVector3D(mid_x, 0, 0))
        camera.setUpVector(QVector3D(0, 0, 1))

        controller = Qt3DExtras.QOrbitCameraController(self.rootEntity)
        controller.setLinearSpeed(50.0)
        controller.setLookSpeed(180.0)
        controller.setCamera(camera)

    def _setup_materials(self):
        """Blue-grey for the right hand; green-grey for the left."""
        self.material_right = Qt3DExtras.QPhongMaterial(self.rootEntity)
        self.material_right.setDiffuse(QColor(100, 150, 200))
        self.material_right.setAmbient(QColor(50,  75,  100))
        self.material_right.setSpecular(QColor(255, 255, 255))
        self.material_right.setShininess(50.0)

        self.material_left = Qt3DExtras.QPhongMaterial(self.rootEntity)
        self.material_left.setDiffuse(QColor(100, 200, 130))
        self.material_left.setAmbient(QColor(50,  100, 65))
        self.material_left.setSpecular(QColor(255, 255, 255))
        self.material_left.setShininess(50.0)

    def _setup_lighting(self):
        self._add_point_light(QVector3D(10,  10, 10), intensity=1.0)
        self._add_point_light(QVector3D(-10, 10, 10), intensity=0.5)

    def _add_point_light(self, position, intensity):
        entity = Qt3DCore.QEntity(self.rootEntity)
        light  = Qt3DRender.QPointLight(entity)
        light.setColor(QColor(255, 255, 255))
        light.setIntensity(intensity)
        transform = Qt3DCore.QTransform(entity)
        transform.setTranslation(position)
        entity.addComponent(light)
        entity.addComponent(transform)

    def _build_scene(self):
        # Right hand — original layout, thumb at x = -10 relative to palm.
        # mirror=False means child X offsets are used as-is.
        self._build_hand(suffix='R', material=self.material_right,
                         palm_x=RIGHT_PALM_X, mirror=False)

        # Left hand — mirrored layout, thumb at x = +10 relative to palm
        # (inward, toward the right hand).
        # mirror=True negates all child X offsets within the palm.
        self._build_hand(suffix='L', material=self.material_left,
                         palm_x=LEFT_PALM_X,  mirror=True)

    # ------------------------------------------------------------------ #
    # Generic hand builder                                                 #
    # ------------------------------------------------------------------ #

    def _make_segment_entity(self, parent, radius, length, material):
        """Create a cylinder entity with a transform, parented to *parent*."""
        entity    = Qt3DCore.QEntity(parent)
        mesh      = Qt3DExtras.QCylinderMesh(entity)
        mesh.setRadius(radius)
        mesh.setLength(length)
        mesh.setRings(20)
        mesh.setSlices(32)
        transform = Qt3DCore.QTransform(entity)
        entity.addComponent(mesh)
        entity.addComponent(transform)
        entity.addComponent(material)
        return entity, transform

    def _build_hand(self, suffix, material, palm_x, mirror):
        """
        Build one complete hand.

        Args:
            suffix:  'R' or 'L' — appended to every stored transform name.
            material: QPhongMaterial for this hand.
            palm_x:  world X position of the palm centre.
            mirror:  if True, negate all child X offsets so the thumb appears
                     on the opposite side (anatomically correct for a left hand).
        """
        PALM_RADIUS = 8
        PALM_LENGTH = 4

        palm_entity, palm_transform = self._make_segment_entity(
            self.rootEntity, PALM_RADIUS, PALM_LENGTH, material
        )
        palm_transform.setTranslation(QVector3D(palm_x, -10, 0))
        palm_transform.setRotation(
            QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), 90)
        )
        setattr(self, f'entity_Palm_{suffix}',    palm_entity)
        setattr(self, f'transform_Palm_{suffix}', palm_transform)

        self._build_four_fingers_for_hand(suffix, palm_entity, PALM_RADIUS, material, mirror)
        self._build_thumb_for_hand(       suffix, palm_entity, PALM_RADIUS, material, mirror)

    # ------------------------------------------------------------------ #
    # Finger builders                                                      #
    # ------------------------------------------------------------------ #

    def _build_three_segment_finger(self, parent, proximal_len, middle_len, distal_len,
                                    proximal_radii, x_offset, palm_radius, material):
        """
        Build one three-segment finger chain (proximal -> middle -> distal).
        x_offset is already sign-adjusted by the caller for mirroring.
        """
        r_proximal, r_middle, r_distal = proximal_radii

        proximal_entity, proximal_transform = self._make_segment_entity(
            parent, r_proximal, proximal_len, material
        )
        proximal_transform.setTranslation(
            QVector3D(x_offset, 0, -(palm_radius + proximal_len / 2))
        )
        proximal_transform.setRotation(
            QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), 90)
        )

        middle_entity, middle_transform = self._make_segment_entity(
            proximal_entity, r_middle, middle_len, material
        )
        middle_transform.setTranslation(
            QVector3D(0, proximal_len / 2 + middle_len / 2, 0)
        )

        distal_entity, distal_transform = self._make_segment_entity(
            middle_entity, r_distal, distal_len, material
        )
        distal_transform.setTranslation(
            QVector3D(0, middle_len / 2 + distal_len / 2, 0)
        )

        return proximal_transform, middle_transform, distal_transform

    def _build_four_fingers_for_hand(self, suffix, palm_entity, palm_radius,
                                     material, mirror):
        """
        Build pointer, middle, ring, pinky.

        Original X offsets (right hand):
            Pointer = -6,  Middle = -2,  Ring = +2,  Pinky = +6
        Mirrored (left hand):
            Pointer = +6,  Middle = +2,  Ring = -2,  Pinky = -6

        The mirror simply negates x_off, so the finger order on the palm
        is reversed left-to-right, matching a left hand viewed from above.
        """
        RADII = (1.3, 1.1, 0.9)

        # (name, prox_len, mid_len, dist_len, x_offset_for_right_hand)
        finger_specs = [
            ('Pointer', 8.0,  5.0, 4.0, -6),
            ('Middle',  10.0, 5.5, 4.0, -2),
            ('Ring',    9.0,  5.0, 4.0,  2),
            ('Pinky',   5.0,  4.0, 4.0,  6),
        ]

        for name, prox_len, mid_len, dist_len, x_off in finger_specs:
            actual_x = -x_off if mirror else x_off
            prox_t, mid_t, dist_t = self._build_three_segment_finger(
                palm_entity, prox_len, mid_len, dist_len,
                RADII, actual_x, palm_radius, material
            )
            setattr(self, f'proximal_transform_{name}_{suffix}', prox_t)
            setattr(self, f'middle_transform_{name}_{suffix}',   mid_t)
            setattr(self, f'distal_transform_{name}_{suffix}',   dist_t)

    def _build_thumb_for_hand(self, suffix, palm_entity, palm_radius,
                               material, mirror):
        """
        Build the two-segment thumb.

        Right hand: thumb at x = -10 (left side of palm).
        Left hand:  thumb at x = +10 (right side of palm, inward).
        """
        PROX_LEN = 6.5
        DIST_LEN = 5.75

        # Original thumb x offset is -10; mirror flips it to +10.
        thumb_x = 10 if mirror else -10

        proximal_entity, proximal_transform = self._make_segment_entity(
            palm_entity, 1.5, PROX_LEN, material
        )
        proximal_transform.setTranslation(
            QVector3D(thumb_x, 0, -(palm_radius + PROX_LEN / 2 - 10))
        )
        proximal_transform.setRotation(
            QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), 90)
        )
        setattr(self, f'proximal_transform_Thumb_{suffix}', proximal_transform)

        distal_entity, distal_transform = self._make_segment_entity(
            proximal_entity, 1.6, DIST_LEN, material
        )
        distal_transform.setTranslation(QVector3D(0, DIST_LEN / 2, 0))
        setattr(self, f'distal_transform_Thumb_{suffix}', distal_transform)

    # ------------------------------------------------------------------ #
    # Internal flex helper                                                 #
    # ------------------------------------------------------------------ #

    def _apply_flex(self, middle_transform, distal_transform, middle_angle, distal_angle):
        middle_transform.setRotation(
            QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), middle_angle)
        )
        distal_transform.setRotation(
            QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), distal_angle)
        )

    # ------------------------------------------------------------------ #
    # Public angle setters -- RIGHT hand                                  #
    # ------------------------------------------------------------------ #

    def setAnglesPointer_R(self, middle_angle, distal_angle):
        self._apply_flex(self.middle_transform_Pointer_R, self.distal_transform_Pointer_R,
                         middle_angle, distal_angle)

    def setAnglesMiddle_R(self, middle_angle, distal_angle):
        self._apply_flex(self.middle_transform_Middle_R, self.distal_transform_Middle_R,
                         middle_angle, distal_angle)

    def setAnglesRing_R(self, middle_angle, distal_angle):
        self._apply_flex(self.middle_transform_Ring_R, self.distal_transform_Ring_R,
                         middle_angle, distal_angle)

    def setAnglesPinky_R(self, middle_angle, distal_angle):
        self._apply_flex(self.middle_transform_Pinky_R, self.distal_transform_Pinky_R,
                         middle_angle, distal_angle)

    def setAngleThumb_R(self, distal_angle):
        self.distal_transform_Thumb_R.setRotation(
            QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), distal_angle)
        )

    def setOrientationPalm_R(self, qx, qy, qz, qw):
        q_offset = QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), 90)
        self.transform_Palm_R.setRotation(q_offset * QQuaternion(qw, qx, qy, qz))

    def setOrientationFingers_R(self, j0AnglesQ):
        q_rest = QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), 0)
        def make_rotation(qx, qy, qz, qw):
            return q_rest * QQuaternion(qw, qx, qy, qz)
        self.proximal_transform_Thumb_R.setRotation(   make_rotation(*j0AnglesQ[0:4]))
        self.proximal_transform_Pointer_R.setRotation( make_rotation(*j0AnglesQ[4:8]))
        self.proximal_transform_Middle_R.setRotation(  make_rotation(*j0AnglesQ[8:12]))
        self.proximal_transform_Ring_R.setRotation(    make_rotation(*j0AnglesQ[12:16]))
        self.proximal_transform_Pinky_R.setRotation(   make_rotation(*j0AnglesQ[16:20]))

    # ------------------------------------------------------------------ #
    # Public angle setters -- LEFT hand                                   #
    # ------------------------------------------------------------------ #

    def setAnglesPointer_L(self, middle_angle, distal_angle):
        self._apply_flex(self.middle_transform_Pointer_L, self.distal_transform_Pointer_L,
                         middle_angle, distal_angle)

    def setAnglesMiddle_L(self, middle_angle, distal_angle):
        self._apply_flex(self.middle_transform_Middle_L, self.distal_transform_Middle_L,
                         middle_angle, distal_angle)

    def setAnglesRing_L(self, middle_angle, distal_angle):
        self._apply_flex(self.middle_transform_Ring_L, self.distal_transform_Ring_L,
                         middle_angle, distal_angle)

    def setAnglesPinky_L(self, middle_angle, distal_angle):
        self._apply_flex(self.middle_transform_Pinky_L, self.distal_transform_Pinky_L,
                         middle_angle, distal_angle)

    def setAngleThumb_L(self, distal_angle):
        self.distal_transform_Thumb_L.setRotation(
            QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), distal_angle)
        )

    def setOrientationPalm_L(self, qx, qy, qz, qw):
        q_offset = QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), 90)
        self.transform_Palm_L.setRotation(q_offset * QQuaternion(qw, qx, qy, qz))

    def setOrientationFingers_L(self, j0AnglesQ):
        q_rest = QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), 0)
        def make_rotation(qx, qy, qz, qw):
            return q_rest * QQuaternion(qw, qx, qy, qz)
        self.proximal_transform_Thumb_L.setRotation(   make_rotation(*j0AnglesQ[0:4]))
        self.proximal_transform_Pointer_L.setRotation( make_rotation(*j0AnglesQ[4:8]))
        self.proximal_transform_Middle_L.setRotation(  make_rotation(*j0AnglesQ[8:12]))
        self.proximal_transform_Ring_L.setRotation(    make_rotation(*j0AnglesQ[12:16]))
        self.proximal_transform_Pinky_L.setRotation(   make_rotation(*j0AnglesQ[16:20]))