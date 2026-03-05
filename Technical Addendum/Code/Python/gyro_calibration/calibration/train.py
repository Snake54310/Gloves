import numpy as np
from scipy.optimize import minimize
from gyro_calibration.calibration.loss import total_loss_quadratic


def train_with_quadratic(episodes):
    """
    Fit the quadratic gyro calibration model to a set of training episodes.

    Model:   offset  = w @ A.T + w^2 @ B.T + b
             w_corr  = w_raw - offset
    Objective: minimise sum_episodes ||integral(w_corr dt)||^2

    Parameters
    ----------
    episodes : list of pd.DataFrame
        Training episodes, each with columns: timestamp, wx, wy, wz.

    Returns
    -------
    A_opt : np.ndarray, shape (3, 3)
        Optimised linear correction matrix.
    B_opt : np.ndarray, shape (3, 3)
        Optimised quadratic correction matrix.
    b_opt : np.ndarray, shape (1, 3)
        Optimised bias vector.
    """
    # Initialise at zero offset — A=0 means no initial correction, avoiding the
    # degenerate A=I saddle point where w_corr = w_raw - w_raw = 0.
    A0 = np.zeros((3, 3)).flatten()   # linear coefficients
    B0 = np.zeros((3, 3)).flatten()   # quadratic coefficients
    b0 = np.zeros(3)                  # bias
    params0 = np.concatenate([A0, B0, b0])

    result = minimize(
        total_loss_quadratic,
        params0,
        args=(episodes,),
        method='L-BFGS-B',
        options={'maxiter': 1000, 'ftol': 1e-12, 'gtol': 1e-8},
    )

    if not result.success:
        print(f"Warning: optimisation did not fully converge — {result.message}")

    params_opt = result.x
    A_opt = params_opt[:9].reshape(3, 3)
    B_opt = params_opt[9:18].reshape(3, 3)
    b_opt = params_opt[18:].reshape(1, 3)

    print("Optimisation result:", result.message)
    print("Final loss:", result.fun)
    print("A_opt:\n", A_opt)
    print("B_opt:\n", B_opt)
    print("b_opt:\n", b_opt)

    return A_opt, B_opt, b_opt