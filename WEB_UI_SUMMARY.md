# Shoutcast Web UI - Complete Package

## 🎉 What's Included

A complete, modern web-based control panel for Shoutcast encoding and decoding on Raspberry Pi with a beautiful, responsive UI.

## 📦 Files Created

### Core Application
- **`app.py`** - Flask web application with REST API
- **`templates/index.html`** - Modern, responsive web UI
- **`requirements.txt`** - Python dependencies (Flask)

### Installation
- **`install_clean.sh`** - Complete installation script for fresh Raspberry Pi OS
- **`QUICK_SETUP.md`** - Step-by-step setup guide
- **`README_WEB_UI.md`** - Complete documentation

## ✨ Features

### Web Interface
- 🎨 Beautiful, modern gradient design
- 📱 Fully responsive (works on mobile/tablet)
- ⚡ Real-time status updates (auto-refresh every 2 seconds)
- 🎛️ Easy-to-use controls
- 📊 Live status indicators

### Encoder (Streaming)
- Configure Shoutcast/Icecast server
- Adjust bitrate, sample rate
- Select audio device
- Start/stop streaming
- Auto-save configuration

### Decoder (Playback)
- Play any Shoutcast stream URL
- Start/stop playback
- Real-time status

### Additional Features
- Audio device detection
- Configuration management
- Systemd service integration
- Auto-restart on failure

## 🚀 Quick Start

### 1. Transfer Files to Pi

```bash
# From your computer, transfer files:
scp -r app.py requirements.txt install_clean.sh templates pi@raspberrypi.local:~/Raspbery/
```

### 2. Run Installation

```bash
# SSH into Pi
ssh pi@raspberrypi.local

# Install
cd ~/Raspbery
chmod +x install_clean.sh
./install_clean.sh
```

### 3. Start Service

```bash
sudo systemctl start shoutcast-web
sudo systemctl enable shoutcast-web
```

### 4. Access Web UI

Open browser: `http://raspberrypi.local:5000`

## 📋 Installation Requirements

- Raspberry Pi OS (64-bit recommended)
- Internet connection
- SSH access
- sudo privileges

## 🎯 What Gets Installed

- Python 3 + pip
- Flask web framework
- Darkice (encoder)
- mpg123 (decoder)
- VLC (alternative decoder)
- ALSA audio libraries
- All dependencies

## 🔧 Configuration

All configuration is done through the web UI:
1. Open web interface
2. Enter server details
3. Configure audio settings
4. Click "Start Streaming"

No manual file editing required!

## 📱 Web UI Screenshots (Description)

The interface includes:
- **Header**: Title with gradient background
- **Status Cards**: Real-time encoder/decoder status with color indicators
- **Encoder Panel**: Full configuration form with start/stop buttons
- **Decoder Panel**: Stream URL input with playback controls
- **Messages**: Success/error notifications
- **Audio Devices**: Expandable device list

## 🛠️ Service Management

```bash
# Start
sudo systemctl start shoutcast-web

# Stop
sudo systemctl stop shoutcast-web

# Status
sudo systemctl status shoutcast-web

# Logs
sudo journalctl -u shoutcast-web -f

# Enable auto-start
sudo systemctl enable shoutcast-web
```

## 🌐 Accessing from Network

The web UI is accessible from any device on your network:
- Desktop: `http://raspberrypi.local:5000`
- Mobile: `http://<pi-ip>:5000`
- Tablet: `http://raspberrypi.local:5000`

## 🔒 Security Notes

- Change `SECRET_KEY` in `app.py` for production
- Consider using HTTPS (nginx reverse proxy)
- Keep system updated
- Use strong passwords for Shoutcast server

## 📊 API Endpoints

The web app provides a REST API:
- `GET /api/status` - Get status
- `GET /api/config` - Get configuration
- `POST /api/config` - Save configuration
- `POST /api/encoder/start` - Start encoder
- `POST /api/encoder/stop` - Stop encoder
- `POST /api/decoder/start` - Start decoder
- `POST /api/decoder/stop` - Stop decoder
- `GET /api/audio/devices` - List audio devices

## 🐛 Troubleshooting

### Web UI Not Loading
- Check service: `sudo systemctl status shoutcast-web`
- Check port: `sudo netstat -tlnp | grep 5000`
- Check firewall: `sudo ufw allow 5000`

### Encoder Issues
- Verify configuration in web UI
- Check audio device: `arecord -l`
- Test manually: `darkice -c ~/Raspbery/darkice.conf`

### Decoder Issues
- Verify stream URL is correct
- Test URL in browser/VLC
- Check audio output: `aplay -l`

## 📚 Documentation

- **QUICK_SETUP.md** - Fast setup guide
- **README_WEB_UI.md** - Complete documentation
- **This file** - Overview and summary

## 🎓 Next Steps

1. Install on fresh Raspberry Pi OS
2. Access web UI
3. Configure your Shoutcast server
4. Start streaming!

## 💡 Tips

- Bookmark the web UI URL for easy access
- Use the "Refresh Devices" button to find audio devices
- Check status indicators for quick status check
- Use systemd service for reliable auto-start

## 🎉 Enjoy!

You now have a modern, web-based control panel for Shoutcast streaming on your Raspberry Pi!


