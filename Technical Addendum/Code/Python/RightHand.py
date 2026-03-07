import math
import numpy as np

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

        self.A_opt = np.array([[ 9.97332628e-01,  1.12050378e-04, -7.33705329e-04],
             [ 2.45214985e-04,  9.97270863e-01,  1.70131172e-03],
             [-6.52609217e-04,  6.82822342e-04,  9.95507970e-01]])

        self.B_opt =  np.array([[ 0.00167398, -0.03091576, -0.00195969],
             [ 0.00710383,  0.00684584,  0.00386646],
             [ 0.00752961, -0.01747535,  0.00112488]])

        self.b_opt = np.array([-0.01106485, -0.00100655, -0.00118413])

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
        # Construct raw gyro vector
        gyro_raw = np.array([wristGyroRadssX, wristGyroRadssY, wristGyroRadssZ])

        # Apply quadratic calibration: corrected = raw - (A @ raw + B @ raw² + b)
        gyro_corrected = (
                self.A_opt @ gyro_raw
                + self.B_opt @ (gyro_raw ** 2)
                + self.b_opt.flatten()
        )

        # NOTE: SENSOR X_rotation on wrist is in -X direction in animation window
        # NOTE: Sensor Y and Z rotations are swapped
        # NOTE: After swapping Sensor Y and Z with window Z and Y, Sensor data for Z in window is reversed (-Z direction)

        self.wristGyroDegX = (self.wristGyroDegX - ((gyro_corrected[0] / self.sampleRate) * 180 / math.pi) + 360) % 360
        self.wristGyroDegY = (self.wristGyroDegY + ((gyro_corrected[2] / self.sampleRate) * 180 / math.pi) + 360) % 360
        self.wristGyroDegZ = (self.wristGyroDegZ - ((gyro_corrected[1] / self.sampleRate) * 180 / math.pi) + 360) % 360

        return

    def updateOrientationFingers(self, thumbX, thumbY, thumbZ, pointerX, pointerY, pointerZ,
                                 middleX, middleY, middleZ, ringX, ringY, ringZ, pinkyX, pinkyY, pinkyZ):
        self.thumbGyroX = (self.thumbGyroX - ((thumbY / self.sampleRate) * 180 / math.pi) + 360) % 360
        self.thumbGyroY = (self.thumbGyroY + ((thumbX / self.sampleRate) * 180 / math.pi) + 360) % 360
        self.thumbGyroZ = (self.thumbGyroZ + ((thumbZ / self.sampleRate) * 180 / math.pi) + 360) % 360

        self.pointerGyroX = (self.pointerGyroX - ((pointerY / self.sampleRate) * 180 / math.pi) + 360) % 360
        self.pointerGyroY = (self.pointerGyroY + ((pointerX / self.sampleRate) * 180 / math.pi) + 360) % 360
        self.pointerGyroZ = (self.pointerGyroZ + ((pointerZ / self.sampleRate) * 180 / math.pi) + 360) % 360

        self.middleGyroX = (self.middleGyroX - ((middleY / self.sampleRate) * 180 / math.pi) + 360) % 360
        self.middleGyroY = (self.middleGyroY + ((middleX / self.sampleRate) * 180 / math.pi) + 360) % 360
        self.middleGyroZ = (self.middleGyroZ + ((middleZ / self.sampleRate) * 180 / math.pi) + 360) % 360

        self.ringGyroX = (self.ringGyroX - ((ringY / self.sampleRate) * 180 / math.pi) + 360) % 360
        self.ringGyroY = (self.ringGyroY + ((ringX / self.sampleRate) * 180 / math.pi) + 360) % 360
        self.ringGyroZ = (self.ringGyroZ + ((ringZ / self.sampleRate) * 180 / math.pi) + 360) % 360

        self.pinkyGyroX = (self.pinkyGyroX - ((pinkyY / self.sampleRate) * 180 / math.pi) + 360) % 360
        self.pinkyGyroY = (self.pinkyGyroY + ((pinkyX / self.sampleRate) * 180 / math.pi) + 360) % 360
        self.pinkyGyroZ = (self.pinkyGyroZ + ((pinkyZ / self.sampleRate) * 180 / math.pi) + 360) % 360

        thumbRelativeOrienation = [((self.thumbGyroX - self.wristGyroDegX) + 360) % 360,
                                   ((self.thumbGyroY + self.wristGyroDegZ) + 360) % 360,
                                   ((self.thumbGyroZ - self.wristGyroDegY) + 360) % 360]

        self.thumb.setOrientation(thumbRelativeOrienation[0], thumbRelativeOrienation[1], thumbRelativeOrienation[2])

        self.thumb.setOrientation(thumbRelativeOrienation[0], thumbRelativeOrienation[1], thumbRelativeOrienation[2])

        pointerRelativeOrienation = [((self.pointerGyroX - self.wristGyroDegX) + 360) % 360, # self.pointerGyroX - self.wristGyroDegX
                                     ((self.pointerGyroY + self.wristGyroDegZ) + 360) % 360, # self.pointerGyroY + self.wristGyroDegZ
                                   #((self.pointerGyroY + ((self.wristGyroDegZ + 180) % 360 - 180) * math.sqrt(3) / 2 + ((self.wristGyroDegY + 180) % 360 - 180) * 1 / 2) + 360) % 360, # self.pointerGyroY + self.wristGyroDegZ
                                     ((self.pointerGyroZ - self.wristGyroDegY) + 360) % 360] # self.pointerGyroZ - self.wristGyroDegY

        self.pointer.setOrientation(pointerRelativeOrienation[0], pointerRelativeOrienation[1], pointerRelativeOrienation[2])

        middleRelativeOrienation = [((self.middleGyroX - self.wristGyroDegX) + 360) % 360,
                                    ((self.middleGyroY + self.wristGyroDegZ) + 360) % 360,
                                    ((self.middleGyroZ - self.wristGyroDegY) + 360) % 360]

        self.middle.setOrientation(middleRelativeOrienation[0], middleRelativeOrienation[1],
                                   middleRelativeOrienation[2])

        ringRelativeOrienation = [((self.ringGyroX - self.wristGyroDegX) + 360) % 360,
                                  ((self.ringGyroY + self.wristGyroDegZ) + 360) % 360,
                                  ((self.ringGyroZ - self.wristGyroDegY) + 360) % 360]

        self.ring.setOrientation(ringRelativeOrienation[0], ringRelativeOrienation[1], ringRelativeOrienation[2])

        pinkyRelativeOrienation = [((self.pinkyGyroX - self.wristGyroDegX) + 360) % 360,
                                   ((self.pinkyGyroY + self.wristGyroDegZ) + 360) % 360,
                                   ((self.pinkyGyroZ - self.wristGyroDegY) + 360) % 360]

        self.pinky.setOrientation(pinkyRelativeOrienation[0], pinkyRelativeOrienation[1], pinkyRelativeOrienation[2])

        return

    def zeroOrientation(self):
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
        return

    def getOrientation(self):
        return [self.wristGyroDegX + 90, self.wristGyroDegY, self.wristGyroDegZ]

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






