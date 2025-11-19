#!/bin/bash

# Raspberry Pi 5 Specific Setup Script
# This script configures audio and system settings for Pi 5

set -e

echo "========================================="
echo "Raspberry Pi 5 Audio Setup"
echo "========================================="
echo ""

# Check if running on Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "Warning: This script is designed for Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    MODEL=$(cat /proc/device-tree/model)
    echo "Detected: $MODEL"
fi

# Enable audio (if not already)
echo ""
echo "[1] Configuring audio..."
if [ -f /boot/config.txt ]; then
    # Check if dtparam=audio is enabled
    if ! grep -q "^dtparam=audio=on" /boot/config.txt; then
        echo "Enabling audio in /boot/config.txt..."
        echo "dtparam=audio=on" | sudo tee -a /boot/config.txt
        echo "✓ Audio enabled (reboot required)"
    else
        echo "✓ Audio already enabled"
    fi
else
    echo "⚠ /boot/config.txt not found (may be using newer config system)"
fi

# Add user to audio group
echo ""
echo "[2] Adding user to audio group..."
if ! groups | grep -q audio; then
    sudo usermod -aG audio $USER
    echo "✓ Added to audio group (logout/login required)"
else
    echo "✓ Already in audio group"
fi

# Configure ALSA for Pi 5
echo ""
echo "[3] Configuring ALSA..."
ALSA_CONFIG="$HOME/.asoundrc"

# Create ALSA config if it doesn't exist
if [ ! -f "$ALSA_CONFIG" ]; then
    cat > "$ALSA_CONFIG" << 'EOF'
# Raspberry Pi 5 Audio Configuration
# Default to card 0 (built-in audio)

# For HDMI audio (if needed):
# pcm.!default {
#     type hw
#     card 0
#     device 3
# }

# For analog audio (3.5mm jack):
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
    echo "✓ Created $ALSA_CONFIG"
    echo "  Edit this file if you need to change audio devices"
else
    echo "✓ ALSA config already exists"
fi

# Set audio volume
echo ""
echo "[4] Setting audio volume..."
if command -v amixer &> /dev/null; then
    # Unmute and set volume to 70%
    amixer set Master unmute 2>/dev/null || true
    amixer set Master 70% 2>/dev/null || true
    amixer set PCM unmute 2>/dev/null || true
    amixer set PCM 70% 2>/dev/null || true
    echo "✓ Audio volume configured"
    echo "  Use 'alsamixer' to adjust manually"
else
    echo "⚠ amixer not available"
fi

# Install PulseAudio (optional, for better compatibility)
echo ""
read -p "Install PulseAudio for better audio compatibility? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing PulseAudio..."
    sudo apt install -y pulseaudio pulseaudio-utils
    echo "✓ PulseAudio installed"
    echo "  You can use 'device = pulse' in darkice.conf"
fi

# Network optimization for streaming
echo ""
echo "[5] Optimizing network settings..."
if [ -f /etc/sysctl.conf ]; then
    # Check if TCP optimizations are already added
    if ! grep -q "# Shoutcast streaming optimizations" /etc/sysctl.conf; then
        echo "Adding network optimizations..."
        sudo tee -a /etc/sysctl.conf > /dev/null << 'EOF'

# Shoutcast streaming optimizations
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
EOF
        echo "✓ Network optimizations added"
        echo "  Run 'sudo sysctl -p' to apply immediately"
    else
        echo "✓ Network optimizations already configured"
    fi
fi

# Create log directory
echo ""
echo "[6] Creating directories..."
mkdir -p logs
mkdir -p config
echo "✓ Directories created"

# Set script permissions
echo ""
echo "[7] Setting script permissions..."
chmod +x *.sh 2>/dev/null || true
echo "✓ Scripts made executable"

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Important:"
echo "- If audio was enabled, you may need to reboot"
echo "- If added to audio group, logout and login"
echo ""
echo "Next steps:"
echo "1. Run: ./test_audio.sh"
echo "2. Configure: cp darkice.conf.example darkice.conf"
echo "3. Edit darkice.conf with your server details"
echo "4. Test: ./start_encoder.sh"


