import numpy as np


def smooth_l1(x, epsilon=1e-4):
    """
    Smooth L1 (pseudo-Huber) norm — differentiable everywhere.
    Approximates ||x||₁ but with a smooth transition near zero,
    giving L-BFGS-B a valid gradient throughout optimisation.
    """
    return np.sum(np.sqrt(x ** 2 + epsilon) - np.sqrt(epsilon))


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


def count_points(episodes):
    return sum(len(ep) for ep in episodes)


def loss_bias_from_stationary(b, stationary_episodes):
    """
    Phase 1 loss — fit b from stationary recordings only.

    When the glove is stationary, true angular velocity is zero.
    Therefore w_corr = A@w + b = I@w + b should also be zero.
    The mean of w over a stationary episode equals the DC bias.
    Minimising the mean squared corrected velocity gives us b directly.

    Loss = (1/N) * Σ_episodes ||mean(w + b)||²

    Parameters
    ----------
    b : np.ndarray, shape (3,)
    stationary_episodes : list of pd.DataFrame
        Episodes recorded with glove completely still.

    Returns
    -------
    float
    """
    N = count_points(stationary_episodes)
    loss = 0.0
    for ep in stationary_episodes:
        omega = ep[['wx', 'wy', 'wz']].values
        mean_corrected = np.mean(omega, axis=0) + b
        loss += np.sum(mean_corrected ** 2)
    return loss / N


def loss_trajectory_linear(params, episodes, b_fixed, lambda_A=1e-3):
    """
    Phase 2 loss — fit A with b fixed from phase 1.

    Loss = (1/N) * Σ_episodes (1/T) * ||∫(A@w + b)dt||²
         + lambda_A * smooth_l1(A - I)

    Normalising by episode duration T makes the loss rate-based,
    so episodes of different lengths contribute equally and A cannot
    learn duration-specific corrections.

    Parameters
    ----------
    params : np.ndarray, shape (9,)
        Flattened A matrix.
    episodes : list of pd.DataFrame
        Trajectory episodes (closed-loop, start == end orientation).
    b_fixed : np.ndarray, shape (3,)
        Bias vector fixed from phase 1.
    lambda_A : float
        Smooth-L1 penalty on A deviating from identity.

    Returns
    -------
    float
    """
    A = params[:9].reshape(3, 3)
    N = count_points(episodes)

    drift_loss = 0.0
    for ep in episodes:
        T = ep['timestamp'].iloc[-1] - ep['timestamp'].iloc[0]
        theta = integrate_episode(ep, A, b_fixed)
        # drift_loss += np.sum((theta / T) ** 2)
        drift_loss += smooth_l1(theta / T)
    drift_loss /= N

    reg_A = lambda_A * smooth_l1(A - np.eye(3))
    return drift_loss + reg_A


def loss_trajectory_quadratic(params, episodes, b_fixed, lambda_A=1e-3, lambda_B=1e-2):
    """
    Phase 2 loss — fit A and B with b fixed from phase 1.

    Loss = (1/N) * Σ_episodes (1/T) * ||∫(A@w + B@w² + b)dt||²
         + lambda_A * smooth_l1(A - I)
         + lambda_B * smooth_l1(B)

    B is penalised more heavily than A so it only activates when
    the linear term is genuinely insufficient.

    Parameters
    ----------
    params : np.ndarray, shape (18,)
        [A (9, row-major), B (9, row-major)]
    episodes : list of pd.DataFrame
    b_fixed : np.ndarray, shape (3,)
    lambda_A : float
    lambda_B : float

    Returns
    -------
    float
    """
    A = params[:9].reshape(3, 3)
    B = params[9:18].reshape(3, 3)
    N = count_points(episodes)

    drift_loss = 0.0
    for ep in episodes:
        T = ep['timestamp'].iloc[-1] - ep['timestamp'].iloc[0]
        theta = integrate_episode(ep, A, b_fixed, B)
        # drift_loss += np.sum((theta / T) ** 2)
        drift_loss += smooth_l1(theta / T)
    drift_loss /= N

    reg_A = lambda_A * smooth_l1(A - np.eye(3))
    reg_B = lambda_B * smooth_l1(B)
    return drift_loss + reg_A + reg_B