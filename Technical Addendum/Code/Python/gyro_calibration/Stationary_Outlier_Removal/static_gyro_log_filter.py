import pandas as pd

# Load the original log.csv (must be in the same directory as this script)
file_name = 'gyro_log_thumb_s.csv'
df = pd.read_csv(file_name)

# Clean up the marker column (empty cells become '')
df['marker'] = df['marker'].fillna('').astype(str).str.strip()

print(f"Original number of rows: {len(df)}")

# Work on a copy so we can update step-by-step
current_df = df.copy()

# Process each axis in the exact order requested: wx → wy → wz
for col in ['wx', 'wy', 'wz']:
    n_rows = len(current_df)

    # Safety: if we can't remove 60 rows, stop this phase
    if n_rows <= 60:
        print(f"Skipping {col} filtering (only {n_rows} rows left).")
        break

    # Identify the exact rows to remove for this column (30 largest + 30 smallest)
    largest_labels = current_df.nlargest(30, col).index.tolist()
    smallest_labels = current_df.nsmallest(30, col).index.tolist()
    remove_set = set(largest_labels + smallest_labels)

    print(f"Removing {len(remove_set)} rows for {col} outliers "
          f"({len(largest_labels)} largest + {len(smallest_labels)} smallest).")

    # Build list of labels that will be kept (preserves original order)
    kept_labels = sorted(set(current_df.index) - remove_set)

    # Create the new DataFrame with only the kept rows
    new_data = current_df.loc[kept_labels].copy().reset_index(drop=True)

    # === Marker handling logic ===
    # For every removed row that had a marker, transfer it exactly as requested
    for k in sorted(remove_set):
        marker = current_df.loc[k, 'marker']
        if not marker:
            continue

        if marker == "start":
            # Move to the following kept row (next surviving row after this one)
            following = next((idx for idx in kept_labels if idx > k), None)
            if following is not None:
                new_pos = kept_labels.index(following)
            elif kept_labels:  # fallback: put on the new last row if it was the final row
                new_pos = len(kept_labels) - 1
            else:
                continue

            curr_m = new_data.at[new_pos, 'marker']
            new_data.at[new_pos, 'marker'] = marker if not curr_m else f"{curr_m},{marker}"

        elif marker == "end":
            # Move to the previous kept row (last surviving row before this one)
            prev = next((idx for idx in reversed(kept_labels) if idx < k), None)
            if prev is not None:
                new_pos = kept_labels.index(prev)
            elif kept_labels:  # fallback: put on the new first row if it was the first row
                new_pos = 0
            else:
                continue

            curr_m = new_data.at[new_pos, 'marker']
            new_data.at[new_pos, 'marker'] = marker if not curr_m else f"{curr_m},{marker}"

    # Replace the working DataFrame with the filtered version
    current_df = new_data
    print(f"Rows remaining after {col} filtering: {len(current_df)}")

# OVERWRITE the original file with the filtered data
current_df.to_csv(file_name, index=False)

print("\nFiltering complete!")
print("→ log.csv has been overwritten with the filtered version")
print("   (30 largest + 30 smallest wx removed, then same for wy, then wz)")