import os
import signal

PID_FILE = 'tasty-quote-streamer.pid'

if os.path.exists(PID_FILE):
    with open(PID_FILE, 'r') as f:
        pid = int(f.read().strip())
        os.kill(pid, signal.SIGINT)  # Send CTRL+C signal
else:
    print("PID file not found. Make sure the script is running.")

