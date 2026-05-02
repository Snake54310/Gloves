import numpy as np
from multiprocessing import Pool
import os

# FOR WRIST (-z):
'''
A_REF = np.array([
    [1.,  0.,  0.],
    [0.,  1.,  0.],
    [0.,  0., -1.],
])
'''
# FOR FINGERS:
A_REF = np.array([
    [1., 0.,  0.],
    [0.,  1.,  0.],
    [0.,  0., 1.],
])


def _integrate_linear(args):
    ep, A, b_fixed = args
    T = ep['timestamp'].iloc[-1] - ep['timestamp'].iloc[0]
    theta = integrate_episode(ep, A, b_fixed)
    return smooth_l1(theta / T), len(ep)

def _integrate_quadratic(args):
    ep, A, b_fixed, B = args
    T = ep['timestamp'].iloc[-1] - ep['timestamp'].iloc[0]
    theta = integrate_episode(ep, A, b_fixed, B)
    return smooth_l1(theta / T), len(ep)

def _integrate_bias(args):
    ep, b = args
    omega = ep[['wx', 'wy', 'wz']].values
    mean_corrected = np.mean(omega, axis=0) + b
    return np.sum(mean_corrected ** 2), len(ep)

def smooth_l1(x, epsilon=1e-4):
    """
    Smooth L1 (pseudo-Huber) norm — differentiable everywhere.
    Approximates ||x||₁ but with a smooth transition near zero,
    giving L-BFGS-B a valid gradient throughout optimisation.
    """
    return np.sum(np.sqrt(x ** 2 + epsilon) - np.sqrt(epsilon))

'''
def integrate_episode(ep, A, b, B=None):
    """
    Apply correction and integrate one episode using the trapezoidal rule.

    Correction model:
        Linear:    w_corr = A @ w + b
        Quadratic: w_corr = A @ w + B @ w² + b

    Parameters
    ----------
    ep : pd.DataFrame
        Episode with columns: timestamp, wx, wy, wz.
    A : np.ndarray, shape (3, 3)
    b : np.ndarray, shape (3,)
    B : np.ndarray, shape (3, 3), optional

    Returns
    -------
    np.ndarray, shape (3,)
        Net integrated angle [theta_x, theta_y, theta_z] in radians.
    """
    t = ep['timestamp'].values
    omega = ep[['wx', 'wy', 'wz']].values  # (N, 3)
    dt = np.diff(t)                         # (N-1,)

    w_corr = (omega @ A.T) + b
    if B is not None:
        w_corr = w_corr + (omega ** 2) @ B.T

    # Trapezoidal integration
    theta = np.sum(0.5 * (w_corr[:-1] + w_corr[1:]) * dt[:, None], axis=0)
    return theta

'''
def count_points(episodes):
    return sum(len(ep) for ep in episodes)

def integrate_episode(ep, A, b, B=None):
    t = ep['timestamp'].values
    omega = ep[['wx', 'wy', 'wz']].values
    dt = np.diff(t)

    w_corr = (omega @ A.T) + b
    if B is not None:
        w_corr = w_corr + (omega ** 2) @ B.T

    w_mid = 0.5 * (w_corr[:-1] + w_corr[1:])

    def step(q, i):
        w = w_mid[i]
        angle = np.linalg.norm(w) * dt[i]
        if angle < 1e-10:
            return q
        axis = w / np.linalg.norm(w)
        dq = np.append(axis * np.sin(angle / 2), np.cos(angle / 2))
        x1, y1, z1, w1 = q
        x2, y2, z2, w2 = dq
        return np.array([
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2,
            w1*w2 - x1*x2 - y1*y2 - z1*z2
        ])

    q = np.array([0.0, 0.0, 0.0, 1.0])
    for i in range(len(dt)):
        q = step(q, i)
        q = q / np.linalg.norm(q)
    return q[:3]

def loss_bias_from_stationary(b, stationary_episodes, pool=None):
    args = [(ep, b) for ep in stationary_episodes]
    if pool is not None:
        results = pool.map(_integrate_bias, args)
    else:
        results = [_integrate_bias(a) for a in args]
    N = sum(r[1] for r in results)
    return sum(r[0] for r in results) / N

def loss_trajectory_linear(params, episodes, b_fixed, lambda_A=1e-3, pool=None):
    A = params[:9].reshape(3, 3)
    args = [(ep, A, b_fixed) for ep in episodes]
    if pool is not None:
        results = pool.map(_integrate_linear, args)
    else:
        results = [_integrate_linear(a) for a in args]
    N = sum(r[1] for r in results)
    drift_loss = sum(r[0] for r in results) / N
    return drift_loss + lambda_A * smooth_l1(A - A_REF)  # changed from np.eye(3)

def loss_trajectory_quadratic(params, episodes, b_fixed, lambda_A=1e-3, lambda_B=1e-2, pool=None):
    A = params[:9].reshape(3, 3)
    B = params[9:18].reshape(3, 3)
    args = [(ep, A, b_fixed, B) for ep in episodes]
    if pool is not None:
        results = pool.map(_integrate_quadratic, args)
    else:
        results = [_integrate_quadratic(a) for a in args]
    N = sum(r[1] for r in results)
    drift_loss = sum(r[0] for r in results) / N
    return drift_loss + lambda_A * smooth_l1(A - A_REF) + lambda_B * smooth_l1(B)  # changed