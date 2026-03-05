import numpy as np
from gyro_calibration.calibration.loss import integrate_episode

# Zero parameters: offset = 0, so omega passes through untouched → raw baseline
A_ZERO = np.zeros((3, 3))
b_ZERO = np.zeros((1, 3))


def evaluate(episodes, A, b, B=None, n_episodes=5):
    """
    Print a per-episode comparison of raw vs. corrected integrated drift.

    Parameters
    ----------
    episodes : list of pd.DataFrame
        Episodes to evaluate.
    A : np.ndarray, shape (3, 3)
        Linear correction matrix.
    b : np.ndarray, shape (1, 3) or (3,)
        Bias vector.
    B : np.ndarray, shape (3, 3), optional
        Quadratic correction matrix. Pass None to use the linear model only.
    n_episodes : int
        Number of episodes to print (default: 5).
    """
    raw_norms = []
    corr_norms = []

    for i, ep in enumerate(episodes[:n_episodes]):
        # Raw: A=zeros so offset=0, omega passes through untouched
        raw = integrate_episode(ep, A_ZERO, b_ZERO, B=None)
        # Corrected: use trained parameters
        corrected = integrate_episode(ep, A, b, B)

        raw_deg = np.degrees(raw)
        corr_deg = np.degrees(corrected)

        print(f"\nEpisode {i}")
        print(f"  Raw drift      (rad): {raw}   (deg): {raw_deg}")
        print(f"  Corrected drift(rad): {corrected}   (deg): {corr_deg}")
        print(f"  Norm  raw: {np.linalg.norm(raw):.6f} rad  |  "
              f"corrected: {np.linalg.norm(corrected):.6f} rad")

        raw_norms.append(np.linalg.norm(raw))
        corr_norms.append(np.linalg.norm(corrected))

    raw_norms = np.array(raw_norms)
    corr_norms = np.array(corr_norms)

    if len(raw_norms) > 0 and raw_norms.mean() > 0:
        reduction = 1.0 - corr_norms.mean() / raw_norms.mean()
        print(f"\nMean raw norm:       {raw_norms.mean():.6f} rad")
        print(f"Mean corrected norm: {corr_norms.mean():.6f} rad")
        print(f"Fractional reduction: {reduction:.2%}")