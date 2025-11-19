#!/bin/bash

# Shoutcast/Icecast Stream Player Script
# Usage: ./play_stream.sh [stream_url]

# Default stream URL (edit this or pass as argument)
DEFAULT_STREAM_URL="http://your-server.com:8000/stream"

# Get stream URL from argument or use default
STREAM_URL="${1:-$DEFAULT_STREAM_URL}"

# Check if URL is provided
if [ "$STREAM_URL" == "http://your-server.com:8000/stream" ] && [ -z "$1" ]; then
    echo "Error: No stream URL provided!"
    echo ""
    echo "Usage: $0 <stream_url>"
    echo "Example: $0 http://stream.example.com:8000/stream"
    echo ""
    echo "Or edit this script and set DEFAULT_STREAM_URL"
    exit 1
fi

echo "========================================="
echo "Shoutcast/Icecast Stream Player"
echo "========================================="
echo "Stream URL: $STREAM_URL"
echo ""

# Check if mpg123 is installed
if command -v mpg123 &> /dev/null; then
    PLAYER="mpg123"
    PLAYER_CMD="mpg123 -v -C $STREAM_URL"
elif command -v mplayer &> /dev/null; then
    PLAYER="mplayer"
    PLAYER_CMD="mplayer -quiet $STREAM_URL"
elif command -v vlc &> /dev/null; then
    PLAYER="vlc"
    PLAYER_CMD="vlc --intf dummy --play-and-exit $STREAM_URL"
else
    echo "Error: No suitable audio player found!"
    echo "Please install one of: mpg123, mplayer, or vlc"
    echo "Run: sudo apt install mpg123"
    exit 1
fi

echo "Using player: $PLAYER"
echo ""
echo "Press Ctrl+C to stop playback"
echo ""

# Test connection
echo "Testing connection to stream..."
if curl -s --head --max-time 5 "$STREAM_URL" | head -n 1 | grep -q "HTTP"; then
    echo "Connection successful!"
else
    echo "Warning: Could not verify stream connection"
    echo "Continuing anyway..."
fi

echo ""
echo "Starting playback..."
echo ""

# Play stream
$PLAYER_CMD

# If we get here, playback ended
echo ""
echo "Playback ended."


