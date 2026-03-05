import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from gyro_calibration.calibration.train import train_linear, train_quadratic
from gyro_calibration.calibration.loss import integrate_episode
from gyro_calibration.calibration.evaluate import evaluate, A_RAW, b_RAW

CSV_PATH = "gyro_calibration/data/raw/gyro_log.csv"


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


def mean_drift_norm(episodes, A, b, B=None):
    return np.mean([
        np.linalg.norm(integrate_episode(ep, A, b, B=B))
        for ep in episodes
    ])


def main():
    # 1) Load and extract episodes
    df = load_and_clean_csv(CSV_PATH)
    episodes = extract_episodes(df)

    if len(episodes) < 4:
        print("Warning: very few episodes found. Check markers/timestamps.")
        return

    # 2) Train/test split
    train_eps, test_eps = train_test_split(episodes, test_size=0.3, random_state=42)
    print(f"Total: {len(episodes)}  Train: {len(train_eps)}  Test: {len(test_eps)}")

    # 3) Fit linear model
    # Tune lambda_A and lambda_b if needed:
    #   - increase lambda_A if A drifts far from identity
    #   - decrease lambda_A if drift correction is too weak
    A_lin, b_lin = train_linear(train_eps, lambda_A=1e-3, lambda_b=1e-4)

    # 4) Fit quadratic model — uses same data, no re-collection needed
    # lambda_B > lambda_A so B only grows if it genuinely helps
    A_quad, b_quad, B_quad = train_quadratic(train_eps, lambda_A=1e-3, lambda_b=1e-4, lambda_B=1e-2)

    # 5) Summary statistics on test set
    raw_norm  = mean_drift_norm(test_eps, A_RAW, b_RAW)
    lin_norm  = mean_drift_norm(test_eps, A_lin,  b_lin)
    quad_norm = mean_drift_norm(test_eps, A_quad, b_quad, B=B_quad)

    print("\n=== SUMMARY (mean drift norm — test episodes) ===")
    print(f"  Raw:       {raw_norm:.6f} rad  ({np.degrees(raw_norm):.4f} deg)")
    print(f"  Linear:    {lin_norm:.6f} rad  ({np.degrees(lin_norm):.4f} deg)"
          f"  [{(1 - lin_norm / raw_norm):.2%} reduction]")
    print(f"  Quadratic: {quad_norm:.6f} rad  ({np.degrees(quad_norm):.4f} deg)"
          f"  [{(1 - quad_norm / raw_norm):.2%} reduction]")

    if quad_norm < lin_norm * 0.9:
        print("\n  → Quadratic gives >10% improvement over linear. Use quadratic model.")
        print("  → Copy A_quad, b_quad, B_quad into updateOrientation.")
    else:
        print("\n  → Linear model is sufficient. Quadratic adds little benefit.")
        print("  → Copy A_lin, b_lin into updateOrientation.")

    # 6) Detailed per-episode output (first 5 test episodes)
    print("\n--- Detailed evaluate() — linear model ---")
    evaluate(test_eps, A_lin, b_lin, B=None)

    print("\n--- Detailed evaluate() — quadratic model ---")
    evaluate(test_eps, A_quad, b_quad, B=B_quad)


if __name__ == "__main__":
    main()