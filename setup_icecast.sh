#!/bin/bash
# Setup Icecast Server for Shoutcast Web UI

set -e

echo "Setting up Icecast server..."

# Install Icecast
sudo apt install -y icecast2

# Create config directory if needed
sudo mkdir -p /etc/icecast2

# Copy custom configuration
if [ -f icecast.xml ]; then
    sudo cp icecast.xml /etc/icecast2/icecast.xml
    echo "✓ Icecast configuration installed"
else
    echo "⚠ icecast.xml not found, using default config"
fi

# Create log directory
sudo mkdir -p /var/log/icecast2
sudo chown icecast2:icecast2 /var/log/icecast2

# Create run directory
sudo mkdir -p /var/run/icecast2
sudo chown icecast2:icecast2 /var/run/icecast2

# Enable Icecast service (optional - we'll control it via web UI)
# sudo systemctl enable icecast2
# sudo systemctl start icecast2

echo "Icecast setup complete!"
echo ""
echo "Default password: hackme"
echo "Change it in /etc/icecast2/icecast.xml"
echo ""
echo "Start Icecast: sudo systemctl start icecast2"
echo "Or use the web UI to start/stop"


