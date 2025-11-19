#!/bin/bash
# Complete Clean Installation Script for Raspberry Pi OS
# Shoutcast Encoder/Decoder with Modern Web UI

set -e

echo "========================================="
echo "Shoutcast Web UI - Clean Installation"
echo "Raspberry Pi OS Setup"
echo "========================================="
echo ""

# Update system
echo "[1/8] Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install Python and pip
echo ""
echo "[2/8] Installing Python and dependencies..."
sudo apt install -y python3 python3-pip python3-venv

# Install audio libraries
echo ""
echo "[3/8] Installing audio libraries..."
sudo apt install -y \
    alsa-utils \
    libasound2-dev \
    libasound2 \
    libasound2-plugins

# Install encoding libraries
echo ""
echo "[4/8] Installing encoding libraries..."
sudo apt install -y \
    libmp3lame-dev \
    libvorbis-dev

# Install Darkice (encoder)
echo ""
echo "[5/8] Installing Darkice encoder..."
sudo apt install -y darkice

# Install decoders/players
echo ""
echo "[6/8] Installing audio players..."
sudo apt install -y \
    mpg123 \
    vlc

# Install additional tools
echo ""
echo "[7/8] Installing additional tools..."
sudo apt install -y \
    procps \
    curl \
    wget

# Create project directory
PROJECT_DIR="$HOME/Raspbery"
echo ""
echo "[8/8] Setting up project directory..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Create Python virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create systemd service
echo ""
echo "Creating systemd service..."
sudo tee /etc/systemd/system/shoutcast-web.service > /dev/null << EOF
[Unit]
Description=Shoutcast Web UI
After=network.target sound.target

[Service]
Type=simple
User=$USER
Group=audio
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload

# Add user to audio group
if ! groups | grep -q audio; then
    sudo usermod -aG audio $USER
    echo "✓ Added user to audio group (logout/login required)"
fi

# Create ALSA config if it doesn't exist
if [ ! -f ~/.asoundrc ]; then
    cat > ~/.asoundrc << 'ALSAEOF'
# Default audio device configuration
pcm.!default {
    type hw
    card 0
    device 0
}

ctl.!default {
    type hw
    card 0
}
ALSAEOF
    echo "✓ Created ALSA configuration"
fi

# Enable audio in config.txt if it exists
if [ -f /boot/config.txt ]; then
    if ! grep -q "^dtparam=audio=on" /boot/config.txt; then
        echo "dtparam=audio=on" | sudo tee -a /boot/config.txt
        echo "✓ Enabled audio in /boot/config.txt"
    fi
fi

echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "Project directory: $PROJECT_DIR"
echo ""
echo "To start the web interface:"
echo "  cd $PROJECT_DIR"
echo "  source venv/bin/activate"
echo "  python app.py"
echo ""
echo "Or use the systemd service:"
echo "  sudo systemctl start shoutcast-web"
echo "  sudo systemctl enable shoutcast-web"
echo ""
echo "Then access the web UI at:"
echo "  http://$(hostname -I | awk '{print $1}'):5000"
echo "  or"
echo "  http://raspberrypi.local:5000"
echo ""
echo "Note: You may need to logout/login for audio group changes to take effect."
echo ""

