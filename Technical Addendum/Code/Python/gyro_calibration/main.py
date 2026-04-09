import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
from gyro_calibration.calibration.train import fit_bias, train_linear, train_quadratic
from gyro_calibration.calibration.loss import integrate_episode
from gyro_calibration.calibration.evaluate import evaluate, A_RAW, b_RAW

from multiprocessing import Pool
import os

def mean_drift_norm(episodes, A, b, B=None, pool=None):
    from gyro_calibration.calibration.loss import integrate_episode
    args = [(ep, A, b, B) for ep in episodes]
    if pool is not None:
        results = pool.map(_integrate_norm, args)
    else:
        results = [_integrate_norm(a) for a in args]
    return np.mean(results)

def _integrate_norm(args):
    from gyro_calibration.calibration.loss import integrate_episode
    ep, A, b, B = args
    return np.linalg.norm(integrate_episode(ep, A, b, B))

# ── File paths ────────────────────────────────────────────────────────────────
# Stationary CSV: glove sitting completely still, multiple episodes.
# Trajectory CSV: glove performing arbitrary closed-loop motions.
# These can be the same file if you used the same marker scheme for both,
# or separate files if you prefer to keep them distinct.
STATIONARY_CSV  = "gyro_calibration/data/raw/gyro_stationary.csv"
TRAJECTORY_CSV  = "gyro_calibration/data/raw/gyro_log.csv"

# ── Hyperparameters ───────────────────────────────────────────────────────────
# Wrist:
'''
LAMBDA_A = 1e-4 # 8e-5   # penalty on A deviating from identity
LAMBDA_B = 1e-5 # 1e-5 # 1e-5   # penalty on B (higher-order, more conservative)
N_FOLDS  = 8      # K-fold splits for trajectory CV
'''

# Fingers:
LAMBDA_A = 1e-4 # 1e-4 # 8e-5   # penalty on A deviating from identity
LAMBDA_B = 1e-5 # 1e-5 # 1e-5   # penalty on B (higher-order, more conservative)
N_FOLDS  = 8      # K-fold splits for trajectory CV


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
    print(f"  Extracted episodes: {len(episodes)}")
    return episodes

'''
def mean_drift_norm(episodes, A, b, B=None):
    return np.mean([
        np.linalg.norm(integrate_episode(ep, A, b, B=B))
        for ep in episodes
    ])
'''

def run_kfold(trajectory_episodes, b_fixed, model='linear', pool=None):
    """
    K-fold cross-validation over trajectory episodes.
    b is always fixed from phase 1 — never refitted per fold.
    """
    episodes = list(trajectory_episodes)
    kf = KFold(n_splits=N_FOLDS, shuffle=True, random_state=42)
    indices = np.arange(len(episodes))

    fold_raw  = []
    fold_corr = []

    print(f"\n{'='*55}")
    print(f"K-FOLD ({N_FOLDS} folds) — {model.upper()} MODEL")
    print(f"{'='*55}")

    for fold, (train_idx, test_idx) in enumerate(kf.split(indices)):
        train_eps = [episodes[i] for i in train_idx]
        test_eps  = [episodes[i] for i in test_idx]

        print(f"\n--- Fold {fold + 1}/{N_FOLDS}  "
              f"(train: {len(train_eps)}, test: {len(test_eps)}) ---")

        if model == 'linear':
            A, b = train_linear(train_eps, b_fixed, LAMBDA_A, pool=pool)
            B = None
        else:
            A, b, B = train_quadratic(train_eps, b_fixed, LAMBDA_A, LAMBDA_B, pool=pool)

        raw_norm = mean_drift_norm(test_eps, A_RAW, b_RAW, pool=pool)
        corr_norm = mean_drift_norm(test_eps, A, b, B=B, pool=pool)
        reduction = 1.0 - corr_norm / raw_norm if raw_norm > 0 else 0.0

        print(f"  Fold {fold + 1}: raw={raw_norm:.6f} rad  "
              f"corrected={corr_norm:.6f} rad  "
              f"reduction={reduction:.2%}")

        fold_raw.append(raw_norm)
        fold_corr.append(corr_norm)

    fold_raw  = np.array(fold_raw)
    fold_corr = np.array(fold_corr)
    reductions = 1.0 - fold_corr / fold_raw

    print(f"\n  Mean raw:        {fold_raw.mean():.6f} rad")
    print(f"  Mean corrected:  {fold_corr.mean():.6f} rad")
    print(f"  Mean reduction:  {reductions.mean():.2%}  "
          f"(std: {reductions.std():.2%}, min: {reductions.min():.2%})")

    return {'fold_raw': fold_raw, 'fold_corr': fold_corr, 'reductions': reductions}


