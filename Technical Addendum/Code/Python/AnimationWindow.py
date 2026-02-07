from PySide6.Qt3DCore import Qt3DCore
from PySide6.Qt3DExtras import Qt3DExtras
from PySide6.Qt3DRender import Qt3DRender
from PySide6.QtGui import QColor, QVector3D, QQuaternion

class AnimationWindow(Qt3DExtras.Qt3DWindow):
    def __init__(self):
        super().__init__()
        self.setTitle("Pointer Finger Display")

        # set window size
        self.resize(900, 700)

        # Root entity
        self.rootEntity = Qt3DCore.QEntity()

        # Camera setup
        camera = self.camera()
        # lens() gets camera's lens object
        # Field-of-view angle, Aspect ratio, nearest-view (nearplane), furthest view (farplane)
        camera.lens().setPerspectiveProjection(45.0, 16.0 / 9.0, 0.1, 1000.0)
        # sets Camera's position as X, Y, Z
        camera.setPosition(QVector3D(5, -30, 50))
        # sets position the camera looks towards
        camera.setViewCenter(QVector3D(5, 0, 0))
        # determines Cameras 'up' direction (0, 1, 0) means Y is up
        camera.setUpVector(QVector3D(0, 0, 1))

        # Camera controller
        camController = Qt3DExtras.QOrbitCameraController(self.rootEntity)
        # sets speed for linear camera movements (units per second)
        camController.setLinearSpeed(50.0)
        # sets rotational speed for camera (units per second)
        camController.setLookSpeed(180.0)
        camController.setCamera(camera)

        # Create material
        self.material = Qt3DExtras.QPhongMaterial(self.rootEntity)
        # sets color of hand/finger material as R, G, B
        self.material.setDiffuse(QColor(100, 150, 200))
        # sets ambient (background) color, independent of light sources, as R, G, B
        self.material.setAmbient(QColor(50, 75, 100))
        # Sets color of reflections on material surface as R, G, B
        self.material.setSpecular(QColor(255, 255, 255))
        # sets shininess factor, higher values make highlights sharper
        self.material.setShininess(50.0)

        # Add lighting
        # adds light source at position X, Y, Z, intensity I
        self.add_light(QVector3D(10, 10, 10), 1.0)
        self.add_light(QVector3D(-10, 10, 10), 0.5)

        # Create finger segments
        # see related method
        self.create_finger_segments()

        # IMPORTANT: Set root entity
        self.setRootEntity(self.rootEntity)

    def add_light(self, position, intensity):
        """Add a point light to the scene"""
        lightEntity = Qt3DCore.QEntity(self.rootEntity)

        light = Qt3DRender.QPointLight(lightEntity)
        light.setColor(QColor(255, 255, 255))
        light.setIntensity(intensity)

        lightTransform = Qt3DCore.QTransform(lightEntity)
        lightTransform.setTranslation(position)

        lightEntity.addComponent(light)
        lightEntity.addComponent(lightTransform)

        return lightEntity

    def create_finger_segments(self):

        # -------------------------------------------- POINTER FINGER INITIALIZATION ----------------------------------
        """Create the three finger segments"""
        # Segment lengths (pointer Finger)
        proximal_len_Pointer = 8.0
        middle_len_Pointer = 5.0
        distal_len_Pointer = 4.0

        # === PROXIMAL SEGMENT (base segment) For Pointer Finger ===
        self.proximal_entity_Pointer = Qt3DCore.QEntity(self.rootEntity)

        proximal_mesh_Pointer = Qt3DExtras.QCylinderMesh(self.proximal_entity_Pointer)
        # sets radius of cylinder mesh
        proximal_mesh_Pointer.setRadius(1.3)
        # sets length of cylinder mesh
        proximal_mesh_Pointer.setLength(proximal_len_Pointer)
        # sets number of subdivisions along length (around radius) to smooth rendering
        proximal_mesh_Pointer.setRings(20)
        # sets number of subdivisions around the circumference to make shape more cylindrical
        proximal_mesh_Pointer.setSlices(32)

        # Transform for proximal - rotation happens here
        self.proximal_transform = Qt3DCore.QTransform(self.proximal_entity_Pointer)
        # Cylinder is created along Y-axis, positioned so base is at origin
        self.proximal_transform.setTranslation(QVector3D(0, proximal_len_Pointer / 2, 0))

        self.proximal_entity_Pointer.addComponent(proximal_mesh_Pointer)
        self.proximal_entity_Pointer.addComponent(self.proximal_transform)
        self.proximal_entity_Pointer.addComponent(self.material)

        # === MIDDLE SEGMENT For Pointer Finger ===
        # Parent to proximal entity
        self.middle_entity_Pointer = Qt3DCore.QEntity(self.proximal_entity_Pointer)

        middle_mesh_Pointer = Qt3DExtras.QCylinderMesh(self.middle_entity_Pointer)
        # sets radius of cylinder mesh
        middle_mesh_Pointer.setRadius(1.1)
        # sets length of cylinder mesh
        middle_mesh_Pointer.setLength(middle_len_Pointer)
        # sets number of subdivisions along length (around radius) to smooth rendering
        middle_mesh_Pointer.setRings(20)
        # sets number of subdivisions around the circumference to make shape more cylindrical
        middle_mesh_Pointer.setSlices(32)

        # Transform for middle - this is where rotation happens
        self.middle_transform_Pointer = Qt3DCore.QTransform(self.middle_entity_Pointer)
        # Position at the top of proximal segment (in proximal's local space)
        # The pivot point is at the base of this cylinder (joint between middle and bast segments)
        self.middle_transform_Pointer.setTranslation(QVector3D(0, proximal_len_Pointer / 2 + middle_len_Pointer / 2, 0))

        self.middle_entity_Pointer.addComponent(middle_mesh_Pointer)
        self.middle_entity_Pointer.addComponent(self.middle_transform_Pointer)
        self.middle_entity_Pointer.addComponent(self.material)

        # === DISTAL SEGMENT For Pointer Finger ===
        # Parent to middle entity
        self.distal_entity_Pointer = Qt3DCore.QEntity(self.middle_entity_Pointer)

        distal_mesh_Pointer = Qt3DExtras.QCylinderMesh(self.distal_entity_Pointer)
        # sets radius of cylinder mesh
        distal_mesh_Pointer.setRadius(0.9)
        # sets length of cylinder mesh
        distal_mesh_Pointer.setLength(distal_len_Pointer)
        # sets number of subdivisions along length (around radius) to smooth rendering
        distal_mesh_Pointer.setRings(20)
        # sets number of subdivisions around the circumference to make shape more cylindrical
        distal_mesh_Pointer.setSlices(32)

        # Transform for distal - this is where rotation happens
        self.distal_transform_Pointer = Qt3DCore.QTransform(self.distal_entity_Pointer)
        #  another pivot point, this time between middle and tip segments
        self.distal_transform_Pointer.setTranslation(QVector3D(0, middle_len_Pointer / 2 + distal_len_Pointer / 2, 0))

        self.distal_entity_Pointer.addComponent(distal_mesh_Pointer)
        self.distal_entity_Pointer.addComponent(self.distal_transform_Pointer)
        self.distal_entity_Pointer.addComponent(self.material)

        # Store segment lengths for rotation calculations
        self.proximal_len_Pointer = proximal_len_Pointer
        self.middle_len_Pointer = middle_len_Pointer
        self.distal_len_Pointer = distal_len_Pointer

        # -------------------------------------------- END POINTER FINGER INITIALIZATION -----------------------------

        # -------------------------------------------- MIDDLE FINGER INITIALIZATION ----------------------------------
        """Create the three finger segments"""
        # Segment lengths (pointer Finger)
        proximal_len_Middle = 10.0
        middle_len_Middle = 5.5
        distal_len_Middle = 4.0

        # === PROXIMAL SEGMENT (base segment) For Middle Finger ===
        self.proximal_entity_Middle = Qt3DCore.QEntity(self.rootEntity)

        proximal_mesh_Middle = Qt3DExtras.QCylinderMesh(self.proximal_entity_Middle)
        # sets radius of cylinder mesh
        proximal_mesh_Middle.setRadius(1.3)
        # sets length of cylinder mesh
        proximal_mesh_Middle.setLength(proximal_len_Middle)
        # sets number of subdivisions along length (around radius) to smooth rendering
        proximal_mesh_Middle.setRings(20)
        # sets number of subdivisions around the circumference to make shape more cylindrical
        proximal_mesh_Middle.setSlices(32)

        # Transform for proximal - rotation happens here
        self.proximal_transform = Qt3DCore.QTransform(self.proximal_entity_Middle)
        # Cylinder is created along Y-axis, positioned so base is at origin
        self.proximal_transform.setTranslation(QVector3D(4, proximal_len_Middle / 2, 0))

        self.proximal_entity_Middle.addComponent(proximal_mesh_Middle)
        self.proximal_entity_Middle.addComponent(self.proximal_transform)
        self.proximal_entity_Middle.addComponent(self.material)

        # === MIDDLE SEGMENT For Middle Finger ===
        # Parent to proximal entity
        self.middle_entity_Middle = Qt3DCore.QEntity(self.proximal_entity_Middle)

        middle_mesh_Middle = Qt3DExtras.QCylinderMesh(self.middle_entity_Middle)
        # sets radius of cylinder mesh
        middle_mesh_Middle.setRadius(1.1)
        # sets length of cylinder mesh
        middle_mesh_Middle.setLength(middle_len_Middle)
        # sets number of subdivisions along length (around radius) to smooth rendering
        middle_mesh_Middle.setRings(20)
        # sets number of subdivisions around the circumference to make shape more cylindrical
        middle_mesh_Middle.setSlices(32)

        # Transform for middle - this is where rotation happens
        self.middle_transform_Middle = Qt3DCore.QTransform(self.middle_entity_Middle)
        # Position at the top of proximal segment (in proximal's local space)
        # The pivot point is at the base of this cylinder (joint between middle and bast segments)
        self.middle_transform_Middle.setTranslation(QVector3D(0, proximal_len_Middle / 2 + middle_len_Middle / 2, 0))

        self.middle_entity_Middle.addComponent(middle_mesh_Middle)
        self.middle_entity_Middle.addComponent(self.middle_transform_Middle)
        self.middle_entity_Middle.addComponent(self.material)

        # === DISTAL SEGMENT For Middle Finger ===
        # Parent to middle entity
        self.distal_entity_Middle = Qt3DCore.QEntity(self.middle_entity_Middle)

        distal_mesh_Middle = Qt3DExtras.QCylinderMesh(self.distal_entity_Middle)
        # sets radius of cylinder mesh
        distal_mesh_Middle.setRadius(0.9)
        # sets length of cylinder mesh
        distal_mesh_Middle.setLength(distal_len_Middle)
        # sets number of subdivisions along length (around radius) to smooth rendering
        distal_mesh_Middle.setRings(20)
        # sets number of subdivisions around the circumference to make shape more cylindrical
        distal_mesh_Middle.setSlices(32)

        # Transform for distal - this is where rotation happens
        self.distal_transform_Middle = Qt3DCore.QTransform(self.distal_entity_Middle)
        #  another pivot point, this time between middle and tip segments
        self.distal_transform_Middle.setTranslation(QVector3D(0, middle_len_Middle / 2 + distal_len_Middle / 2, 0))

        self.distal_entity_Middle.addComponent(distal_mesh_Middle)
        self.distal_entity_Middle.addComponent(self.distal_transform_Middle)
        self.distal_entity_Middle.addComponent(self.material)

        # Store segment lengths for rotation calculations
        self.proximal_len_Middle = proximal_len_Middle
        self.middle_len_Middle = middle_len_Middle
        self.distal_len_Middle = distal_len_Middle

        # -------------------------------------------- END Middle FINGER INITIALIZATION -----------------------------

        # -------------------------------------------- Ring FINGER INITIALIZATION ----------------------------------
        """Create the three finger segments"""
        # Segment lengths (pointer Finger)
        proximal_len_Ring = 9.0
        middle_len_Ring = 5.0
        distal_len_Ring = 4.0

        # === PROXIMAL SEGMENT (base segment) For Ring Finger ===
        self.proximal_entity_Ring = Qt3DCore.QEntity(self.rootEntity)

        proximal_mesh_Ring = Qt3DExtras.QCylinderMesh(self.proximal_entity_Ring)
        # sets radius of cylinder mesh
        proximal_mesh_Ring.setRadius(1.3)
        # sets length of cylinder mesh
        proximal_mesh_Ring.setLength(proximal_len_Ring)
        # sets number of subdivisions along length (around radius) to smooth rendering
        proximal_mesh_Ring.setRings(20)
        # sets number of subdivisions around the circumference to make shape more cylindrical
        proximal_mesh_Ring.setSlices(32)

        # Transform for proximal - rotation happens here
        self.proximal_transform = Qt3DCore.QTransform(self.proximal_entity_Ring)
        # Cylinder is created along Y-axis, positioned so base is at origin
        self.proximal_transform.setTranslation(QVector3D(8, proximal_len_Ring / 2, 0))

        self.proximal_entity_Ring.addComponent(proximal_mesh_Ring)
        self.proximal_entity_Ring.addComponent(self.proximal_transform)
        self.proximal_entity_Ring.addComponent(self.material)

        # === MIDDLE SEGMENT For Ring Finger ===
        # Parent to proximal entity
        self.middle_entity_Ring = Qt3DCore.QEntity(self.proximal_entity_Ring)

        middle_mesh_Ring = Qt3DExtras.QCylinderMesh(self.middle_entity_Ring)
        # sets radius of cylinder mesh
        middle_mesh_Ring.setRadius(1.1)
        # sets length of cylinder mesh
        middle_mesh_Ring.setLength(middle_len_Ring)
        # sets number of subdivisions along length (around radius) to smooth rendering
        middle_mesh_Ring.setRings(20)
        # sets number of subdivisions around the circumference to make shape more cylindrical
        middle_mesh_Ring.setSlices(32)

        # Transform for middle - this is where rotation happens
        self.middle_transform_Ring = Qt3DCore.QTransform(self.middle_entity_Ring)
        # Position at the top of proximal segment (in proximal's local space)
        # The pivot point is at the base of this cylinder (joint between middle and bast segments)
        self.middle_transform_Ring.setTranslation(QVector3D(0, proximal_len_Ring / 2 + middle_len_Ring / 2, 0))

        self.middle_entity_Ring.addComponent(middle_mesh_Ring)
        self.middle_entity_Ring.addComponent(self.middle_transform_Ring)
        self.middle_entity_Ring.addComponent(self.material)

        # === DISTAL SEGMENT For Ring Finger ===
        # Parent to middle entity
        self.distal_entity_Ring = Qt3DCore.QEntity(self.middle_entity_Ring)

        distal_mesh_Ring = Qt3DExtras.QCylinderMesh(self.distal_entity_Ring)
        # sets radius of cylinder mesh
        distal_mesh_Ring.setRadius(0.9)
        # sets length of cylinder mesh
        distal_mesh_Ring.setLength(distal_len_Ring)
        # sets number of subdivisions along length (around radius) to smooth rendering
        distal_mesh_Ring.setRings(20)
        # sets number of subdivisions around the circumference to make shape more cylindrical
        distal_mesh_Ring.setSlices(32)

        # Transform for distal - this is where rotation happens
        self.distal_transform_Ring = Qt3DCore.QTransform(self.distal_entity_Ring)
        #  another pivot point, this time between middle and tip segments
        self.distal_transform_Ring.setTranslation(QVector3D(0, middle_len_Ring / 2 + distal_len_Ring / 2, 0))

        self.distal_entity_Ring.addComponent(distal_mesh_Ring)
        self.distal_entity_Ring.addComponent(self.distal_transform_Ring)
        self.distal_entity_Ring.addComponent(self.material)

        # Store segment lengths for rotation calculations
        self.proximal_len_Ring = proximal_len_Ring
        self.middle_len_Ring = middle_len_Ring
        self.distal_len_Ring = distal_len_Ring

        # -------------------------------------------- END Ring FINGER INITIALIZATION -----------------------------

        # -------------------------------------------- PINKY FINGER INITIALIZATION ----------------------------------
        """Create the three finger segments"""
        # Segment lengths (pointer Finger)
        proximal_len_Pinky = 5.0
        middle_len_Pinky = 4.0
        distal_len_Pinky = 4.0

        # === PROXIMAL SEGMENT (base segment) For Pinky Finger ===
        self.proximal_entity_Pinky = Qt3DCore.QEntity(self.rootEntity)

        proximal_mesh_Pinky = Qt3DExtras.QCylinderMesh(self.proximal_entity_Pinky)
        # sets radius of cylinder mesh
        proximal_mesh_Pinky.setRadius(1.3)
        # sets length of cylinder mesh
        proximal_mesh_Pinky.setLength(proximal_len_Pinky)
        # sets number of subdivisions along length (around radius) to smooth rendering
        proximal_mesh_Pinky.setRings(20)
        # sets number of subdivisions around the circumference to make shape more cylindrical
        proximal_mesh_Pinky.setSlices(32)

        # Transform for proximal - rotation happens here
        self.proximal_transform = Qt3DCore.QTransform(self.proximal_entity_Pinky)
        # Cylinder is created along Y-axis, positioned so base is at origin
        self.proximal_transform.setTranslation(QVector3D(12, proximal_len_Pinky / 2, 0))

        self.proximal_entity_Pinky.addComponent(proximal_mesh_Pinky)
        self.proximal_entity_Pinky.addComponent(self.proximal_transform)
        self.proximal_entity_Pinky.addComponent(self.material)

        # === MIDDLE SEGMENT For Pinky Finger ===
        # Parent to proximal entity
        self.middle_entity_Pinky = Qt3DCore.QEntity(self.proximal_entity_Pinky)

        middle_mesh_Pinky = Qt3DExtras.QCylinderMesh(self.middle_entity_Pinky)
        # sets radius of cylinder mesh
        middle_mesh_Pinky.setRadius(1.1)
        # sets length of cylinder mesh
        middle_mesh_Pinky.setLength(middle_len_Pinky)
        # sets number of subdivisions along length (around radius) to smooth rendering
        middle_mesh_Pinky.setRings(20)
        # sets number of subdivisions around the circumference to make shape more cylindrical
        middle_mesh_Pinky.setSlices(32)

        # Transform for middle - this is where rotation happens
        self.middle_transform_Pinky = Qt3DCore.QTransform(self.middle_entity_Pinky)
        # Position at the top of proximal segment (in proximal's local space)
        # The pivot point is at the base of this cylinder (joint between middle and bast segments)
        self.middle_transform_Pinky.setTranslation(QVector3D(0, proximal_len_Pinky / 2 + middle_len_Pinky / 2, 0))

        self.middle_entity_Pinky.addComponent(middle_mesh_Pinky)
        self.middle_entity_Pinky.addComponent(self.middle_transform_Pinky)
        self.middle_entity_Pinky.addComponent(self.material)

        # === DISTAL SEGMENT For Pinky Finger ===
        # Parent to middle entity
        self.distal_entity_Pinky = Qt3DCore.QEntity(self.middle_entity_Pinky)

        distal_mesh_Pinky = Qt3DExtras.QCylinderMesh(self.distal_entity_Pinky)
        # sets radius of cylinder mesh
        distal_mesh_Pinky.setRadius(0.9)
        # sets length of cylinder mesh
        distal_mesh_Pinky.setLength(distal_len_Pinky)
        # sets number of subdivisions along length (around radius) to smooth rendering
        distal_mesh_Pinky.setRings(20)
        # sets number of subdivisions around the circumference to make shape more cylindrical
        distal_mesh_Pinky.setSlices(32)

        # Transform for distal - this is where rotation happens
        self.distal_transform_Pinky = Qt3DCore.QTransform(self.distal_entity_Pinky)
        #  another pivot point, this time between middle and tip segments
        self.distal_transform_Pinky.setTranslation(QVector3D(0, middle_len_Pinky / 2 + distal_len_Pinky / 2, 0))

        self.distal_entity_Pinky.addComponent(distal_mesh_Pinky)
        self.distal_entity_Pinky.addComponent(self.distal_transform_Pinky)
        self.distal_entity_Pinky.addComponent(self.material)

        # Store segment lengths for rotation calculations
        self.proximal_len_Pinky = proximal_len_Pinky
        self.middle_len_Pinky = middle_len_Pinky
        self.distal_len_Pinky = distal_len_Pinky

        # -------------------------------------------- END PINKY FINGER INITIALIZATION -----------------------------

        # -------------------------------------------- THUMB INITIALIZATION ----------------------------------
        """Create the three finger segments"""
        # Segment lengths (pointer Finger)
        proximal_len_Thumb = 6.5
        distal_len_Thumb = 5.75

        # === PROXIMAL SEGMENT (base segment) For Thumb Finger ===
        self.proximal_entity_Thumb = Qt3DCore.QEntity(self.rootEntity)

        proximal_mesh_Thumb = Qt3DExtras.QCylinderMesh(self.proximal_entity_Thumb)
        # sets radius of cylinder mesh
        proximal_mesh_Thumb.setRadius(1.5)
        # sets length of cylinder mesh
        proximal_mesh_Thumb.setLength(proximal_len_Thumb)
        # sets number of subdivisions along length (around radius) to smooth rendering
        proximal_mesh_Thumb.setRings(20)
        # sets number of subdivisions around the circumference to make shape more cylindrical
        proximal_mesh_Thumb.setSlices(32)

        # Transform for proximal - rotation happens here
        self.proximal_transform = Qt3DCore.QTransform(self.proximal_entity_Thumb)
        # Cylinder is created along Y-axis, positioned so base is at origin
        self.proximal_transform.setTranslation(QVector3D(-6, proximal_len_Thumb / 2 - 10, 0))

        self.proximal_entity_Thumb.addComponent(proximal_mesh_Thumb)
        self.proximal_entity_Thumb.addComponent(self.proximal_transform)
        self.proximal_entity_Thumb.addComponent(self.material)

        # === DISTAL SEGMENT For Thumb Finger ===
        # Parent to middle entity
        self.distal_entity_Thumb = Qt3DCore.QEntity(self.proximal_entity_Thumb)

        distal_mesh_Thumb = Qt3DExtras.QCylinderMesh(self.distal_entity_Thumb)
        # sets radius of cylinder mesh
        distal_mesh_Thumb.setRadius(1.6)
        # sets length of cylinder mesh
        distal_mesh_Thumb.setLength(distal_len_Thumb)
        # sets number of subdivisions along length (around radius) to smooth rendering
        distal_mesh_Thumb.setRings(20)
        # sets number of subdivisions around the circumference to make shape more cylindrical
        distal_mesh_Thumb.setSlices(32)

        # Transform for distal - this is where rotation happens
        self.distal_transform_Thumb = Qt3DCore.QTransform(self.distal_entity_Thumb)
        #  another pivot point, this time between middle and tip segments
        self.distal_transform_Thumb.setTranslation(QVector3D(0, distal_len_Thumb / 2, 0))

        self.distal_entity_Thumb.addComponent(distal_mesh_Thumb)
        self.distal_entity_Thumb.addComponent(self.distal_transform_Thumb)
        self.distal_entity_Thumb.addComponent(self.material)

        # Store segment lengths for rotation calculations
        self.proximal_len_Thumb = proximal_len_Thumb
        self.distal_len_Thumb = distal_len_Thumb

        # -------------------------------------------- END THUMB FINGER INITIALIZATION -----------------------------

        # -------------------------------------------- PALM INITIALIZATION ---------------------------

        self.entity_Palm = Qt3DCore.QEntity(self.rootEntity)

        mesh_Palm = Qt3DExtras.QCylinderMesh(self.entity_Palm)

        # sets radius of cylinder mesh
        mesh_Palm.setRadius(8)
        # sets length of cylinder mesh
        mesh_Palm.setLength(4)
        # sets number of subdivisions along length (around radius) to smooth rendering
        mesh_Palm.setRings(10)
        # sets number of subdivisions around the circumference to make shape more cylindrical
        mesh_Palm.setSlices(64)

        # Transform for proximal - rotation happens here
        self.transform_Palm = Qt3DCore.QTransform(self.entity_Palm)
        # Cylinder is created along Z-axis, positioned so base is at Center of Fingers/thumb
        self.transform_Palm.setTranslation(QVector3D(5, -10, 0))

        # rotate around X-axis to face upward
        rotation_Palm = QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), 90)
        self.transform_Palm.setRotation(rotation_Palm)

        self.entity_Palm.addComponent(mesh_Palm)
        self.entity_Palm.addComponent(self.transform_Palm)
        self.entity_Palm.addComponent(self.material)

        # -------------------------------------------- END PALM INITIALIZATION ---------------------------

    def setAnglesPointer(self, middle_angle: float, distal_angle: float):
        """
        Set the bend angles for the finger segments.

        Args:
            middle_angle: Angle in degrees for the middle segment (0 = straight)
            distal_angle: Angle in degrees for the distal segment (0 = straight)
        """
        # For the middle segment: rotate around negative X-axis at its base (fingers curl down)
        middle_rotation = QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), middle_angle)

        # sets rotation angle middle_angle degrees around -x axis
        self.middle_transform_Pointer.setRotation(middle_rotation)

        # Keep original translation on middle segment
        self.middle_transform_Pointer.setTranslation(QVector3D(0, self.proximal_len_Pointer / 2 + self.middle_len_Pointer / 2, 0))

        # For the distal segment: rotate around negative X-axis at its base (fingers curl down)
        distal_rotation = QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), distal_angle)

        # sets rotation angle distal_angle degrees around -x axis
        self.distal_transform_Pointer.setRotation(distal_rotation)

        # Keep original translation
        self.distal_transform_Pointer.setTranslation(QVector3D(0, self.middle_len_Pointer / 2 + self.distal_len_Pointer / 2, 0))

    def setAnglesMiddle(self, middle_angle: float, distal_angle: float):
        """
        Set the bend angles for the finger segments.

        Args:
            middle_angle: Angle in degrees for the middle segment (0 = straight)
            distal_angle: Angle in degrees for the distal segment (0 = straight)
        """
        # For the middle segment: rotate around negative X-axis at its base (fingers curl down)
        middle_rotation = QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), middle_angle)

        # sets rotation angle middle_angle degrees around -x axis
        self.middle_transform_Middle.setRotation(middle_rotation)

        # Keep original translation on middle segment
        self.middle_transform_Middle.setTranslation(QVector3D(0, self.proximal_len_Middle / 2 + self.middle_len_Middle / 2, 0))

        # For the distal segment: rotate around negative X-axis at its base (fingers curl down)
        distal_rotation = QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), distal_angle)

        # sets rotation angle distal_angle degrees around -x axis
        self.distal_transform_Middle.setRotation(distal_rotation)

        # Keep original translation
        self.distal_transform_Middle.setTranslation(QVector3D(0, self.middle_len_Middle / 2 + self.distal_len_Middle / 2, 0))

    def setAnglesRing(self, middle_angle: float, distal_angle: float):
            """
            Set the bend angles for the finger segments.

            Args:
                middle_angle: Angle in degrees for the middle segment (0 = straight)
                distal_angle: Angle in degrees for the distal segment (0 = straight)
            """
            # For the middle segment: rotate around negative X-axis at its base (fingers curl down)
            middle_rotation = QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), middle_angle)

            # sets rotation angle middle_angle degrees around -x axis
            self.middle_transform_Ring.setRotation(middle_rotation)

            # Keep original translation on middle segment
            self.middle_transform_Ring.setTranslation(
                QVector3D(0, self.proximal_len_Ring / 2 + self.middle_len_Ring / 2, 0))

            # For the distal segment: rotate around negative X-axis at its base (fingers curl down)
            distal_rotation = QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), distal_angle)

            # sets rotation angle distal_angle degrees around -x axis
            self.distal_transform_Ring.setRotation(distal_rotation)

            # Keep original translation
            self.distal_transform_Ring.setTranslation(
                QVector3D(0, self.middle_len_Ring / 2 + self.distal_len_Ring / 2, 0))

    def setAnglesPinky(self, middle_angle: float, distal_angle: float):
        """
        Set the bend angles for the finger segments.

        Args:
            middle_angle: Angle in degrees for the middle segment (0 = straight)
            distal_angle: Angle in degrees for the distal segment (0 = straight)
        """
        # For the middle segment: rotate around negative X-axis at its base (fingers curl down)
        middle_rotation = QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), middle_angle)

        # sets rotation angle middle_angle degrees around -x axis
        self.middle_transform_Pinky.setRotation(middle_rotation)

        # Keep original translation on middle segment
        self.middle_transform_Pinky.setTranslation(
            QVector3D(0, self.proximal_len_Pinky / 2 + self.middle_len_Pinky / 2, 0))

        # For the distal segment: rotate around negative X-axis at its base (fingers curl down)
        distal_rotation = QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), distal_angle)

        # sets rotation angle distal_angle degrees around -x axis
        self.distal_transform_Pinky.setRotation(distal_rotation)

        # Keep original translation
        self.distal_transform_Pinky.setTranslation(
            QVector3D(0, self.middle_len_Pinky / 2 + self.distal_len_Pinky / 2, 0))

    def setAngleThumb(self, distal_angle: float):
        """
        Set the bend angles for the finger segments.

        Args:
            middle_angle: Angle in degrees for the middle segment (0 = straight)
            distal_angle: Angle in degrees for the distal segment (0 = straight)
        """

        # For the distal segment: rotate around negative X-axis at its base (fingers curl down)
        distal_rotation = QQuaternion.fromAxisAndAngle(QVector3D(-1, 0, 0), distal_angle)

        # sets rotation angle distal_angle degrees around -x axis
        self.distal_transform_Thumb.setRotation(distal_rotation)

        # Keep original translation
        self.distal_transform_Thumb.setTranslation(
            QVector3D(0, self.distal_len_Thumb / 2, 0))