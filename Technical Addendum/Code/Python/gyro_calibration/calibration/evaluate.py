
import numpy as np
from gyro_calibration.calibration.loss import integrate_episode

def evaluate(episodes, A, b):

    for i, ep in enumerate(episodes[:5]):
        raw = integrate_episode(ep, np.eye(3), np.zeros((1,3)))
        corrected = integrate_episode(ep, A, b)

        print(f"\nEpisode {i}")
        print("Raw drift:", raw)
        print("Corrected drift:", corrected)