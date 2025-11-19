#!/bin/bash

# Stop Darkice Encoder Script

echo "Stopping Darkice encoder..."

# Check if darkice is running
if ! pgrep -x "darkice" > /dev/null; then
    echo "Darkice is not running."
    exit 0
fi

# Get PID
PID=$(pgrep -x darkice)
echo "Found Darkice process: $PID"

# Stop darkice
kill "$PID"

# Wait a moment
sleep 2

# Check if still running
if pgrep -x "darkice" > /dev/null; then
    echo "Process still running, forcing kill..."
    kill -9 "$PID"
    sleep 1
fi

# Verify stopped
if ! pgrep -x "darkice" > /dev/null; then
    echo "Darkice stopped successfully."
else
    echo "Warning: Could not stop Darkice completely."
    exit 1
fi


