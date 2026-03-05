from gyro_calibration.calibration.loss import total_loss
import numpy as np
from scipy.optimize import minimize

def train(episodes):
    A0 = np.eye(3).flatten()
    b0 = np.zeros(3)
    params0 = np.concatenate([A0, b0])

    result = minimize(total_loss, params0, args=(episodes,), method='L-BFGS-B')

    params_opt = result.x
    A_opt = params_opt[:9].reshape(3,3)
    b_opt = params_opt[9:]  # shape (3,)

    print("A_opt:\n", A_opt)
    print("b_opt:\n", b_opt)

    return A_opt, b_opt