from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QVector3D, QQuaternion
from PySide6.Qt3DCore import Qt3DCore
from PySide6.Qt3DExtras import Qt3DExtras
from PySide6.Qt3DRender import Qt3DRender
import math


class AnimationWindow(Qt3DExtras.Qt3DWindow):
    def __init__(self):
        super().__init__()
        self.setTitle("Pointer Finger Display")
        self.resize(900, 700)

        # Root entity - MUST be created first
        self.rootEntity = Qt3DCore.QEntity()

        # Camera setup
        camera = self.camera()
        camera.lens().setPerspectiveProjection(45.0, 16.0 / 9.0, 0.1, 1000.0)
        camera.setPosition(QVector3D(0, 0, 30.0))
        camera.setViewCenter(QVector3D(0, 0, 0))
        camera.setUpVector(QVector3D(0, 1, 0))

        # Camera controller
        camController = Qt3DExtras.QOrbitCameraController(self.rootEntity)
        camController.setLinearSpeed(50.0)
        camController.setLookSpeed(180.0)
        camController.setCamera(camera)

        # Create material
        self.material = Qt3DExtras.QPhongMaterial(self.rootEntity)
        self.material.setDiffuse(QColor(100, 150, 200))
        self.material.setAmbient(QColor(50, 75, 100))
        self.material.setSpecular(QColor(255, 255, 255))
        self.material.setShininess(50.0)

        # Add lighting
        self.add_light(QVector3D(10, 10, 10), 1.0)
        self.add_light(QVector3D(-10, 10, 10), 0.5)

        # Create finger segments
        self.create_finger_segments()

        # IMPORTANT: Set root entity LAST
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
        """Create the three finger segments"""
        # Segment lengths
        proximal_len = 8.0
        middle_len = 6.0
        distal_len = 4.0

        # === PROXIMAL SEGMENT (base segment) ===
        self.proximal_entity = Qt3DCore.QEntity(self.rootEntity)

        proximal_mesh = Qt3DExtras.QCylinderMesh(self.proximal_entity)
        proximal_mesh.setRadius(1.3)
        proximal_mesh.setLength(proximal_len)
        proximal_mesh.setRings(20)
        proximal_mesh.setSlices(32)

        # Transform for proximal - rotation happens here
        self.proximal_transform = Qt3DCore.QTransform(self.proximal_entity)
        # Cylinder is created along Y-axis, positioned so base is at origin
        self.proximal_transform.setTranslation(QVector3D(0, proximal_len / 2, 0))

        self.proximal_entity.addComponent(proximal_mesh)
        self.proximal_entity.addComponent(self.proximal_transform)
        self.proximal_entity.addComponent(self.material)

        # === MIDDLE SEGMENT ===
        # Parent to proximal entity
        self.middle_entity = Qt3DCore.QEntity(self.proximal_entity)

        middle_mesh = Qt3DExtras.QCylinderMesh(self.middle_entity)
        middle_mesh.setRadius(1.1)
        middle_mesh.setLength(middle_len)
        middle_mesh.setRings(20)
        middle_mesh.setSlices(32)

        # Transform for middle - this is where rotation happens
        self.middle_transform = Qt3DCore.QTransform(self.middle_entity)
        # Position at the top of proximal segment (in proximal's local space)
        # The pivot point is at the base of this cylinder
        self.middle_transform.setTranslation(QVector3D(0, proximal_len / 2 + middle_len / 2, 0))

        self.middle_entity.addComponent(middle_mesh)
        self.middle_entity.addComponent(self.middle_transform)
        self.middle_entity.addComponent(self.material)

        # === DISTAL SEGMENT ===
        # Parent to middle entity
        self.distal_entity = Qt3DCore.QEntity(self.middle_entity)

        distal_mesh = Qt3DExtras.QCylinderMesh(self.distal_entity)
        distal_mesh.setRadius(0.9)
        distal_mesh.setLength(distal_len)
        distal_mesh.setRings(20)
        distal_mesh.setSlices(32)

        # Transform for distal - this is where rotation happens
        self.distal_transform = Qt3DCore.QTransform(self.distal_entity)
        # Position at the top of middle segment (in middle's local space)
        self.distal_transform.setTranslation(QVector3D(0, middle_len / 2 + distal_len / 2, 0))

        self.distal_entity.addComponent(distal_mesh)
        self.distal_entity.addComponent(self.distal_transform)
        self.distal_entity.addComponent(self.material)

        # Store segment lengths for rotation calculations
        self.proximal_len = proximal_len
        self.middle_len = middle_len
        self.distal_len = distal_len

    def setAngles(self, middle_angle: float, distal_angle: float):
        """
        Set the bend angles for the finger segments.

        Args:
            middle_angle: Angle in degrees for the middle segment (0 = straight)
            distal_angle: Angle in degrees for the distal segment (0 = straight)
        """
        # For the middle segment: rotate around X-axis at its base
        # We need to rotate, but keep the translation
        middle_rotation = QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), middle_angle)
        self.middle_transform.setRotation(middle_rotation)
        # Keep original translation
        self.middle_transform.setTranslation(QVector3D(0, self.proximal_len / 2 + self.middle_len / 2, 0))

        # For the distal segment: rotate around X-axis at its base
        distal_rotation = QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), distal_angle)
        self.distal_transform.setRotation(distal_rotation)
        # Keep original translation
        self.distal_transform.setTranslation(QVector3D(0, self.middle_len / 2 + self.distal_len / 2, 0))


# Test the window
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    window = AnimationWindow()
    window.show()

    # Test changing angles after a delay
    from PySide6.QtCore import QTimer


    def test_rotation():
        print("Testing rotation...")
        window.setAngles(30, 45)


    QTimer.singleShot(2000, test_rotation)

    sys.exit(app.exec())