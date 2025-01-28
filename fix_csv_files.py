#!/usr/bin/env python3

import os
import sys
import pandas as pd
import shutil
from datetime import datetime
import pytz
import argparse

def process_csv_file(file_path):
    """
    Process a single CSV file:
    - Standardize the 'timestamp' column to ISO format with UTC timezone.
    - For 'positions-quotes-*.csv' files, add 'open_price' column with 0.00 if missing.
    - Backup the original file with a '.old' extension.
    - Preserve the original file's access and modification times.
    """
    # Determine file type based on filename
    filename = os.path.basename(file_path)
    is_positions_quotes = filename.startswith("positions-quotes-")
    # Read original file's metadata
    try:
        stat_info = os.stat(file_path)
        original_atime = stat_info.st_atime
        original_mtime = stat_info.st_mtime
    except Exception as e:
        print(f"Error accessing file metadata for {file_path}: {e}")
        return

    # Read CSV with pandas
    try:
        df = pd.read_csv(file_path, dtype=str)  # Read all columns as strings to prevent unintended type coercion
    except Exception as e:
        print(f"Error reading CSV file {file_path}: {e}")
        return

    # Check if 'timestamp' column exists
    if 'timestamp' not in df.columns:
        print(f"'timestamp' column not found in {file_path}. Skipping file.")
        return

    # Function to standardize timestamp
    def standardize_timestamp(ts):
        try:
            if ts.endswith('Z'):  # Handle Zulu time
                dt = pd.to_datetime(ts, utc=True)
            else:
                dt = pd.to_datetime(ts, utc=True, errors='coerce')
                if pd.isnull(dt):
                    # If parsing failed, try adding UTC timezone
                    dt = pd.to_datetime(ts + '+00:00', utc=True, errors='coerce')
            if pd.isnull(dt):
                print(f"Could not parse timestamp: {ts}. Leaving as is.")
                return ts  # Return original if unable to parse
            return dt.isoformat()
        except Exception as e:
            print(f"Error parsing timestamp '{ts}': {e}")
            return ts  # Return original in case of error

    # Apply the standardization to the 'timestamp' column
    df['timestamp'] = df['timestamp'].apply(standardize_timestamp)

    # For positions-quotes-*.csv, handle 'open_price' column
    if is_positions_quotes:
        if 'open_price' not in df.columns:
            df.insert(4, 'open_price', '0.00')  # Insert after 'quantity' which is index 3
            print(f"Added 'open_price' column with 0.00 to {file_path}.")

    # Backup original file
    backup_file = file_path + ".old"
    try:
        if os.path.exists(backup_file):
            print(f"Backup file {backup_file} already exists. Overwriting.")
        shutil.copy2(file_path, backup_file)
        print(f"Backup created: {backup_file}")
    except Exception as e:
        print(f"Error creating backup for {file_path}: {e}")
        return

    # Write the updated DataFrame back to CSV
    try:
        df.to_csv(file_path, index=False)
        print(f"Updated file saved: {file_path}")
    except Exception as e:
        print(f"Error writing updated CSV to {file_path}: {e}")
        return

    # Restore original file's access and modification times
    try:
        os.utime(file_path, (original_atime, original_mtime))
    except Exception as e:
        print(f"Error restoring file times for {file_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Fix CSV files by standardizing timestamps and adding missing columns.")
    parser.add_argument(
        '-d', '--directory',
        type=str,
        default='data/',
        help='Directory containing the CSV files to process. Default is "data/".'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output.'
    )
    args = parser.parse_args()

    data_dir = args.directory

    if not os.path.isdir(data_dir):
        print(f"Directory '{data_dir}' does not exist.")
        sys.exit(1)

    # Find all relevant CSV files
    csv_files = []
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith('.csv') and (file.startswith('positions-quotes-') or file.startswith('strategy-mtm-')):
                csv_files.append(os.path.join(root, file))

    if not csv_files:
        print(f"No matching CSV files found in directory '{data_dir}'.")
        sys.exit(0)

    print(f"Found {len(csv_files)} CSV file(s) to process.")

    for csv_file in csv_files:
        if args.verbose:
            print(f"Processing file: {csv_file}")
        else:
            print(f"Processing: {csv_file}")
        process_csv_file(csv_file)

    print("Processing completed.")

if __name__ == "__main__":
    main()

