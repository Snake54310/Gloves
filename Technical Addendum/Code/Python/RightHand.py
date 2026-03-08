import math
import numpy as np
from scipy.spatial.transform import Rotation

class Thumb:
    def __init__(self, segment1Length, segment2Length): # segments progressive from base
        self.seg1Len = segment1Length
        self.seg2Len = segment2Length
        self.j1flex = 0.0 # angle of joint between segments 1 and 2
        self.orientationX = 0 #270
        self.orientationY = 0
        self.orientationZ = 0

    def setJ1Flex(self, newJ1Flex):
        self.j1flex = newJ1Flex
        return

    def getJ1Flex(self):
        return self.j1flex

    def getSegLens(self):
        return [self.seg1Len, self.seg2Len]
    def setOrientation(self, X, Y, Z): # NOTE: this orientation is RELATIVE to wrist. Absolute orientation is stored in hand class
        self.orientationX = X
        self.orientationY = Y
        self.orientationZ = Z
        return

    def getOrientation(self):
        return [self.orientationX, self.orientationY, self.orientationZ]

    def zeroOrientation(self):
        self.orientationX = 0 #270
        self.orientationY = 0
        self.orientationZ = 0
        return

class Pointer:
    def __init__(self, segment1Length, segment2Length, segment3Length): # segments progressive from base
        self.seg1Len = segment1Length
        self.seg2Len = segment2Length
        self.seg3Len = segment3Length
        self.j1flex = 0.0  # angle of joint between segments 1 and 2
        self.j2flex = 0.0  # angle of joint between segments 2 and 3
        self.orientationX = 0 #270
        self.orientationY = 0
        self.orientationZ = 0

    def setJ1Flex(self, newJ1Flex):
        self.j1flex = newJ1Flex
        return

    def setJ2Flex(self, newJ2Flex):
        self.j2flex = newJ2Flex
        return

    def getJ1Flex(self):
        return self.j1flex

    def getJ2Flex(self):
        return self.j2flex

    def getSegLens(self):
        return [self.seg1Len, self.seg2Len, self.seg3Len]

    def setOrientation(self, X, Y,
                       Z):  # NOTE: this orientation is RELATIVE to wrist. Absolute orientation is stored in hand class
        self.orientationX = X
        self.orientationY = Y
        self.orientationZ = Z
        return

    def getOrientation(self):
        return [self.orientationX, self.orientationY, self.orientationZ]

    def zeroOrientation(self):
        self.orientationX = 0 #270
        self.orientationY = 0
        self.orientationZ = 0
        return


class Middle:
    def __init__(self, segment1Length, segment2Length, segment3Length): # segments progressive from base
        self.seg1Len = segment1Length
        self.seg2Len = segment2Length
        self.seg3Len = segment3Length
        self.j1flex = 0.0  # angle of joint between segments 1 and 2
        self.j2flex = 0.0  # angle of joint between segments 2 and 3
        self.orientationX = 0 #270
        self.orientationY = 0
        self.orientationZ = 0

    def setJ1Flex(self, newJ1Flex):
        self.j1flex = newJ1Flex
        return

    def setJ2Flex(self, newJ2Flex):
        self.j2flex = newJ2Flex
        return

    def getJ1Flex(self):
        return self.j1flex

    def getJ2Flex(self):
        return self.j2flex

    def getSegLens(self):
        return [self.seg1Len, self.seg2Len, self.seg3Len]

    def setOrientation(self, X, Y,
                       Z):  # NOTE: this orientation is RELATIVE to wrist. Absolute orientation is stored in hand class
        self.orientationX = X
        self.orientationY = Y
        self.orientationZ = Z
        return

    def getOrientation(self):
        return [self.orientationX, self.orientationY, self.orientationZ]

    def zeroOrientation(self):
        self.orientationX = 0 #270
        self.orientationY = 0
        self.orientationZ = 0
        return


