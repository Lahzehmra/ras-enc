#!/bin/bash

# Shoutcast Encoder/Decoder Installation Script for Raspberry Pi 5
# This script installs all required dependencies

set -e

echo "========================================="
echo "Shoutcast Encoder/Decoder Installation"
echo "Raspberry Pi 5 Setup"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo "Please do not run as root. Use sudo when needed."
   exit 1
fi

# Update package list
echo "[1/6] Updating package list..."
sudo apt update

# Install build dependencies
echo "[2/6] Installing build dependencies..."
sudo apt install -y build-essential git autoconf automake libtool

# Install audio libraries
echo "[3/6] Installing audio libraries..."
sudo apt install -y \
    alsa-utils \
    alsa-base \
    libasound2-dev \
    libasound2 \
    libasound2-plugins

# Install encoding libraries
echo "[4/6] Installing encoding libraries..."
sudo apt install -y \
    libmp3lame-dev \
    libvorbis-dev \
    libfaac-dev \
    libtwolame-dev

# Install Darkice (encoder)
echo "[5/6] Installing Darkice encoder..."
if ! command -v darkice &> /dev/null; then
    sudo apt install -y darkice
else
    echo "Darkice already installed"
fi

# Install decoders/players
echo "[6/6] Installing audio players..."
sudo apt install -y \
    mpg123 \
    vlc \
    mplayer \
    sox

# Install additional utilities
echo "Installing additional utilities..."
sudo apt install -y \
    curl \
    wget \
    netcat-openbsd

# Configure ALSA
echo ""
echo "Configuring ALSA..."
if [ ! -f ~/.asoundrc ]; then
    echo "Creating ~/.asoundrc..."
    cat > ~/.asoundrc << 'EOF'
# Default audio device configuration
# Modify card number based on your hardware
# Use 'aplay -l' to find your card number
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
    echo "Created ~/.asoundrc - please edit with your audio device number"
fi

# Set permissions
echo ""
echo "Setting permissions..."
chmod +x play_stream.sh
chmod +x start_encoder.sh
chmod +x stop_encoder.sh

# Create directories
echo ""
echo "Creating directories..."
mkdir -p logs
mkdir -p config

echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Configure audio devices:"
echo "   arecord -l  # List input devices"
echo "   aplay -l    # List output devices"
echo ""
echo "2. Edit darkice.conf.example with your server details"
echo "   cp darkice.conf.example darkice.conf"
echo "   nano darkice.conf"
echo ""
echo "3. Test audio input:"
echo "   arecord -d 5 -f cd test.wav"
echo "   aplay test.wav"
echo ""
echo "4. Start encoding:"
echo "   ./start_encoder.sh"
echo ""
echo "5. Test decoder:"
echo "   ./play_stream.sh http://your-server.com:8000/stream"
echo ""


