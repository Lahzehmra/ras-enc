#!/bin/bash
# Complete Shoutcast Encoder/Decoder Setup for Raspberry Pi 5
# Run this script directly on your Raspberry Pi via SSH

set -e

echo "========================================="
echo "Shoutcast Encoder/Decoder Setup"
echo "Raspberry Pi 5 - Complete Installation"
echo "========================================="
echo ""

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$HOME/Raspbery"

# Create project directory
echo "[1/10] Creating project directory..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"
echo "✓ Project directory: $PROJECT_DIR"

# Update system
echo ""
echo "[2/10] Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install build dependencies
echo ""
echo "[3/10] Installing build dependencies..."
sudo apt install -y build-essential git autoconf automake libtool

# Install audio libraries
echo ""
echo "[4/10] Installing audio libraries..."
sudo apt install -y \
    alsa-utils \
    alsa-base \
    libasound2-dev \
    libasound2 \
    libasound2-plugins

# Install encoding libraries
echo ""
echo "[5/10] Installing encoding libraries..."
sudo apt install -y \
    libmp3lame-dev \
    libvorbis-dev \
    libfaac-dev \
    libtwolame-dev

# Install Darkice
echo ""
echo "[6/10] Installing Darkice encoder..."
sudo apt install -y darkice

# Install decoders/players
echo ""
echo "[7/10] Installing audio players..."
sudo apt install -y \
    mpg123 \
    vlc \
    mplayer \
    sox \
    curl \
    wget

# Configure audio
echo ""
echo "[8/10] Configuring audio system..."

# Add user to audio group
if ! groups | grep -q audio; then
    sudo usermod -aG audio $USER
    echo "✓ Added user to audio group"
fi

# Create ALSA config
if [ ! -f ~/.asoundrc ]; then
    cat > ~/.asoundrc << 'EOF'
# Raspberry Pi 5 Audio Configuration
pcm.!default {
    type hw
    card 0
    device 0
}

ctl.!default {
    type hw
    card 0
}
EOF
    echo "✓ Created ALSA configuration"
fi

# Enable audio in config.txt if it exists
if [ -f /boot/config.txt ]; then
    if ! grep -q "^dtparam=audio=on" /boot/config.txt; then
        echo "dtparam=audio=on" | sudo tee -a /boot/config.txt
        echo "✓ Enabled audio in /boot/config.txt (reboot may be needed)"
    fi
fi

# Create Darkice configuration
echo ""
echo "[9/10] Creating configuration files..."

cat > "$PROJECT_DIR/darkice.conf" << 'EOF'
# Darkice Configuration for Shoutcast/Icecast Streaming
# Edit this file with your server details

[general]
duration = 0
bufferSecs = 5
reconnect = yes
reconnectDelay = 5
logLevel = 2

[input]
# Use 'arecord -l' to find your device number
# Format: hw:CARD,DEVICE or plughw:CARD,DEVICE
device = hw:1,0
sampleRate = 44100
bitsPerSample = 16
channel = 2

[icecast2-0]
bitrateMode = cbr
bitrate = 128
format = mp3
server = your-server.com
port = 8000
password = yourpassword
mountPoint = /stream
name = Raspberry Pi Stream
description = Audio stream from Raspberry Pi 5
genre = Various
url = http://your-server.com
public = yes
EOF

echo "✓ Created darkice.conf - EDIT THIS WITH YOUR SERVER DETAILS"

# Create helper scripts
echo ""
echo "[10/10] Creating helper scripts..."

# Start encoder script
cat > "$PROJECT_DIR/start_encoder.sh" << 'SCRIPT_EOF'
#!/bin/bash
CONFIG_FILE="darkice.conf"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: $CONFIG_FILE not found!"
    exit 1
fi
if pgrep -x "darkice" > /dev/null; then
    echo "Darkice is already running!"
    exit 1
fi
echo "Starting Darkice encoder..."
darkice -c "$CONFIG_FILE"
SCRIPT_EOF

# Stop encoder script
cat > "$PROJECT_DIR/stop_encoder.sh" << 'SCRIPT_EOF'
#!/bin/bash
if ! pgrep -x "darkice" > /dev/null; then
    echo "Darkice is not running."
    exit 0
fi
PID=$(pgrep -x darkice)
echo "Stopping Darkice (PID: $PID)..."
kill "$PID"
sleep 2
if pgrep -x "darkice" > /dev/null; then
    kill -9 "$PID"
fi
echo "Darkice stopped."
SCRIPT_EOF

# Play stream script
cat > "$PROJECT_DIR/play_stream.sh" << 'SCRIPT_EOF'
#!/bin/bash
STREAM_URL="${1:-http://your-server.com:8000/stream}"
if [ "$STREAM_URL" == "http://your-server.com:8000/stream" ] && [ -z "$1" ]; then
    echo "Usage: $0 <stream_url>"
    exit 1
fi
echo "Playing stream: $STREAM_URL"
if command -v mpg123 &> /dev/null; then
    mpg123 -v -C "$STREAM_URL"
elif command -v mplayer &> /dev/null; then
    mplayer -quiet "$STREAM_URL"
elif command -v vlc &> /dev/null; then
    vlc --intf dummy "$STREAM_URL"
else
    echo "No audio player found!"
    exit 1
fi
SCRIPT_EOF

# Test audio script
cat > "$PROJECT_DIR/test_audio.sh" << 'SCRIPT_EOF'
#!/bin/bash
echo "Audio Device Test"
echo "================="
echo ""
echo "Input devices:"
arecord -l
echo ""
echo "Output devices:"
aplay -l
echo ""
echo "Testing recording (3 seconds)..."
arecord -d 3 -f cd test.wav 2>/dev/null
if [ -f test.wav ]; then
    echo "✓ Recording successful"
    echo "Playing back..."
    aplay test.wav 2>/dev/null
    read -p "Delete test file? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm test.wav
    fi
fi
SCRIPT_EOF

# Make scripts executable
chmod +x "$PROJECT_DIR"/*.sh

# Create systemd service
echo ""
echo "Creating systemd service..."

sudo tee /etc/systemd/system/darkice.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=Darkice Streaming Audio Encoder
After=network.target sound.target

[Service]
Type=simple
User=mra
Group=audio
WorkingDirectory=/home/mra/Raspbery
ExecStart=/usr/bin/darkice -c /home/mra/Raspbery/darkice.conf
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE_EOF

sudo systemctl daemon-reload
echo "✓ Systemd service created"

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Test audio devices:"
echo "   cd $PROJECT_DIR"
echo "   ./test_audio.sh"
echo ""
echo "2. Edit configuration:"
echo "   nano $PROJECT_DIR/darkice.conf"
echo "   - Set device (from arecord -l)"
echo "   - Set server, port, password"
echo ""
echo "3. Test encoder:"
echo "   ./start_encoder.sh"
echo ""
echo "4. Test decoder:"
echo "   ./play_stream.sh http://your-server.com:8000/stream"
echo ""
echo "5. Enable service (optional):"
echo "   sudo systemctl enable darkice"
echo "   sudo systemctl start darkice"
echo ""
echo "Project directory: $PROJECT_DIR"
echo ""


