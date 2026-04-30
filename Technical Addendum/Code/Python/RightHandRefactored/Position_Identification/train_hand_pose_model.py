"""
train_hand_pose_model.py

Trains a Random Forest classifier ("most trees") on PositionData_Snapshots.csv
to classify the 5 hand poses: thumbs_up, thumbs_down, peace, point, no_position.

Run this script in the same folder as your PositionData_Snapshots.csv file.
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import os

print("=== Hand Pose Random Forest Trainer ===\n")

# ================== CONFIG ==================
CSV_FILE = 'PositionData_Snapshots.csv'
MODEL_FILE = 'hand_pose_random_forest_model.pkl'
N_TREES = 1000          # "most trees" — you can increase this further
RANDOM_STATE = 42
# ===========================================

if not os.path.exists(CSV_FILE):
    print(f"❌ Error: {CSV_FILE} not found!")
    print("Please run the glove program, press the snapshot buttons several times, then try again.")
    exit()

# 1. Load data
df = pd.read_csv(CSV_FILE)
print(f"Loaded {len(df)} snapshots with {df.shape[1]} columns.")

# 2. Prepare features and labels
# Drop timestamps (not useful for classification)
df = df.drop(['Timestamp_RealTime', 'Timestamp_RunTime'], axis=1, errors='ignore')

X = df.drop('Label', axis=1)      # all quaternion + joint angle columns
y = df['Label']

print(f"Features: {X.shape[1]} columns")
print(f"Classes: {sorted(y.unique())}")
print(f"Samples per class:\n{y.value_counts()}\n")

# 3. Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
)

# 4. Train Random Forest with many trees
print(f"🌲 Training Random Forest with {N_TREES} trees...")
rf = RandomForestClassifier(
    n_estimators=N_TREES,
    max_depth=None,
    min_samples_split=2,
    min_samples_leaf=1,
    n_jobs=-1,                  # use all CPU cores
    random_state=RANDOM_STATE,
    oob_score=True
)

rf.fit(X_train, y_train)

# 5. Evaluate
y_pred = rf.predict(X_test)

print("\n" + "="*60)
print("MODEL PERFORMANCE")
print("="*60)
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f} ({accuracy_score(y_test, y_pred)*100:.1f}%)")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# Feature importance (useful for debugging)
importances = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)
print("\nTop 10 most important features:")
print(importances.head(10))

# 6. Save the model
joblib.dump(rf, MODEL_FILE)
print(f"\n✅ Model successfully saved as '{MODEL_FILE}'")
print("You can now load this model in your main program for real-time classification!")