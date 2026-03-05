import numpy as np


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

    # Apply correction to every sample: w_corr = A @ w + b (+ B @ w² if quadratic)
    w_corr = (omega @ A.T) + b              # shape (N, 3)
    if B is not None:
        w_corr = w_corr + (omega ** 2) @ B.T

    # Trapezoidal integration: 0.5 * (w[k] + w[k+1]) * dt
    theta = np.sum(0.5 * (w_corr[:-1] + w_corr[1:]) * dt[:, None], axis=0)
    return theta


def count_points(episodes):
    """Total number of samples across all episodes — used to scale loss."""
    return sum(len(ep) for ep in episodes)


def total_loss_linear(params, episodes, lambda_A=1e-3, lambda_b=1e-4):
    """
    Loss for linear model: w_corr = A @ w + b

    Loss = (1/N) * Σ_episodes ||∫w_corr dt||²
         + lambda_A * ||A - I||₁        (LASSO on deviation of A from identity)
         + lambda_b * ||b||₁            (LASSO on bias)

    Scaling by N (total points) makes lambda values dataset-size independent.
    Penalising ||A - I|| rather than ||A|| keeps A near identity,
    preventing the degenerate A→0 solution.

    Parameters
    ----------
    params : np.ndarray, shape (12,)
        [A (9, row-major), b (3)]
    episodes : list of pd.DataFrame
    lambda_A : float
        LASSO penalty weight for A deviation from identity.
    lambda_b : float
        LASSO penalty weight for bias b.

    Returns
    -------
    float
    """
    A = params[:9].reshape(3, 3)
    b = params[9:12]

    N = count_points(episodes)

    # Drift loss — scaled by total number of points

    drift_loss = 0.0
    for ep in episodes:
        theta = integrate_episode(ep, A, b)
        drift_loss += np.sum(theta ** 2)
        # drift_loss += np.linalg.norm(theta)
    drift_loss /= N


    # LASSO regularization
    # Penalise A deviating from identity (not A itself — keeps scale near 1)
    reg_A = lambda_A * np.sum(np.abs(A - np.eye(3)))
    reg_b = lambda_b * np.sum(np.abs(b))

    return drift_loss + reg_A + reg_b


def total_loss_quadratic(params, episodes, lambda_A=1e-3, lambda_b=1e-4, lambda_B=1e-2):
    """
    Loss for quadratic model: w_corr = A @ w + B @ w² + b

    Loss = (1/N) * Σ_episodes ||∫w_corr dt||²
         + lambda_A * ||A - I||₁     (LASSO on A deviation from identity)
         + lambda_b * ||b||₁         (LASSO on bias)
         + lambda_B * ||B||₁         (LASSO on B — penalised more than A)

    B is penalised more heavily than A (lambda_B > lambda_A) because
    the quadratic term should only activate when linear correction is
    genuinely insufficient — it has more capacity to overfit.

    Parameters
    ----------
    params : np.ndarray, shape (21,)
        [A (9, row-major), b (3), B (9, row-major)]
    episodes : list of pd.DataFrame
    lambda_A : float
        LASSO penalty weight for A deviation from identity.
    lambda_b : float
        LASSO penalty weight for bias b.
    lambda_B : float
        LASSO penalty weight for B (higher-order, penalised more).

    Returns
    -------
    float
    """
    A = params[:9].reshape(3, 3)
    b = params[9:12]
    B = params[12:21].reshape(3, 3)

    N = count_points(episodes)

    # Drift loss — scaled by total number of points
    drift_loss = 0.0
    for ep in episodes:
        theta = integrate_episode(ep, A, b, B)
        drift_loss += np.sum(theta ** 2)
        # drift_loss += np.linalg.norm(theta)
    drift_loss /= N

    # LASSO regularization — B penalised more than A
    reg_A = lambda_A * np.sum(np.abs(A - np.eye(3)))
    reg_b = lambda_b * np.sum(np.abs(b))
    reg_B = lambda_B * np.sum(np.abs(B))  # higher penalty for quadratic term

    return drift_loss + reg_A + reg_b + reg_B