# tasty-quant/generate_crontab.py

import yaml
import pytz
from datetime import datetime, timedelta
import os
import sys

# Load the YAML configuration
def load_config(config_file: str):
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(f"Configuration file {config_file} not found.")
        exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing the configuration file: {e}")
        exit(1)

# Convert UTC times to local times using the current date
def convert_utc_to_local(utc_time_str: str, local_tz: str):
    local_timezone = pytz.timezone(local_tz)
    utc_timezone = pytz.utc
    now_utc = datetime.now(pytz.utc)

    # Parse the UTC time string and set it to today's date in UTC
    try:
        utc_time = datetime.strptime(utc_time_str, "%H:%M")
    except ValueError:
        print(f"Invalid UTC time format: {utc_time_str}. Expected HH:MM.")
        exit(1)

    utc_time = utc_time.replace(year=now_utc.year, month=now_utc.month, day=now_utc.day)
    utc_time = utc_timezone.localize(utc_time)

    # Convert to local time
    local_time = utc_time.astimezone(local_timezone)
    return local_time.strftime("%M %H"), local_time

# Check if DST is active for the current date in the local timezone
def is_dst(local_tz: str):
    local_timezone = pytz.timezone(local_tz)
    now_local = datetime.now(local_timezone)
    return bool(now_local.dst()), now_local

# Generate crontab entries based on the configuration
def generate_crontab(config):
    python_path = sys.executable  # Path to the current Python interpreter
    project_directory = os.path.dirname(os.path.abspath(__file__))  # Project directory

    # Extract configuration
    current_tz = config['market']['timezone']
    open_utc_time = config['market']['open_utc']
    close_utc_time = config['market']['close_utc']

    # Determine if DST is in effect
    dst_active, now_local = is_dst(current_tz)

    if dst_active:
        print("Daylight Saving Time is currently active.")
    else:
        print("Daylight Saving Time is not active.")

    # Convert market open and close times to local timezone
    open_local_time_str, open_local_time = convert_utc_to_local(open_utc_time, current_tz)
    close_local_time_str, close_local_time = convert_utc_to_local(close_utc_time, current_tz)

    # Adjust times: start at market open, stop at market close
    start_time_str = open_local_time.strftime("%M %H")
    stop_time_str = close_local_time.strftime("%M %H")

    # Print UTC and Local times
    print(f"Current UTC time: {now_local.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"Market Open Time: {open_local_time_str} Local ({'DST' if dst_active else 'Standard'})")
    print(f"Market Close Time: {close_local_time_str} Local ({'DST' if dst_active else 'Standard'})")
    print(f"UTC Market Open: {open_utc_time} UTC")
    print(f"UTC Market Close: {close_utc_time} UTC")
    print(f"Script Start Time (market open): {start_time_str} Local")
    print(f"Script Stop Time (market close): {stop_time_str} Local")

    # Define weekdays (Monday=1, Sunday=7)
    weekdays = '1-5'

    # Define the paths for scripts
    start_script = os.path.join(project_directory, 'start_script.sh')
    shutdown_script = os.path.join(project_directory, 'shutdown_script.py')
    test_log = os.path.join(project_directory, 'log', 'shutdown_script.log')

    # Generate crontab entries with correct field counts (five fields) and restricted to weekdays
    crontab_entries = [
        f"# Start the script at market open ({open_utc_time} UTC)\n"
        f"{start_time_str} * * {weekdays} cd {project_directory} && /bin/bash ./start_script.sh",

        f"# Stop the script at market close ({close_utc_time} UTC)\n"
        f"{stop_time_str} * * {weekdays} cd {project_directory} && {python_path} shutdown_script.py",

        f"\n# Test cronjobs",

        f"02 9 * * {weekdays} cd {project_directory} && {python_path} -c \"print('Cron job executed successfully START')\" >> {test_log} 2>&1",

        f"03 9 * * {weekdays} cd {project_directory} && {python_path} -c \"print('Cron job executed successfully STOP')\" >> {test_log} 2>&1"
    ]

    # Combine all entries into a single string separated by newlines
    return "\n".join(crontab_entries)

def main():
    config_file = 'tasty-quote-streamer.yaml'

    # Load the configuration
    config = load_config(config_file)

    # Generate crontab entries
    crontab = generate_crontab(config)
    print("\nGenerated Crontab Entries:")
    print(crontab)

    # Optionally, write it to a file
    with open('generated_crontab.txt', 'w') as f:
        f.write(crontab)

if __name__ == "__main__":
    main()
