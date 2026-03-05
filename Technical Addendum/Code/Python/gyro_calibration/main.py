# main.py

import pandas as pd

from calibration.train import train
from calibration.evaluate import evaluate

def load_data(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    df['marker'] = df['marker'].astype(str).str.strip()
    return df


def extract_episodes(df):
    df['marker'] = df['marker'].astype(str).str.strip().str.lower()

    episodes = []
    current_start = None

    for idx, row in df.iterrows():

        if row['marker'] == 'start':
            current_start = idx

        elif row['marker'] == 'end' and current_start is not None:
            ep = df.loc[current_start:idx].copy()

            if len(ep) > 2:
                episodes.append(ep)

            current_start = None  # reset

    print("Extracted episodes:", len(episodes))
    return episodes


df = load_data("gyro_calibration/data/raw/gyro_log.csv")
episodes = extract_episodes(df)

A_opt, b_opt = train(episodes)
evaluate(episodes, A_opt, b_opt)