def main(pool):
    # ── Phase 1: fit b from stationary data ──────────────────────────────────
    print("Loading stationary data...")
    df_stat = load_and_clean_csv(STATIONARY_CSV)
    stationary_episodes = extract_episodes(df_stat)

    if len(stationary_episodes) < 1:
        print("ERROR: No stationary episodes found. "
              "Record the glove sitting still with start/end markers.")
        return

    b_fixed = fit_bias(stationary_episodes, pool=pool)

    # ── Phase 2: fit A (and B) from trajectory data ───────────────────────────
    print("\nLoading trajectory data...")
    df_traj = load_and_clean_csv(TRAJECTORY_CSV)
    trajectory_episodes = extract_episodes(df_traj)

    if len(trajectory_episodes) < N_FOLDS:
        print(f"ERROR: Need at least {N_FOLDS} trajectory episodes.")
        return

    # K-fold CV to measure generalisation
    lin_results  = run_kfold(trajectory_episodes, b_fixed, model='linear',    pool=pool)
    quad_results = run_kfold(trajectory_episodes, b_fixed, model='quadratic', pool=pool)

    lin_mean  = lin_results['reductions'].mean()
    quad_mean = quad_results['reductions'].mean()

    print(f"\n{'='*55}")
    print("FINAL COMPARISON")
    print(f"{'='*55}")
    print(f"  Linear    mean reduction: {lin_mean:.2%}  "
          f"(std: {lin_results['reductions'].std():.2%})")
    print(f"  Quadratic mean reduction: {quad_mean:.2%}  "
          f"(std: {quad_results['reductions'].std():.2%})")

    use_quadratic = False # quad_mean > lin_mean * 1.02

    if use_quadratic:
        print("\n  → Quadratic gives >2% improvement. Use quadratic model.")
    else:
        print("\n  → Linear model is sufficient.")

    # ── Train final model on ALL trajectory episodes ──────────────────────────
    print(f"\n{'='*55}")
    print("FINAL MODEL — trained on all trajectory episodes")
    print("(Copy these parameters into updateOrientation)")
    print(f"{'='*55}")

    if use_quadratic:
        A_final, b_final, B_final = train_quadratic(
            trajectory_episodes, b_fixed, LAMBDA_A, LAMBDA_B, pool=pool
        )
        print("\nDeploy quadratic model in updateOrientation:")
        print("  gyro_corrected = A @ gyro_raw + B @ (gyro_raw ** 2) + b")
    else:
        A_final, b_final = train_linear(
            trajectory_episodes, b_fixed, LAMBDA_A, pool=pool
        )
        B_final = None
        print("\nDeploy linear model in updateOrientation:")
        print("  gyro_corrected = A @ gyro_raw + b")

    print(f"\n  A =\n{A_final}")
    print(f"  b = {b_final}")
    if B_final is not None:
        print(f"  B =\n{B_final}")

    # ── Detailed per-episode evaluate ─────────────────────────────────────────
    print(f"\n{'='*55}")
    print("DETAILED EVALUATE — first 5 trajectory episodes (final model)")
    print(f"{'='*55}")
    evaluate(trajectory_episodes, A_final, b_final, B=B_final)


if __name__ == "__main__":
    with Pool(processes=os.cpu_count()) as pool:
        main(pool)