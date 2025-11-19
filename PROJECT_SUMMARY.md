# Project Summary - Shoutcast Encoder/Decoder for Raspberry Pi 5

## Project Structure

```
Raspbery/
│
├── README.md                 # Main documentation
├── QUICKSTART.md            # 5-minute quick start guide
├── SETUP_GUIDE.md           # Detailed step-by-step setup
├── PROJECT_SUMMARY.md       # This file
│
├── install.sh               # Main installation script
├── setup_pi5.sh             # Raspberry Pi 5 specific setup
├── test_audio.sh            # Audio hardware testing
│
├── darkice.conf.example     # Encoder configuration template
├── start_encoder.sh          # Start encoder script
├── stop_encoder.sh           # Stop encoder script
│
├── play_stream.sh            # Decoder/player script
├── decoder_python.py        # Python alternative decoder
├── requirements.txt          # Python dependencies
│
├── darkice.service          # Systemd service for encoder
└── stream_player.service    # Systemd service for decoder
```

## Quick Reference

### Installation Order

1. **Initial Setup**
   ```bash
   ./setup_pi5.sh
   # Reboot if needed
   ```

2. **Install Dependencies**
   ```bash
   ./install.sh
   ```

3. **Test Hardware**
   ```bash
   ./test_audio.sh
   ```

4. **Configure Encoder**
   ```bash
   cp darkice.conf.example darkice.conf
   nano darkice.conf
   ```

5. **Test Encoder**
   ```bash
   ./start_encoder.sh
   ```

6. **Test Decoder**
   ```bash
   ./play_stream.sh http://your-server.com:8000/stream
   ```

7. **Install Services** (optional)
   ```bash
   sudo cp darkice.service /etc/systemd/system/
   sudo systemctl enable darkice.service
   sudo systemctl start darkice.service
   ```

## File Descriptions

### Documentation
- **README.md**: Complete guide with all features and troubleshooting
- **QUICKSTART.md**: Fast setup for experienced users
- **SETUP_GUIDE.md**: Detailed walkthrough for beginners
- **PROJECT_SUMMARY.md**: Overview and quick reference

### Installation Scripts
- **install.sh**: Installs all required packages and dependencies
- **setup_pi5.sh**: Configures Raspberry Pi 5 specific settings
- **test_audio.sh**: Tests and identifies audio hardware

### Encoder (Streaming)
- **darkice.conf.example**: Configuration template for Darkice
- **start_encoder.sh**: Starts the encoder with proper logging
- **stop_encoder.sh**: Stops the encoder gracefully
- **darkice.service**: Systemd service for auto-start on boot

### Decoder (Receiving)
- **play_stream.sh**: Shell script to play Shoutcast streams
- **decoder_python.py**: Python alternative (requires pyaudio)
- **requirements.txt**: Python package dependencies
- **stream_player.service**: Systemd service for continuous playback

## Key Features

### Encoder Features
- ✅ Stream to Shoutcast/Icecast servers
- ✅ Multiple audio format support (MP3, OGG)
- ✅ Configurable bitrate and sample rate
- ✅ Automatic reconnection
- ✅ Systemd service integration
- ✅ Logging and monitoring

### Decoder Features
- ✅ Play Shoutcast/Icecast streams
- ✅ Multiple player support (mpg123, VLC, mplayer)
- ✅ Python alternative implementation
- ✅ Systemd service for continuous playback
- ✅ Connection testing

## Typical Workflow

### First Time Setup
```
1. Run setup_pi5.sh → Reboot
2. Run install.sh
3. Run test_audio.sh → Note device numbers
4. Configure darkice.conf
5. Test with start_encoder.sh
6. Install service for auto-start
```

### Daily Usage
```
# Start streaming
sudo systemctl start darkice

# Stop streaming
sudo systemctl stop darkice

# Check status
sudo systemctl status darkice

# View logs
sudo journalctl -u darkice -f

# Play stream
./play_stream.sh http://server.com:8000/stream
```

## Configuration Examples

### Basic Voice Streaming (USB Mic)
```ini
device = plughw:1,0
sampleRate = 22050
channel = 1
bitrate = 64
```

### High Quality Music Streaming
```ini
device = hw:1,0
sampleRate = 44100
channel = 2
bitrate = 192
```

### Low CPU Usage
```ini
sampleRate = 22050
channel = 1
bitrate = 64
```

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| No audio input | Run `alsamixer`, check `arecord -l` |
| Can't connect | Check server URL, port, password |
| High CPU | Lower sampleRate and bitrate |
| Service won't start | Check logs: `sudo journalctl -u darkice` |
| No audio output | Check `aplay -l`, adjust volume |

## System Requirements

- **Hardware**: Raspberry Pi 5
- **OS**: Raspberry Pi OS (64-bit recommended)
- **Audio**: USB microphone/sound card or line input
- **Network**: Internet connection for streaming
- **Storage**: 2GB+ free space

## Performance Notes

- **CPU Usage**: ~5-15% for encoding at 128kbps
- **Memory**: ~50-100MB for Darkice
- **Network**: ~128kbps upload for 128kbps stream
- **Storage**: Minimal (logs only)

## Security Considerations

- Change default passwords in configuration
- Use firewall rules for server ports
- Keep system updated: `sudo apt update && sudo apt upgrade`
- Review service file permissions
- Use HTTPS streams when possible

## Support & Resources

- **Darkice Documentation**: http://www.darkice.org/
- **ALSA Documentation**: https://www.alsa-project.org/
- **Raspberry Pi Forums**: https://forums.raspberrypi.com/
- **Shoutcast/Icecast**: Check your server documentation

## License

This project is provided as-is for educational and personal use.

## Version History

- **v1.0**: Initial release
  - Encoder setup with Darkice
  - Decoder with multiple players
  - Systemd service integration
  - Complete documentation
  - Raspberry Pi 5 optimizations


