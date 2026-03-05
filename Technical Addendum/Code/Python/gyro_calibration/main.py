import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from gyro_calibration.calibration.train import train_with_quadratic
from gyro_calibration.calibration.loss import integrate_episode
from gyro_calibration.calibration.evaluate import evaluate

CSV_PATH = "gyro_calibration/data/raw/gyro_log.csv"

# Zero parameters: offset = 0, so omega passes through untouched → raw baseline
A_ZERO = np.zeros((3, 3))
B_ZERO = None
B_ZERO_ARG = None
b_ZERO = np.zeros((1, 3))


def load_and_clean_csv(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    if "marker" in df.columns:
        df["marker"] = df["marker"].astype(str).str.strip().str.lower()
    else:
        df["marker"] = ""
    for c in ["timestamp", "wx", "wy", "wz"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def extract_episodes(df):
    """Sequential scan: open on 'start', close on next 'end'."""
    episodes = []
    current_start = None

    for idx, row in df.reset_index(drop=True).iterrows():
        mark = str(row.get("marker", "")).strip().lower()

        if mark == "start":
            current_start = idx

        elif mark == "end" and current_start is not None:
            ep = df.iloc[current_start: idx + 1].copy()
            if len(ep) >= 2 and ep["timestamp"].iloc[-1] > ep["timestamp"].iloc[0]:
                episodes.append(ep)
            current_start = None

    print(f"Extracted episodes: {len(episodes)}")
    return episodes


def print_episode_results(ep_id, theta_raw, theta_corr):
    deg_raw = np.degrees(theta_raw)
    deg_corr = np.degrees(theta_corr)
    print(f"\nEpisode {ep_id}")
    print(f"  Raw integrated drift       (rad): {theta_raw}")
    print(f"  Corrected integrated drift (rad): {theta_corr}")
    print(f"  Raw integrated drift       (deg): {deg_raw}")
    print(f"  Corrected integrated drift (deg): {deg_corr}")


def main():
    # 1) Load CSV and extract episodes
    df = load_and_clean_csv(CSV_PATH)
    episodes = extract_episodes(df)

    if len(episodes) < 4:
        print("Warning: very few episodes found. Check markers/timestamps.")
        return

    # 2) Split train/test (70/30)
    train_eps, test_eps = train_test_split(episodes, test_size=0.3, random_state=42)
    print(f"Total episodes: {len(episodes)}  Train: {len(train_eps)}  Test: {len(test_eps)}")

    # 3) Train quadratic calibration model on train_eps
    A_opt, B_opt, b_opt = train_with_quadratic(train_eps)

    # 4) Evaluate on held-out test episodes
    print("\n--- Per-episode results (test set) ---")
    for i, ep in enumerate(test_eps):
        # Raw: A=zeros so offset=0, omega passes through untouched
        theta_raw = integrate_episode(ep, A_ZERO, b_ZERO, B=None)
        # Corrected: use trained parameters
        theta_corr = integrate_episode(ep, A_opt, b_opt, B=B_opt)
        print_episode_results(i, theta_raw, theta_corr)

    # 5) Summary statistics
    raw_norms = np.array([
        np.linalg.norm(integrate_episode(ep, A_ZERO, b_ZERO, B=None))
        for ep in test_eps
    ])
    corr_norms = np.array([
        np.linalg.norm(integrate_episode(ep, A_opt, b_opt, B=B_opt))
        for ep in test_eps
    ])

    print("\nSummary (norm of integrated drift over test episodes):")
    print(f"  Mean raw norm:       {raw_norms.mean():.6f} rad")
    print(f"  Mean corrected norm: {corr_norms.mean():.6f} rad")
    if raw_norms.mean() > 0:
        print(f"  Fractional reduction: {(1 - corr_norms.mean() / raw_norms.mean()):.2%}")

    # 6) Verbose per-episode evaluate (first 5 test episodes)
    print("\n--- Detailed evaluate() output ---")
    evaluate(test_eps, A_opt, b_opt, B=B_opt)


if __name__ == "__main__":
    main()