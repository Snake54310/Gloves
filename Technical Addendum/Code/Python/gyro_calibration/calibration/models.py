import numpy as np


def apply_transform(omega, A, b, B=None):
    """
    Apply calibration transform to raw angular velocity samples.

    Parameters
    ----------
    omega : np.ndarray, shape (N, 3)
        Raw angular velocity samples.
    A : np.ndarray, shape (3, 3)
        Linear correction matrix.
    b : np.ndarray, shape (1, 3) or (3,)
        Bias vector.
    B : np.ndarray, shape (3, 3), optional
        Quadratic correction matrix. If None, only linear correction is applied.

    Returns
    -------
    np.ndarray, shape (N, 3)
        Predicted offset to subtract from omega.
    """
    # Linear term: omega @ A.T + b
    offset = (omega @ A.T) + np.array(b).reshape(-1)

    # Optional quadratic term: (omega**2) @ B.T
    if B is not None:
        offset = offset + (omega ** 2) @ B.T

    return offset