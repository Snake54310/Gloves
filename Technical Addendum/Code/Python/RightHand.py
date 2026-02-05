import math


class Thumb:
    def __init__(self, segment1Length, segment2Length): # segments progressive from base
        self.seg1Len = segment1Length
        self.seg2Len = segment2Length
        self.j1flex = 0.0 # angle of joint between segments 1 and 2

    def setJ1Flex(self, newJ1Flex):
        self.j1flex = newJ1Flex
        return

    def getJ1Flex(self):
        return self.j1flex

    def getSegLens(self):
        return [self.seg1Len, self.seg2Len]


class Pointer:
    def __init__(self, segment1Length, segment2Length, segment3Length): # segments progressive from base
        self.seg1Len = segment1Length
        self.seg2Len = segment2Length
        self.seg3Len = segment3Length
        self.j1flex = 0.0  # angle of joint between segments 1 and 2
        self.j2flex = 0.0  # angle of joint between segments 2 and 3

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


class Middle:
    def __init__(self, segment1Length, segment2Length, segment3Length): # segments progressive from base
        self.seg1Len = segment1Length
        self.seg2Len = segment2Length
        self.seg3Len = segment3Length
        self.j1flex = 0.0  # angle of joint between segments 1 and 2
        self.j2flex = 0.0  # angle of joint between segments 2 and 3

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


class Ring:
    def __init__(self, segment1Length, segment2Length, segment3Length): # segments progressive from base
        self.seg1Len = segment1Length
        self.seg2Len = segment2Length
        self.seg3Len = segment3Length
        self.j1flex = 0.0  # angle of joint between segments 1 and 2
        self.j2flex = 0.0  # angle of joint between segments 2 and 3

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


class Pinky:
    def __init__(self, segment1Length, segment2Length, segment3Length): # segments progressive from base
        self.seg1Len = segment1Length
        self.seg2Len = segment2Length
        self.seg3Len = segment3Length
        self.j1flex = 0.0  # angle of joint between segments 1 and 2
        self.j2flex = 0.0  # angle of joint between segments 2 and 3

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


class RightHand: # NOTE: if two distinct hand classes are not necessary, backtrack and re-write this for the general case
    def __init__(self):
        self.thumb = Thumb(1.625, 1.4375)
        self.pointer = Pointer(2.0, 1.25, 1.0)
        self.middle = Middle(2.5, 1.375, 1.0)
        self.ring = Ring(2.25, 1.375, 1.0)
        self.pinky = Pinky(1.375, 1.0, 1.0)

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











