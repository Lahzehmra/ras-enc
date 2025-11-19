# Shoutcast Web UI - Modern Control Panel

A beautiful, modern web interface for controlling Shoutcast encoding and decoding on Raspberry Pi.

## Features

- 🎨 **Modern Web UI** - Beautiful, responsive design
- 📡 **Encoder Control** - Start/stop streaming to Shoutcast servers
- 🔊 **Decoder Control** - Play Shoutcast streams
- ⚙️ **Configuration Management** - Easy web-based configuration
- 📊 **Real-time Status** - Live status updates
- 🎵 **Audio Device Detection** - Automatic audio device listing

## Installation

### Clean Raspberry Pi OS Installation

1. **Flash Raspberry Pi OS** (64-bit recommended for Pi 5)
   - Download from: https://www.raspberrypi.com/software/
   - Use Raspberry Pi Imager

2. **First Boot Setup**
   ```bash
   # Enable SSH (if not already enabled)
   sudo systemctl enable ssh
   sudo systemctl start ssh
   ```

3. **Run Installation Script**
   ```bash
   # Transfer install_clean.sh to your Pi, then:
   chmod +x install_clean.sh
   ./install_clean.sh
   ```

   Or run directly via SSH:
   ```bash
   # From your computer:
   scp install_clean.sh app.py requirements.txt templates/index.html user@pi:~/Raspbery/
   ssh user@pi
   cd ~/Raspbery
   chmod +x install_clean.sh
   ./install_clean.sh
   ```

## Usage

### Start Web Interface

**Option 1: Manual Start**
```bash
cd ~/Raspbery
source venv/bin/activate
python app.py
```

**Option 2: Systemd Service (Recommended)**
```bash
sudo systemctl start shoutcast-web
sudo systemctl enable shoutcast-web  # Auto-start on boot
```

### Access Web UI

Open your web browser and navigate to:
- `http://raspberrypi.local:5000`
- or `http://<pi-ip-address>:5000`

### Using the Web Interface

1. **Configure Encoder:**
   - Enter your Shoutcast server details
   - Set bitrate, sample rate, and audio device
   - Click "Start Streaming"

2. **Play Streams:**
   - Enter a Shoutcast stream URL
   - Click "Start Playback"

3. **Monitor Status:**
   - Real-time status indicators at the top
   - Green = Running, Red = Stopped

## Configuration

### Encoder Settings

- **Server Address**: Your Shoutcast/Icecast server hostname or IP
- **Port**: Server port (usually 8000)
- **Password**: Server password
- **Mount Point**: Stream path (e.g., `/stream`)
- **Bitrate**: Audio quality (64-320 kbps)
- **Sample Rate**: Audio sample rate (22050, 44100, or 48000 Hz)
- **Audio Device**: ALSA device (use "Refresh Devices" to find)

### Finding Audio Devices

Click "Refresh Devices" button to see available audio input/output devices.

Common device formats:
- `hw:0,0` - Hardware device, card 0, device 0
- `plughw:1,0` - Plugin device, card 1, device 0
- `default` - Default ALSA device

## Service Management

```bash
# Start service
sudo systemctl start shoutcast-web

# Stop service
sudo systemctl stop shoutcast-web

# Check status
sudo systemctl status shoutcast-web

# View logs
sudo journalctl -u shoutcast-web -f

# Enable auto-start on boot
sudo systemctl enable shoutcast-web
```

## Troubleshooting

### Web UI Not Accessible

1. Check if service is running:
   ```bash
   sudo systemctl status shoutcast-web
   ```

2. Check firewall:
   ```bash
   sudo ufw allow 5000
   ```

3. Check if port is in use:
   ```bash
   sudo netstat -tlnp | grep 5000
   ```

### Encoder Won't Start

1. Check configuration:
   - Verify server address, port, and password
   - Check audio device is correct

2. Check audio devices:
   ```bash
   arecord -l
   ```

3. Test darkice manually:
   ```bash
   cd ~/Raspbery
   darkice -c darkice.conf
   ```

4. Check logs:
   ```bash
   sudo journalctl -u shoutcast-web -n 50
   ```

### Decoder Won't Play

1. Verify stream URL is correct
2. Test stream URL in browser or VLC
3. Check audio output:
   ```bash
   aplay -l
   alsamixer  # Adjust volume
   ```

### Audio Issues

1. Check audio group membership:
   ```bash
   groups  # Should include 'audio'
   ```

2. If not in audio group:
   ```bash
   sudo usermod -aG audio $USER
   # Then logout and login
   ```

3. Test audio:
   ```bash
   speaker-test -t wav -c 2
   ```

## File Structure

```
~/Raspbery/
├── app.py                 # Flask web application
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Web UI template
├── darkice.conf          # Darkice configuration (auto-generated)
└── venv/                 # Python virtual environment
```

## API Endpoints

- `GET /` - Web interface
- `GET /api/status` - Get encoder/decoder status
- `GET /api/config` - Get configuration
- `POST /api/config` - Save configuration
- `POST /api/encoder/start` - Start encoder
- `POST /api/encoder/stop` - Stop encoder
- `POST /api/decoder/start` - Start decoder
- `POST /api/decoder/stop` - Stop decoder
- `GET /api/audio/devices` - Get audio device list

## Development

### Running in Development Mode

```bash
cd ~/Raspbery
source venv/bin/activate
export FLASK_ENV=development
python app.py
```

### Updating

```bash
cd ~/Raspbery
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart shoutcast-web
```

## Security Notes

- Change the `SECRET_KEY` in `app.py` for production
- Use HTTPS in production (consider using nginx as reverse proxy)
- Change default password for Shoutcast server
- Keep system updated: `sudo apt update && sudo apt upgrade`

## License

This project is provided as-is for educational and personal use.

## Support

For issues:
1. Check service logs: `sudo journalctl -u shoutcast-web -f`
2. Verify configuration in web UI
3. Test audio devices independently
4. Check network connectivity