class Ring:
    def __init__(self, segment1Length, segment2Length, segment3Length): # segments progressive from base
        self.seg1Len = segment1Length
        self.seg2Len = segment2Length
        self.seg3Len = segment3Length
        self.j1flex = 0.0  # angle of joint between segments 1 and 2
        self.j2flex = 0.0  # angle of joint between segments 2 and 3
        self.orientationX = 0 #270
        self.orientationY = 0
        self.orientationZ = 0

    def setJ1Flex(self, newJ1Flex):
        self.j1flex = newJ1Flex
        return

    def setJ2Flex(self, newJ2Flex):
        self.j2flex = newJ2Flex
        return

    def getJ1Flex(self):
        return self.j1flex

    def getJ2Flex(self):
        return self.j2flex

    def getSegLens(self):
        return [self.seg1Len, self.seg2Len, self.seg3Len]

    def setOrientation(self, X, Y,
                       Z):  # NOTE: this orientation is RELATIVE to wrist. Absolute orientation is stored in hand class
        self.orientationX = X
        self.orientationY = Y
        self.orientationZ = Z
        return

    def getOrientation(self):
        return [self.orientationX, self.orientationY, self.orientationZ]

    def zeroOrientation(self):
        self.orientationX = 0 #270
        self.orientationY = 0
        self.orientationZ = 0
        return


class Pinky:
    def __init__(self, segment1Length, segment2Length, segment3Length): # segments progressive from base
        self.seg1Len = segment1Length
        self.seg2Len = segment2Length
        self.seg3Len = segment3Length
        self.j1flex = 0.0  # angle of joint between segments 1 and 2
        self.j2flex = 0.0  # angle of joint between segments 2 and 3
        self.orientationX = 0 #270
        self.orientationY = 0
        self.orientationZ = 0

    def setJ1Flex(self, newJ1Flex):
        self.j1flex = newJ1Flex
        return

    def setJ2Flex(self, newJ2Flex):
        self.j2flex = newJ2Flex
        return

    def getJ1Flex(self):
        return self.j1flex

    def getJ2Flex(self):
        return self.j2flex

    def getSegLens(self):
        return [self.seg1Len, self.seg2Len, self.seg3Len]

    def setOrientation(self, X, Y,
                       Z):  # NOTE: this orientation is RELATIVE to wrist. Absolute orientation is stored in hand class
        self.orientationX = X
        self.orientationY = Y
        self.orientationZ = Z
        return

    def getOrientation(self):
        return [self.orientationX, self.orientationY, self.orientationZ]

    def zeroOrientation(self):
        self.orientationX = 0 #270
        self.orientationY = 0
        self.orientationZ = 0
        return


