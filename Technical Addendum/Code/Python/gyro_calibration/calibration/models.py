import numpy as np


def apply_correction(omega, A, b, B=None):
    """
    Apply calibration transform to a single raw gyro sample.

    Linear model:    w_corr = A @ w + b
    Quadratic model: w_corr = A @ w + B @ w² + b

    Parameters
    ----------
    omega : np.ndarray, shape (3,)
        Raw angular velocity [wx, wy, wz] in rad/s.
    A : np.ndarray, shape (3, 3)
    b : np.ndarray, shape (3,)
    B : np.ndarray, shape (3, 3), optional

    Returns
    -------
    np.ndarray, shape (3,)
        Corrected angular velocity.
    """
    corrected = A @ omega + b
    if B is not None:
        corrected = corrected + B @ (omega ** 2)
    return corrected