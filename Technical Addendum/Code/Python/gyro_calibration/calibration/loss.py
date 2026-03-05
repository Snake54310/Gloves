import numpy as np
from gyro_calibration.calibration.models import apply_transform


def integrate_episode(ep, A, b, B=None):
    """
    Integrate corrected angular velocity over one episode.

    Correction model: w_corrected = w_raw - apply_transform(w_raw, A, b, B)
    Integration:      theta = sum(w_corrected * dt)

    Parameters
    ----------
    ep : pd.DataFrame
        Episode dataframe with columns: timestamp, wx, wy, wz.
    A : np.ndarray, shape (3, 3)
        Linear correction matrix.
    b : np.ndarray, shape (1, 3) or (3,)
        Bias vector.
    B : np.ndarray, shape (3, 3), optional
        Quadratic correction matrix.

    Returns
    -------
    np.ndarray, shape (3,)
        Integrated angle vector (rad).
    """
    t = ep['timestamp'].values
    omega = ep[['wx', 'wy', 'wz']].values

    dt = np.diff(t)             # shape (N-1,)
    omega = omega[:-1]          # align samples with dt intervals

    # Subtract predicted offset (correction model: w_corr = w_raw - offset)
    offset = apply_transform(omega, A, b, B)
    w_corrected = omega - offset

    theta = np.sum(w_corrected * dt[:, None], axis=0)
    return theta


def total_loss(params, episodes):
    """
    Loss for the linear calibration model: minimise sum of squared integrated drift.

    Parameters
    ----------
    params : np.ndarray, shape (12,)
        Flat array [A (9), b (3)].
    episodes : list of pd.DataFrame
        Training episodes.

    Returns
    -------
    float
        Total squared integrated drift across all episodes.
    """
    A = params[:9].reshape(3, 3)
    b = params[9:].reshape(1, 3)

    total = 0.0
    for ep in episodes:
        theta = integrate_episode(ep, A, b)
        total += np.sum(theta ** 2)
    return total


def total_loss_quadratic(params, episodes):
    """
    Loss for the quadratic calibration model: minimise sum of squared integrated drift.

    Correction model: offset = w @ A.T + w^2 @ B.T + b
                      w_corr  = w_raw - offset
    Loss:             sum over episodes of ||integral(w_corr dt)||^2

    Parameters
    ----------
    params : np.ndarray, shape (21,)
        Flat array [A (9), B (9), b (3)].
    episodes : list of pd.DataFrame
        Training episodes.

    Returns
    -------
    float
        Total squared integrated drift across all episodes.
    """
    A = params[:9].reshape(3, 3)
    B = params[9:18].reshape(3, 3)
    b = params[18:].reshape(1, 3)

    loss = 0.0
    for ep in episodes:
        theta = integrate_episode(ep, A, b, B)
        loss += np.sum(theta ** 2)
    return loss