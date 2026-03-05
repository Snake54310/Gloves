

import numpy as np
from gyro_calibration.calibration.models import apply_transform

def integrate_episode(ep, A, b):
    t = ep['timestamp'].values
    omega = ep[['wx','wy','wz']].values

    dt = np.diff(t)
    omega = omega[:-1]

    corrected = apply_transform(omega, A, b)
    theta = np.sum(corrected * dt[:, None], axis=0)

    return theta


def total_loss(params, episodes):
    A = params[:9].reshape(3,3)
    b = params[9:].reshape(1,3)

    total = 0
    for ep in episodes:
        theta = integrate_episode(ep, A, b)
        total += np.sum(theta**2)

    return total