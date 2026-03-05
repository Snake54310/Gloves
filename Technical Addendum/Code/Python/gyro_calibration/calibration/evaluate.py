import numpy as np
from gyro_calibration.calibration.loss import integrate_episode

# Raw baseline: A=I, b=0 — signal passes through untouched
A_RAW = np.eye(3)
b_RAW = np.zeros(3)


def evaluate(episodes, A, b, B=None, n_episodes=5):
    """
    Print per-episode comparison of raw vs corrected integrated drift.

    Parameters
    ----------
    episodes : list of pd.DataFrame
    A : np.ndarray, shape (3, 3)
    b : np.ndarray, shape (3,)
    B : np.ndarray, shape (3, 3), optional
    n_episodes : int
    """
    raw_norms  = []
    corr_norms = []

    for i, ep in enumerate(episodes[:n_episodes]):
        raw       = integrate_episode(ep, A_RAW, b_RAW, B=None)
        corrected = integrate_episode(ep, A, b, B=B)

        print(f"\nEpisode {i}")
        print(f"  Raw drift       (rad): {raw}")
        print(f"  Raw drift       (deg): {np.degrees(raw)}")
        print(f"  Corrected drift (rad): {corrected}")
        print(f"  Corrected drift (deg): {np.degrees(corrected)}")
        print(f"  Norm  raw: {np.linalg.norm(raw):.6f} rad  |  "
              f"corrected: {np.linalg.norm(corrected):.6f} rad")

        raw_norms.append(np.linalg.norm(raw))
        corr_norms.append(np.linalg.norm(corrected))

    raw_norms  = np.array(raw_norms)
    corr_norms = np.array(corr_norms)

    if len(raw_norms) > 0 and raw_norms.mean() > 0:
        reduction = 1.0 - corr_norms.mean() / raw_norms.mean()
        print(f"\nMean raw norm:        {raw_norms.mean():.6f} rad")
        print(f"Mean corrected norm:  {corr_norms.mean():.6f} rad")
        print(f"Fractional reduction: {reduction:.2%}")