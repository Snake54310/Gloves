import numpy as np


def smooth_l1(x, epsilon=1e-4):
    """
    Smooth L1 (pseudo-Huber) norm — differentiable everywhere.

    Approximates L1 (||x||₁) but with a smooth transition near zero,
    giving L-BFGS-B a valid gradient throughout optimisation.

    Parameters
    ----------
    x : np.ndarray
    epsilon : float
        Smoothing parameter. Smaller = closer to true L1.

    Returns
    -------
    float
    """
    return np.sum(np.sqrt(x ** 2 + epsilon) - np.sqrt(epsilon))


def integrate_episode(ep, A, b, B=None):
    """
    Apply correction and integrate one episode using the trapezoidal rule.

    Correction model:
        Linear:    w_corr = A @ w + b
        Quadratic: w_corr = A @ w + B @ w² + b

    Since every episode is a guaranteed closed-orientation loop
    (glove is zeroed at start and end), the true integral is zero.
    Any residual is drift.

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
    omega = ep[['wx', 'wy', 'wz']].values  # shape (N, 3)
    dt = np.diff(t)                         # shape (N-1,)

    # Apply correction: w_corr = A @ w + b (+ B @ w² if quadratic)
    w_corr = (omega @ A.T) + b
    if B is not None:
        w_corr = w_corr + (omega ** 2) @ B.T

    # Trapezoidal integration: 0.5 * (w[k] + w[k+1]) * dt
    theta = np.sum(0.5 * (w_corr[:-1] + w_corr[1:]) * dt[:, None], axis=0)
    return theta


def count_points(episodes):
    """Total number of samples across all episodes — used to scale loss."""
    return sum(len(ep) for ep in episodes)


def total_loss_bias_only(b, episodes):
    """
    Loss for bias-only model: w_corr = I @ w + b = w + b
    A is fixed to identity. Used in stage 1 of two-stage training.

    Parameters
    ----------
    b : np.ndarray, shape (3,)
    episodes : list of pd.DataFrame

    Returns
    -------
    float
    """
    A = np.eye(3)
    N = count_points(episodes)

    drift_loss = 0.0
    for ep in episodes:
        theta = integrate_episode(ep, A, b)
        drift_loss += np.sum(theta ** 2)
    return drift_loss / N


def total_loss_linear(params, episodes, lambda_A=1e-3, lambda_b=1e-4):
    """
    Loss for linear model: w_corr = A @ w + b

    Loss = (1/N) * Σ_episodes ||∫w_corr dt||²
         + lambda_A * smooth_l1(A - I)
         + lambda_b * smooth_l1(b)

    Penalises A deviating from identity (not A itself), so scale
    stays near 1 and the degenerate A→0 solution is prevented.
    Scaled by N so lambda values are dataset-size independent.

    Parameters
    ----------
    params : np.ndarray, shape (12,)
        [A (9, row-major), b (3)]
    episodes : list of pd.DataFrame
    lambda_A : float
    lambda_b : float

    Returns
    -------
    float
    """
    A = params[:9].reshape(3, 3)
    b = params[9:12]
    N = count_points(episodes)

    drift_loss = 0.0
    # In total_loss_linear and total_loss_quadratic:
    for ep in episodes:
        T = ep['timestamp'].iloc[-1] - ep['timestamp'].iloc[0]
        theta = integrate_episode(ep, A, b)
        drift_loss += np.sum((theta / T) ** 2)  # normalize by duration
    #drift_loss /= N

    reg_A = lambda_A * smooth_l1(A - np.eye(3))
    reg_b = lambda_b * smooth_l1(b)

    return drift_loss + reg_A + reg_b


def total_loss_quadratic(params, episodes, lambda_A=1e-3, lambda_b=1e-4, lambda_B=1e-2):
    """
    Loss for quadratic model: w_corr = A @ w + B @ w² + b

    B is penalised more heavily than A so it only activates when the
    linear term is genuinely insufficient.

    Parameters
    ----------
    params : np.ndarray, shape (21,)
        [A (9, row-major), b (3), B (9, row-major)]
    episodes : list of pd.DataFrame
    lambda_A : float
    lambda_b : float
    lambda_B : float
        Higher-order penalty — should be larger than lambda_A.

    Returns
    -------
    float
    """
    A = params[:9].reshape(3, 3)
    b = params[9:12]
    B = params[12:21].reshape(3, 3)
    N = count_points(episodes)

    drift_loss = 0.0
    # In total_loss_linear and total_loss_quadratic:
    for ep in episodes:
        T = ep['timestamp'].iloc[-1] - ep['timestamp'].iloc[0]
        theta = integrate_episode(ep, A, b, B)
        drift_loss += np.sum((theta / T) ** 2)  # normalize by duration
    #drift_loss /= N

    reg_A = lambda_A * smooth_l1(A - np.eye(3))
    reg_b = lambda_b * smooth_l1(b)
    reg_B = lambda_B * smooth_l1(B)  # higher penalty for quadratic term

    return drift_loss + reg_A + reg_b + reg_B