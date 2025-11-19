# Complete Setup Guide - Raspberry Pi 5 Shoutcast System

## Overview

This guide walks you through setting up a complete Shoutcast/Icecast audio streaming system on Raspberry Pi 5, including both encoding (streaming) and decoding (receiving) capabilities.

## Part 1: Initial Setup

### Step 1: Prepare Raspberry Pi 5

1. **Install Raspberry Pi OS** (64-bit recommended)
   - Download from: https://www.raspberrypi.com/software/
   - Use Raspberry Pi Imager to flash to microSD card
   - Enable SSH and configure WiFi during imaging

2. **First Boot**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Reboot if kernel was updated
   sudo reboot
   ```

### Step 2: Clone/Download This Project

```bash
# If using git
git clone <repository-url>
cd Raspbery

# Or extract files to: /home/pi/Raspbery
```

### Step 3: Run Pi 5 Specific Setup

```bash
chmod +x setup_pi5.sh
./setup_pi5.sh
```

This will:
- Enable audio hardware
- Configure ALSA
- Add user to audio group
- Optimize network settings
- Set up directories

**Note:** You may need to reboot after this step.

## Part 2: Install Dependencies

### Step 4: Install All Software

```bash
chmod +x install.sh
./install.sh
```

This installs:
- Darkice (encoder)
- mpg123, VLC (decoders)
- ALSA tools
- Audio libraries

### Step 5: Test Audio Hardware

```bash
chmod +x test_audio.sh
./test_audio.sh
```

This will:
- List all audio devices
- Test recording
- Test playback
- Verify installations

**Important:** Note the card/device numbers shown (e.g., `card 1, device 0`)

## Part 3: Encoder Configuration

### Step 6: Configure Darkice

1. **Copy example configuration:**
   ```bash
   cp darkice.conf.example darkice.conf
   ```

2. **Edit configuration:**
   ```bash
   nano darkice.conf
   ```

3. **Essential settings to configure:**
   ```ini
   [input]
   device = hw:1,0          # Use numbers from test_audio.sh
   sampleRate = 44100       # 22050 for lower CPU, 48000 for better quality
   channel = 2              # 1 for mono, 2 for stereo
   
   [icecast2-0]
   server = your-server.com # Your Shoutcast/Icecast server
   port = 8000              # Server port
   password = yourpassword  # Server password
   mountPoint = /stream     # Stream path
   bitrate = 128            # 64-320 kbps
   ```

### Step 7: Test Encoder

```bash
# Start encoder manually
./start_encoder.sh
```

**Check:**
- No error messages
- Stream appears on server
- Can connect from another device

**Stop:** Press Ctrl+C

## Part 4: Decoder Configuration

### Step 8: Test Decoder

```bash
# Play a test stream
./play_stream.sh http://your-server.com:8000/stream

# Or use mpg123 directly
mpg123 http://your-server.com:8000/stream
```

### Step 9: Configure Auto-Playback (Optional)

Edit `stream_player.service`:
```bash
nano stream_player.service
```

Change the ExecStart line:
```ini
ExecStart=/usr/bin/mpg123 -v -C http://your-server.com:8000/stream
```

Install service:
```bash
sudo cp stream_player.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable stream_player.service
sudo systemctl start stream_player.service
```

## Part 5: Run as Services

### Step 10: Set Up Encoder Service

1. **Edit service file:**
   ```bash
   nano darkice.service
   ```
   
   Update paths if needed:
   ```ini
   WorkingDirectory=/home/pi/Raspbery
   ExecStart=/usr/bin/darkice -c /home/pi/Raspbery/darkice.conf
   ```

2. **Install service:**
   ```bash
   sudo cp darkice.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable darkice.service
   sudo systemctl start darkice.service
   ```

3. **Check status:**
   ```bash
   sudo systemctl status darkice.service
   sudo journalctl -u darkice -f
   ```

## Part 6: Verification

### Step 11: Verify Everything Works

**Encoder:**
```bash
# Check if running
sudo systemctl status darkice

# View logs
sudo journalctl -u darkice -n 50

# Test stream URL
curl -I http://your-server.com:8000/stream
```

**Decoder:**
```bash
# Test playback
./play_stream.sh http://your-server.com:8000/stream

# Check service (if installed)
sudo systemctl status stream_player
```

## Common Configurations

### USB Microphone Setup

1. Plug in USB microphone
2. Run `arecord -l` to find device
3. In `darkice.conf`:
   ```ini
   device = plughw:1,0
   channel = 1  # Mono for voice
   sampleRate = 22050  # Lower for voice
   ```

### Line Input Setup

1. Connect audio source to line-in
2. Find device: `arecord -l`
3. In `darkice.conf`:
   ```ini
   device = hw:1,0
   channel = 2  # Stereo
   sampleRate = 44100
   ```

### Low CPU Usage Setup

For older Pi or high load:
```ini
sampleRate = 22050
bitrate = 64
channel = 1  # Mono
```

### High Quality Setup

For best quality:
```ini
sampleRate = 48000
bitrate = 192
channel = 2  # Stereo
```

## Troubleshooting

### Encoder Won't Start

```bash
# Check configuration
darkice -c darkice.conf -v 3

# Check audio device
arecord -l
arecord -d 2 test.wav

# Check permissions
ls -l darkice.conf
groups  # Should include 'audio'
```

### No Audio Input

```bash
# Test recording
arecord -d 5 -f cd test.wav
aplay test.wav

# Check volume
alsamixer

# Try different device
# In darkice.conf: device = plughw:1,0
```

### Can't Connect to Server

```bash
# Test network
ping your-server.com

# Test port
nc -zv your-server.com 8000

# Test HTTP
curl -I http://your-server.com:8000/stream

# Check firewall
sudo ufw status
```

### High CPU Usage

- Lower sample rate (44100 → 22050)
- Lower bitrate (128 → 64)
- Use mono instead of stereo
- Check for other processes: `htop`

### Service Issues

```bash
# Check service status
sudo systemctl status darkice

# View full logs
sudo journalctl -u darkice -n 100

# Restart service
sudo systemctl restart darkice

# Check service file syntax
sudo systemctl daemon-reload
```

## Maintenance

### Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### Backup Configuration
```bash
cp darkice.conf darkice.conf.backup
```

### Monitor Resources
```bash
# CPU and memory
htop

# Network
iftop -i wlan0

# Disk
df -h
```

### Log Rotation
Logs are managed by systemd journal. To limit size:
```bash
sudo nano /etc/systemd/journald.conf
# Set: SystemMaxUse=100M
sudo systemctl restart systemd-journald
```

## Next Steps

- Set up multiple streams
- Configure automatic reconnection
- Add stream metadata
- Set up monitoring/alerting
- Configure backup streams

## Support

For issues:
1. Check logs: `sudo journalctl -u darkice`
2. Run test scripts: `./test_audio.sh`
3. Verify configuration syntax
4. Check hardware connections
5. Test network connectivity


