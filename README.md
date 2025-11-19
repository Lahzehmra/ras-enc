# Momento Audio Streaming System

A modern web-based audio streaming system for Raspberry Pi (Momento) with built-in encoder, decoder, and Icecast server.

## Features

### 🎙️ Audio Encoder
- Real-time audio encoding using Darkice
- Configurable bitrate, sample rate, and format
- Support for multiple audio input devices
- Real-time audio level monitoring (VU meter)
- Buffer size configuration for smooth encoding

### 📻 Built-in Icecast Server
- Integrated Icecast2 streaming server
- No external server required
- Web-based start/stop control
- Default configuration ready to use
- Admin interface accessible via web

### 🔊 Audio Decoder/Player
- **VLC-based player** - Handles all audio formats (MP3, AAC, OGG, FLAC, WAV, M3U, etc.)
- **RAM-based buffering** - All buffers stored in RAM for fast access and smooth playback
- Configurable network buffer (5-120 seconds, default: 30s)
- Pre-buffer cache (0-30 seconds, default: 10s)
- Auto-reconnect on network issues
- High-quality audio resampling
- Support for HTTP, HTTPS, and other network protocols

### ⚙️ Settings & Configuration
- Network configuration (IP, netmask, gateway, DHCP/static)
- USB audio device detection and selection
- Password management (unified for UI and Icecast)
- Buffer size configuration
- Playback device persistence

### 🔐 Security
- User authentication system
- Password-protected configuration changes
- Session management
- Secure password hashing

## Requirements

- Raspberry Pi (tested on Raspberry Pi OS)
- Python 3.7+
- Flask
- Darkice (for encoding)
- VLC (cvlc) - **Required for playback**
- Icecast2 (for streaming server)
- ALSA audio system

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Lahzehmra/ras-enc.git
cd ras-enc
```

2. Install dependencies:
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv darkice vlc icecast2 alsa-utils
```

3. Set up Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install flask
```

4. Configure Icecast (optional - defaults are provided):
```bash
sudo cp icecast.xml /etc/icecast2/icecast.xml
sudo chown icecast2:icecast /etc/icecast2/icecast.xml
```

5. Run the application:
```bash
source venv/bin/activate
python app.py
```

6. Access the web interface:
   - Open browser: `http://<raspberry-pi-ip>:5000`
   - Default credentials: `admin` / `hackme` (change immediately!)

## Architecture

### Player System
- **VLC (cvlc) is the ONLY player** - Simplified architecture
- Handles all audio formats and network protocols
- RAM-based buffering for optimal performance
- No fallback players needed - VLC handles everything

### Buffer System
All buffers are stored in **RAM** (not disk) for fast access:
- **Network Buffer**: 30 seconds default (5-120s range)
- **File Cache**: 2x network buffer (60s for 30s network buffer)
- **Live Cache**: 10 seconds default (0-30s range) - pre-buffers before playback starts

### Audio Flow
```
Encoder: Microphone/Line Input → Darkice → Icecast Server
Decoder: Network Stream → VLC (RAM buffers) → ALSA Output
```

## Configuration

### Default Settings
- **Encoder Buffer**: 10 seconds
- **Decoder Network Buffer**: 30 seconds
- **Decoder Playback Cache**: 10 seconds
- **Icecast Port**: 8000
- **Web UI Port**: 5000

### Buffer Recommendations
- **For stable networks**: 15-30 seconds network buffer
- **For unstable networks**: 30-60 seconds network buffer
- **For best quality**: 10+ seconds playback cache
- **For low latency**: 5-10 seconds total buffer

## Usage

### Starting the Encoder
1. Select input audio device
2. Configure server settings (if using external server)
3. Set bitrate and sample rate
4. Click "Start Streaming"

### Starting the Decoder
1. Enter stream URL (MP3, AAC, M3U, etc.)
2. Select output audio device
3. Configure buffer sizes (optional)
4. Click "Start Playback"

### Using Built-in Icecast Server
1. Click "Start Server" in the Server tab
2. Configure encoder to use: `localhost:8000`
3. Stream URL will be: `http://<pi-ip>:8000/stream`

## File Structure

```
ras-enc/
├── app.py                 # Main Flask application
├── templates/
│   ├── index.html        # Main web UI
│   └── settings.html     # Settings page
├── icecast.xml           # Icecast configuration
├── darkice.conf          # Darkice configuration template
├── install_clean.sh      # Installation script
└── README.md             # This file
```

## API Endpoints

### Authentication
- `POST /api/login` - User login
- `GET /api/logout` - User logout
- `GET /api/auth/status` - Check authentication status

### Encoder
- `POST /api/encoder/start` - Start encoder
- `POST /api/encoder/stop` - Stop encoder
- `GET /api/encoder/status` - Get encoder status
- `GET /api/encoder/levels` - Get audio levels

### Decoder
- `POST /api/decoder/start` - Start decoder
- `POST /api/decoder/stop` - Stop decoder
- `GET /api/decoder/status` - Get decoder status
- `POST /api/decoder/config` - Save decoder configuration

### Server
- `POST /api/icecast/start` - Start Icecast server
- `POST /api/icecast/stop` - Stop Icecast server
- `GET /api/icecast/status` - Get server status

### Settings
- `GET /api/settings` - Get all settings
- `POST /api/settings` - Update settings
- `POST /api/settings/password` - Change password

## Troubleshooting

### No Audio Output
- Check audio device selection
- Verify ALSA volume controls are unmuted
- Check buffer sizes (increase for unstable networks)
- Ensure VLC (cvlc) is installed: `sudo apt-get install vlc`

### Poor Playback Quality
- Increase network buffer (30-60 seconds)
- Increase playback cache (10-20 seconds)
- Check network connection stability
- Verify stream URL is accessible

### Encoder Not Starting
- Check input device selection
- Verify Darkice is installed
- Check audio permissions
- Review system logs

## Performance Notes

- **RAM Usage**: Buffers are stored in RAM. For 30s buffer at 44.1kHz stereo:
  - Network buffer: ~5MB RAM
  - File cache: ~10MB RAM
  - Total: ~15MB RAM per stream

- **CPU Usage**: VLC is efficient, typically <5% CPU on Raspberry Pi 4

- **Network**: Buffers help handle network jitter and packet loss

## Security Notes

- **Change default password immediately** after first login
- Use strong passwords for production
- Consider HTTPS for production deployments
- Restrict network access if needed

## License

This project is provided as-is for educational and personal use.

## Contributing

Contributions are welcome! Please ensure code follows the existing style and includes appropriate error handling.

## Support

For issues and questions, please open an issue on the GitHub repository.

---

**Note**: This system uses VLC as the exclusive player for all audio formats. All buffers are stored in RAM for optimal performance. The simplified architecture makes the codebase easier to maintain and more reliable.