class RightHand: # NOTE: if two distinct hand classes are not necessary, backtrack and re-write this for the general case
    def __init__(self):
        self.thumb = Thumb(1.625, 1.4375)
        self.pointer = Pointer(2.0, 1.25, 1.0)
        self.middle = Middle(2.5, 1.375, 1.0)
        self.ring = Ring(2.25, 1.375, 1.0)
        self.pinky = Pinky(1.375, 1.0, 1.0)

        self.wristGyroDegX = 0
        self.wristGyroDegY = 0
        self.wristGyroDegZ = 0
        self.sampleRate = 10

        # NOTE: THESE ARE ABSOLUTE ROTATION ORIENTATION FOR FINGERS
        self.thumbGyroX = 0
        self.thumbGyroY = 0
        self.thumbGyroZ = 0

        self.pointerGyroX = 0
        self.pointerGyroY = 0
        self.pointerGyroZ = 0

        self.middleGyroX = 0
        self.middleGyroY = 0
        self.middleGyroZ = 0

        self.ringGyroX = 0
        self.ringGyroY = 0
        self.ringGyroZ = 0

        self.pinkyGyroX = 0
        self.pinkyGyroY = 0
        self.pinkyGyroZ = 0

        self.A_opt = np.array([[ 9.96932938e-01, 3.01375334e-04, -3.84939428e-04],
 [ 3.14513998e-04, 1.00072395e+00, 3.27329631e-04],
 [ 5.09220370e-04, -3.57745251e-04, -9.98943685e-01]])

        self.B_opt =  np.array([[ 0.00165557, -0.00073534, -0.00171393],
 [ 0.00024516, 0.00079155, -0.00045689],
 [ 0.00326962, 0.00310142, 0.00132524]])

        self.b_opt = np.array([-0.01106485, -0.00100655, -0.00118413])

        self.orientation_q = Rotation.identity()
        self.thumb_q = Rotation.identity()
        self.pointer_q = Rotation.identity()
        self.middle_q = Rotation.identity()
        self.ring_q = Rotation.identity()
        self.pinky_q = Rotation.identity()

        self.wristGyroDegW = 1.0
        self.thumbGyroW = 1.0
        self.pointerGyroW = 1.0
        self.middleGyroW = 1.0
        self.ringGyroW = 1.0
        self.pinkyGyroW = 1.0

    def setJ1Angles(self, thumbFlex, pointerFlex, middleFlex, ringFlex, pinkyFlex):
        self.thumb.setJ1Flex(thumbFlex)
        self.pointer.setJ1Flex(pointerFlex)
        self.middle.setJ1Flex(middleFlex)
        self.ring.setJ1Flex(ringFlex)
        self.pinky.setJ1Flex(pinkyFlex)

    def setJ2Angles(self, pointerFlex, middleFlex, ringFlex, pinkyFlex):
        self.pointer.setJ2Flex(pointerFlex)
        self.middle.setJ2Flex(middleFlex)
        self.ring.setJ2Flex(ringFlex)
        self.pinky.setJ2Flex(pinkyFlex)

    def getJ1Angles(self):
        j1Angles = [self.thumb.getJ1Flex(), self.pointer.getJ1Flex(), self.middle.getJ1Flex(), self.ring.getJ1Flex(), self.pinky.getJ1Flex()]
        return j1Angles

    def getJ2Angles(self):
        j2Angles = [self.pointer.getJ2Flex(), self.middle.getJ2Flex(), self.ring.getJ2Flex(), self.pinky.getJ2Flex()]
        return j2Angles

    def updateSampleRate(self, newRate):
        self.sampleRate = newRate
        return

    def updateOrientation(self, wristGyroRadssX, wristGyroRadssY, wristGyroRadssZ):
        gyro_raw = np.array([wristGyroRadssX, wristGyroRadssY, wristGyroRadssZ])

        gyro_corrected = (
                self.A_opt @ gyro_raw
                + self.B_opt @ (gyro_raw ** 2)
                + self.b_opt.flatten()
        )

        gyro_body = np.array([
            -gyro_corrected[0],
            gyro_corrected[2],
            -gyro_corrected[1],
        ])

        delta_rot = Rotation.from_rotvec(gyro_body / self.sampleRate)
        self.orientation_q = self.orientation_q * delta_rot

        euler = self.orientation_q.as_euler('zyx', degrees=True)
        self.wristGyroDegX = euler[2] % 360
        self.wristGyroDegY = euler[1] % 360
        self.wristGyroDegZ = euler[0] % 360

        q = self.orientation_q.as_quat()  # scipy: [x, y, z, w]
        self.wristGyroDegW = q[3]

        return

    def updateOrientationFingers(self, thumbX, thumbY, thumbZ, pointerX, pointerY, pointerZ,
                                 middleX, middleY, middleZ, ringX, ringY, ringZ, pinkyX, pinkyY, pinkyZ):
        def integrate(q, x, y, z):
            gyro_body = np.array([-y, x, z])
            delta_rot = Rotation.from_rotvec(gyro_body / self.sampleRate)
            return q * delta_rot

        self.thumb_q = integrate(self.thumb_q, thumbX, thumbY, thumbZ)
        self.pointer_q = integrate(self.pointer_q, pointerX, pointerY, pointerZ)
        self.middle_q = integrate(self.middle_q, middleX, middleY, middleZ)
        self.ring_q = integrate(self.ring_q, ringX, ringY, ringZ)
        self.pinky_q = integrate(self.pinky_q, pinkyX, pinkyY, pinkyZ)

        def extract_euler(q):
            e = q.as_euler('zyx', degrees=True)
            w = q.as_quat()[3]
            return e[2] % 360, e[1] % 360, e[0] % 360, w

        self.thumbGyroX, self.thumbGyroY, self.thumbGyroZ, self.thumbGyroW = extract_euler(self.thumb_q)
        self.pointerGyroX, self.pointerGyroY, self.pointerGyroZ, self.pointerGyroW = extract_euler(self.pointer_q)
        self.middleGyroX, self.middleGyroY, self.middleGyroZ, self.middleGyroW = extract_euler(self.middle_q)
        self.ringGyroX, self.ringGyroY, self.ringGyroZ, self.ringGyroW = extract_euler(self.ring_q)
        self.pinkyGyroX, self.pinkyGyroY, self.pinkyGyroZ, self.pinkyGyroW = extract_euler(self.pinky_q)

        thumbRelativeOrientation = [((self.thumbGyroX - self.wristGyroDegX) + 360) % 360,
                                    ((self.thumbGyroY + self.wristGyroDegZ) + 360) % 360,
                                    ((self.thumbGyroZ - self.wristGyroDegY) + 360) % 360]
        self.thumb.setOrientation(*thumbRelativeOrientation)

        pointerRelativeOrientation = [((self.pointerGyroX - self.wristGyroDegX) + 360) % 360,
                                      ((self.pointerGyroY + self.wristGyroDegZ) + 360) % 360,
                                      ((self.pointerGyroZ - self.wristGyroDegY) + 360) % 360]
        self.pointer.setOrientation(*pointerRelativeOrientation)

        middleRelativeOrientation = [((self.middleGyroX - self.wristGyroDegX) + 360) % 360,
                                     ((self.middleGyroY + self.wristGyroDegZ) + 360) % 360,
                                     ((self.middleGyroZ - self.wristGyroDegY) + 360) % 360]
        self.middle.setOrientation(*middleRelativeOrientation)

        ringRelativeOrientation = [((self.ringGyroX - self.wristGyroDegX) + 360) % 360,
                                   ((self.ringGyroY + self.wristGyroDegZ) + 360) % 360,
                                   ((self.ringGyroZ - self.wristGyroDegY) + 360) % 360]
        self.ring.setOrientation(*ringRelativeOrientation)

        pinkyRelativeOrientation = [((self.pinkyGyroX - self.wristGyroDegX) + 360) % 360,
                                    ((self.pinkyGyroY + self.wristGyroDegZ) + 360) % 360,
                                    ((self.pinkyGyroZ - self.wristGyroDegY) + 360) % 360]
        self.pinky.setOrientation(*pinkyRelativeOrientation)

        return

    def zeroOrientation(self):
        self.orientation_q = Rotation.identity()
        self.wristGyroDegX = 0
        self.wristGyroDegY = 0
        self.wristGyroDegZ = 0
        self.thumb.zeroOrientation()
        self.pointer.zeroOrientation()
        self.middle.zeroOrientation()
        self.ring.zeroOrientation()
        self.pinky.zeroOrientation()

        self.thumbGyroX = 0
        self.thumbGyroY = 0
        self.thumbGyroZ = 0

        self.pointerGyroX = 0
        self.pointerGyroY = 0
        self.pointerGyroZ = 0

        self.middleGyroX = 0
        self.middleGyroY = 0
        self.middleGyroZ = 0

        self.ringGyroX = 0
        self.ringGyroY = 0
        self.ringGyroZ = 0

        self.pinkyGyroX = 0
        self.pinkyGyroY = 0
        self.pinkyGyroZ = 0

        self.thumb_q = Rotation.identity()
        self.pointer_q = Rotation.identity()
        self.middle_q = Rotation.identity()
        self.ring_q = Rotation.identity()
        self.pinky_q = Rotation.identity()

        return

    def getOrientation(self):
        return [self.wristGyroDegX, self.wristGyroDegY, self.wristGyroDegZ]

    def getRelativeOrientations(self):
        relativeOrientations = (self.thumb.getOrientation() + self.pointer.getOrientation() +
                               self.middle.getOrientation() + self.ring.getOrientation() + self.pinky.getOrientation())
        return relativeOrientations

    def getJ0Angles(self):
        # all of this math is deceivingly simple and the proof involves:
        # 1. making the assumption that the finger's 2 forward joints (1 in the case of the thumb)
        # all rotate around 1 axis and thus lie on one plane
        # 2. finding this plane using the X, Y, Z orientation of the distal segment and the reversed-rotation axis
        # of the 2 forward joints (1 in the case of the thumb) all relative to the angle of the back of the hand (wrist)
        # 3. reverse-transforming this rotation inside of the finger's plane to get the rotation of the base segment
        # around the finger's rotation axis
        # 4. converting this rotation back from the finger's plane to the domain where we can determine a base-segment
        # angle relative to the wrist's plane (assuming the wrist runs forward along the Y-axis for simplicity).

        relativeOrientations = self.getRelativeOrientations()
        thumbJ0X = (relativeOrientations[0] - self.thumb.getJ1Flex() + 360) % 360
        thumbJ0Y = relativeOrientations[1]
        thumbJ0Z = relativeOrientations[2]

        pointerJ0X = (relativeOrientations[3] - self.pointer.getJ1Flex() - self.pointer.getJ2Flex() + 360) % 360
        pointerJ0Y = relativeOrientations[4]
        pointerJ0Z = relativeOrientations[5]

        #pointerJ0X = (self.pointerGyroX - self.pointer.getJ1Flex() - self.pointer.getJ2Flex() + 360) % 360
        #pointerJ0Y = self.pointerGyroY
        #pointerJ0Z = self.pointerGyroZ

        middleJ0X = (relativeOrientations[6] - self.middle.getJ1Flex() - self.middle.getJ2Flex() + 360) % 360
        middleJ0Y = relativeOrientations[7]
        middleJ0Z = relativeOrientations[8]

        ringJ0X = (relativeOrientations[9] - self.ring.getJ1Flex() - self.ring.getJ2Flex() + 360) % 360
        ringJ0Y = relativeOrientations[10]
        ringJ0Z = relativeOrientations[11]

        pinkyJ0X = (relativeOrientations[12] - self.pinky.getJ1Flex() - self.pinky.getJ2Flex() + 360) % 360
        pinkyJ0Y = relativeOrientations[13]
        pinkyJ0Z = relativeOrientations[14]

        j0Angles = [thumbJ0X, thumbJ0Y, thumbJ0Z, pointerJ0X, pointerJ0Y, pointerJ0Z, middleJ0X, middleJ0Y, middleJ0Z,
                    ringJ0X, ringJ0Y, ringJ0Z, pinkyJ0X, pinkyJ0Y, pinkyJ0Z]
        return j0Angles

    def getOrientationQ(self):
        q = self.orientation_q.as_quat()  # [x, y, z, w]
        return [q[0], q[1], q[2], q[3]]

    def getRelativeOrientationsQ(self):
        R_remap = Rotation.from_euler('x', -90, degrees=True)
        wrist_remapped = self.orientation_q.inv() * R_remap

        def rel_q(finger_q, j1=0.0, j2=0.0):
            rel = wrist_remapped * finger_q
            flex_correction = Rotation.from_euler('x', (j1 + j2), degrees=True)
            corrected = rel * flex_correction
            q = corrected.as_quat()
            return [q[0], q[1], q[2], q[3]]

        return (
                rel_q(self.thumb_q, self.thumb.getJ1Flex()) +
                rel_q(self.pointer_q, self.pointer.getJ1Flex(), self.pointer.getJ2Flex()) +
                rel_q(self.middle_q, self.middle.getJ1Flex(), self.middle.getJ2Flex()) +
                rel_q(self.ring_q, self.ring.getJ1Flex(), self.ring.getJ2Flex()) +
                rel_q(self.pinky_q, self.pinky.getJ1Flex(), self.pinky.getJ2Flex())
        )



