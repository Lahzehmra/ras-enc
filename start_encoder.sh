#!/bin/bash

# Start Darkice Encoder Script
# This script starts the Darkice encoder with the configuration file

CONFIG_FILE="darkice.conf"
LOG_DIR="logs"
LOG_FILE="$LOG_DIR/darkice_$(date +%Y%m%d_%H%M%S).log"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file '$CONFIG_FILE' not found!"
    echo "Please copy darkice.conf.example to darkice.conf and edit it."
    exit 1
fi

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Check if darkice is already running
if pgrep -x "darkice" > /dev/null; then
    echo "Darkice is already running!"
    echo "PID: $(pgrep -x darkice)"
    echo "To stop it, run: ./stop_encoder.sh"
    exit 1
fi

# Check if darkice is installed
if ! command -v darkice &> /dev/null; then
    echo "Error: Darkice is not installed!"
    echo "Please run: ./install.sh"
    exit 1
fi

# Test audio device
echo "Testing audio input device..."
if ! arecord -l &> /dev/null; then
    echo "Warning: No audio input devices found!"
    echo "Run 'arecord -l' to check available devices"
fi

echo "Starting Darkice encoder..."
echo "Config file: $CONFIG_FILE"
echo "Log file: $LOG_FILE"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start darkice in foreground (for testing)
# For background, use: darkice -c "$CONFIG_FILE" > "$LOG_FILE" 2>&1 &
darkice -c "$CONFIG_FILE" 2>&1 | tee "$LOG_FILE"


