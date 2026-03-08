import numpy as np
from scipy.optimize import minimize
from gyro_calibration.calibration.loss import (
    loss_bias_from_stationary,
    loss_trajectory_linear,
    loss_trajectory_quadratic,
)

A_REF = np.array([
    [1.,  0.,  0.],
    [0.,  1.,  0.],
    [0.,  0., -1.],
])

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


def fit_bias(stationary_episodes, pool=None):
    print("\n=== PHASE 1 — Fit bias from stationary data ===")
    b0 = np.zeros(3)
    b_opt = _run_minimize(
        loss_bias_from_stationary,
        b0,
        args=(stationary_episodes, pool),
        label="Phase 1 (bias)",
    )
    print(f"  b: {b_opt}")
    return b_opt


def train_linear(trajectory_episodes, b_fixed, lambda_A=1e-3, pool=None):
    print("\n=== LINEAR MODEL (A only, b fixed from stationary) ===")
    A0 = A_REF.flatten()
    params_opt = _run_minimize(
        loss_trajectory_linear,
        A0,
        args=(trajectory_episodes, b_fixed, lambda_A, pool),
        label="Linear",
    )
    A = params_opt[:9].reshape(3, 3)
    print(f"  A:\n{A}")
    print(f"  b (fixed): {b_fixed}")
    return A, b_fixed


def train_quadratic(trajectory_episodes, b_fixed, lambda_A=1e-3, lambda_B=1e-2, pool=None):
    print("\n=== QUADRATIC MODEL (A + B, b fixed from stationary) ===")
    A0 = A_REF.flatten()
    B0 = np.zeros(9)
    params0 = np.concatenate([A0, B0])
    params_opt = _run_minimize(
        loss_trajectory_quadratic,
        params0,
        args=(trajectory_episodes, b_fixed, lambda_A, lambda_B, pool),
        label="Quadratic",
    )
    A = params_opt[:9].reshape(3, 3)
    B = params_opt[9:18].reshape(3, 3)
    print(f"  A:\n{A}")
    print(f"  b (fixed): {b_fixed}")
    print(f"  B:\n{B}")
    return A, b_fixed, B