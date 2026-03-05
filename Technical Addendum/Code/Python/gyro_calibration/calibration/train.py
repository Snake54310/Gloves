import numpy as np
from scipy.optimize import minimize
from gyro_calibration.calibration.loss import (
    loss_bias_from_stationary,
    loss_trajectory_linear,
    loss_trajectory_quadratic,
)


def _run_minimize(loss_fn, params0, args, label):
    """Helper: run L-BFGS-B and report convergence."""
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


def fit_bias(stationary_episodes):
    """
    Phase 1 — fit bias b from stationary recordings only.

    When the glove is completely still, true angular velocity is zero.
    Any nonzero reading is pure sensor bias. This gives a physically
    grounded b that generalises across all trajectory episodes.

    Parameters
    ----------
    stationary_episodes : list of pd.DataFrame
        Episodes recorded with glove completely still.

    Returns
    -------
    b : np.ndarray, shape (3,)
    """
    print("\n=== PHASE 1 — Fit bias from stationary data ===")
    b0 = np.zeros(3)
    b_opt = _run_minimize(
        loss_bias_from_stationary,
        b0,
        args=(stationary_episodes,),
        label="Phase 1 (bias)",
    )
    print(f"  b: {b_opt}")
    return b_opt


def train_linear(trajectory_episodes, b_fixed, lambda_A=1e-3):
    """
    Phase 2 — fit linear correction A with b fixed from phase 1.

    b is never refitted here — it comes solely from stationary data.
    Only A is free, initialised to identity (no initial correction).

    Parameters
    ----------
    trajectory_episodes : list of pd.DataFrame
    b_fixed : np.ndarray, shape (3,)
        Bias fixed from fit_bias(). Never modified here.
    lambda_A : float

    Returns
    -------
    A : np.ndarray, shape (3, 3)
    b : np.ndarray, shape (3,)  — same as b_fixed
    """
    print("\n=== LINEAR MODEL (A only, b fixed from stationary) ===")
    A0 = np.eye(3).flatten()
    params_opt = _run_minimize(
        loss_trajectory_linear,
        A0,
        args=(trajectory_episodes, b_fixed, lambda_A),
        label="Linear",
    )

    A = params_opt[:9].reshape(3, 3)
    print(f"  A:\n{A}")
    print(f"  b (fixed): {b_fixed}")
    return A, b_fixed


def train_quadratic(trajectory_episodes, b_fixed, lambda_A=1e-3, lambda_B=1e-2):
    """
    Phase 2 — fit quadratic correction A and B with b fixed from phase 1.

    b is never refitted here — it comes solely from stationary data.
    A is initialised to identity, B is initialised to zero.
    B is penalised more heavily than A so it only grows if it
    genuinely reduces drift beyond what A alone achieves.

    Parameters
    ----------
    trajectory_episodes : list of pd.DataFrame
    b_fixed : np.ndarray, shape (3,)
        Bias fixed from fit_bias(). Never modified here.
    lambda_A : float
    lambda_B : float

    Returns
    -------
    A : np.ndarray, shape (3, 3)
    b : np.ndarray, shape (3,)  — same as b_fixed
    B : np.ndarray, shape (3, 3)
    """
    print("\n=== QUADRATIC MODEL (A + B, b fixed from stationary) ===")
    A0 = np.eye(3).flatten()
    B0 = np.zeros(9)
    params0 = np.concatenate([A0, B0])
    params_opt = _run_minimize(
        loss_trajectory_quadratic,
        params0,
        args=(trajectory_episodes, b_fixed, lambda_A, lambda_B),
        label="Quadratic",
    )

    A = params_opt[:9].reshape(3, 3)
    B = params_opt[9:18].reshape(3, 3)
    print(f"  A:\n{A}")
    print(f"  b (fixed): {b_fixed}")
    print(f"  B:\n{B}")
    return A, b_fixed, B