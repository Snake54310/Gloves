import numpy as np
from scipy.optimize import minimize
from gyro_calibration.calibration.loss import (
    total_loss_bias_only,
    total_loss_linear,
    total_loss_quadratic,
)


def _run_minimize(loss_fn, params0, args, label):
    """Helper to run L-BFGS-B and print convergence info."""
    result = minimize(
        loss_fn,
        params0,
        args=args,
        method='L-BFGS-B',
        options={'maxiter': 2000, 'ftol': 1e-14, 'gtol': 1e-9},
    )
    if not result.success:
        print(f"  Warning ({label}): did not fully converge — {result.message}")
    else:
        print(f"  {label}: {result.message}")
    print(f"  Final loss: {result.fun:.6e}")
    return result.x


def train_linear(episodes, lambda_A=1e-3, lambda_b=1e-4):
    """
    Fit linear correction model: w_corr = A @ w + b

    Two-stage training:
        Stage 1 — fit b only with A fixed to identity.
                   b is a constant offset and cannot hurt test episodes
                   the way A can. Starting here anchors the solution
                   in a physically safe region.
        Stage 2 — fit A and b jointly from the stage 1 result.
                   A can now only improve on what b already achieves,
                   rather than absorbing corrections b should handle.

    Parameters
    ----------
    episodes : list of pd.DataFrame
    lambda_A : float
        Smooth-L1 penalty on A deviating from identity.
    lambda_b : float
        Smooth-L1 penalty on bias magnitude.

    Returns
    -------
    A : np.ndarray, shape (3, 3)
    b : np.ndarray, shape (3,)
    """
    print("\n=== LINEAR MODEL — Stage 1: bias only (A=I fixed) ===")
    b0 = np.zeros(3)
    b_stage1 = _run_minimize(
        total_loss_bias_only,
        b0,
        args=(episodes,),
        label="Stage 1",
    )
    print(f"  b (stage 1): {b_stage1}")

    print("\n=== LINEAR MODEL — Stage 2: joint A + b ===")
    A0 = np.eye(3).flatten()
    params0 = np.concatenate([A0, b_stage1])  # warm-start b from stage 1
    params_opt = _run_minimize(
        total_loss_linear,
        params0,
        args=(episodes, lambda_A, lambda_b),
        label="Stage 2",
    )

    A = params_opt[:9].reshape(3, 3)
    b = params_opt[9:12]

    print(f"  A:\n{A}")
    print(f"  b: {b}")

    return A, b


def train_quadratic(episodes, lambda_A=1e-1, lambda_b=1e-4, lambda_B=1e-2):
    """
    Fit quadratic correction model: w_corr = A @ w + B @ w² + b

    Two-stage training:
        Stage 1 — fit b only (A=I, B=0 fixed).
        Stage 2 — fit A, b, and B jointly from stage 1 result.
                   B is initialised to zero and penalised more heavily
                   than A, so it only grows if genuinely needed.

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
    print("\n=== QUADRATIC MODEL — Stage 1: bias only (A=I, B=0 fixed) ===")
    b0 = np.zeros(3)
    b_stage1 = _run_minimize(
        total_loss_bias_only,
        b0,
        args=(episodes,),
        label="Stage 1",
    )
    print(f"  b (stage 1): {b_stage1}")

    print("\n=== QUADRATIC MODEL — Stage 2: joint A + b + B ===")
    A0 = np.eye(3).flatten()
    B0 = np.zeros(9)
    params0 = np.concatenate([A0, b_stage1, B0])  # warm-start b from stage 1
    params_opt = _run_minimize(
        total_loss_quadratic,
        params0,
        args=(episodes, lambda_A, lambda_b, lambda_B),
        label="Stage 2",
    )

    A = params_opt[:9].reshape(3, 3)
    b = params_opt[9:12]
    B = params_opt[12:21].reshape(3, 3)

    print(f"  A:\n{A}")
    print(f"  b: {b}")
    print(f"  B:\n{B}")

    return A, b, B