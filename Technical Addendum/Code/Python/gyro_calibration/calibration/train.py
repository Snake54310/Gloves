import numpy as np
from scipy.optimize import minimize
from gyro_calibration.calibration.loss import total_loss_linear, total_loss_quadratic


def train_linear(episodes, lambda_A=1e-3, lambda_b=1e-4):
    """
    Fit linear correction model: w_corr = A @ w + b

    A is initialised to identity (no initial correction).
    b is initialised to zero.

    LASSO penalties:
        lambda_A penalises A deviating from identity.
        lambda_b penalises bias magnitude.
    Scaled by total number of points so lambdas are
    dataset-size independent.

    Parameters
    ----------
    episodes : list of pd.DataFrame
    lambda_A : float
    lambda_b : float

    Returns
    -------
    A : np.ndarray, shape (3, 3)
    b : np.ndarray, shape (3,)
    """
    # Initialise at identity + zero bias: no correction applied initially
    A0 = np.eye(3).flatten()
    b0 = np.zeros(3)
    params0 = np.concatenate([A0, b0])

    result = minimize(
        total_loss_linear,
        params0,
        args=(episodes, lambda_A, lambda_b),
        method='L-BFGS-B',
        options={'maxiter': 2000, 'ftol': 1e-14, 'gtol': 1e-9},
    )

    if not result.success:
        print(f"Warning: optimisation did not fully converge — {result.message}")

    A = result.x[:9].reshape(3, 3)
    b = result.x[9:12]

    print("\n=== LINEAR MODEL ===")
    print(f"Optimisation: {result.message}")
    print(f"Final loss:   {result.fun:.6e}")
    print(f"A:\n{A}")
    print(f"b: {b}")

    return A, b


def train_quadratic(episodes, lambda_A=1e-3, lambda_b=1e-4, lambda_B=1e-2):
    """
    Fit quadratic correction model: w_corr = A @ w + B @ w² + b

    B is initialised to zero and penalised more heavily than A,
    so it only grows if it genuinely reduces drift beyond what
    the linear term alone can achieve.

    Parameters
    ----------
    episodes : list of pd.DataFrame
    lambda_A : float
    lambda_b : float
    lambda_B : float
        Higher-order penalty — should be larger than lambda_A.

    Returns
    -------
    A : np.ndarray, shape (3, 3)
    b : np.ndarray, shape (3,)
    B : np.ndarray, shape (3, 3)
    """
    # Initialise A=I, b=0, B=0
    A0 = np.eye(3).flatten()
    b0 = np.zeros(3)
    B0 = np.zeros(9)
    params0 = np.concatenate([A0, b0, B0])

    result = minimize(
        total_loss_quadratic,
        params0,
        args=(episodes, lambda_A, lambda_b, lambda_B),
        method='L-BFGS-B',
        options={'maxiter': 2000, 'ftol': 1e-14, 'gtol': 1e-9},
    )

    if not result.success:
        print(f"Warning: optimisation did not fully converge — {result.message}")

    A = result.x[:9].reshape(3, 3)
    b = result.x[9:12]
    B = result.x[12:21].reshape(3, 3)

    print("\n=== QUADRATIC MODEL ===")
    print(f"Optimisation: {result.message}")
    print(f"Final loss:   {result.fun:.6e}")
    print(f"A:\n{A}")
    print(f"b: {b}")
    print(f"B:\n{B}")

    return A, b, B