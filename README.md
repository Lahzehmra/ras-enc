# Shoutcast Audio Encoder & Decoder for Raspberry Pi 5

Complete guide and implementation for streaming audio to and receiving audio from Shoutcast/Icecast servers on Raspberry Pi 5.

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Encoder Setup](#encoder-setup)
5. [Decoder Setup](#decoder-setup)
6. [Usage](#usage)
7. [Troubleshooting](#troubleshooting)

## Overview

This project provides:
- **Encoder**: Stream audio from Raspberry Pi 5 to a Shoutcast/Icecast server
- **Decoder**: Receive and play Shoutcast/Icecast streams on Raspberry Pi 5

### Components
- **Darkice**: Audio encoder for streaming
- **mpg123**: Audio decoder/player for receiving streams
- **ALSA**: Audio system for capture and playback
- **Systemd services**: Auto-start on boot

## Prerequisites

### Hardware
- Raspberry Pi 5
- MicroSD card (32GB+ recommended)
- Audio input device (USB microphone, USB sound card, or line-in)
- Audio output device (speakers, headphones, or HDMI audio)
- Internet connection

### Software
- Raspberry Pi OS (64-bit recommended for Pi 5)
- Root/sudo access

## Installation

### Step 1: Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### Step 2: Install Dependencies

Run the installation script:

```bash
chmod +x install.sh
./install.sh
```

Or manually install:

```bash
sudo apt install -y darkice alsa-utils mpg123 vlc libmp3lame-dev libvorbis-dev libasound2-dev
```

### Step 3: Configure Audio

#### Check Audio Devices

```bash
# List audio input devices
arecord -l

# List audio output devices
aplay -l

# Test microphone
arecord -d 5 -f cd test.wav
aplay test.wav
```

#### Set Default Audio Device (if needed)

Edit `/etc/asound.conf` or create `~/.asoundrc`:

```
pcm.!default {
    type hw
    card 1
    device 0
}

ctl.!default {
    type hw
    card 1
}
```

## Encoder Setup

### Step 1: Configure Darkice

1. Copy the example configuration:
```bash
cp darkice.conf.example darkice.conf
```

2. Edit `darkice.conf` with your Shoutcast server details:
   - Server address
   - Port (usually 8000)
   - Mount point
   - Password
   - Audio source device

### Step 2: Test Encoder

```bash
# Test with configuration file
darkice -c darkice.conf
```

### Step 3: Run as Service

```bash
# Copy service file
sudo cp darkice.service /etc/systemd/system/

# Edit service file if needed
sudo nano /etc/systemd/system/darkice.service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable darkice.service
sudo systemctl start darkice.service

# Check status
sudo systemctl status darkice.service
```

## Decoder Setup

### Step 1: Test Stream Playback

```bash
# Play a Shoutcast stream
mpg123 http://stream.example.com:8000/stream

# Or with VLC
vlc http://stream.example.com:8000/stream
```

### Step 2: Create Playback Script

Use the provided `play_stream.sh` script:

```bash
chmod +x play_stream.sh
./play_stream.sh http://stream.example.com:8000/stream
```

### Step 3: Run as Service (Optional)

For continuous playback, use the systemd service:

```bash
sudo cp stream_player.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable stream_player.service
sudo systemctl start stream_player.service
```

## Usage

### Encoder (Streaming)

#### Start Streaming
```bash
# Manual start
darkice -c darkice.conf

# Or via systemd
sudo systemctl start darkice
```

#### Stop Streaming
```bash
# Manual stop (Ctrl+C)
# Or via systemd
sudo systemctl stop darkice
```

#### View Logs
```bash
sudo journalctl -u darkice -f
```

### Decoder (Receiving)

#### Play Stream
```bash
# Using mpg123
mpg123 http://your-server.com:8000/stream

# Using the script
./play_stream.sh http://your-server.com:8000/stream

# Using VLC
vlc http://your-server.com:8000/stream
```

#### Stop Playback
```bash
# Press Ctrl+C or kill the process
pkill mpg123
```

## Configuration Examples

### Encoder Configuration (darkice.conf)

```ini
[general]
duration = 0        # 0 = infinite
bufferSecs = 5
reconnect = yes

[input]
device = hw:1,0     # Your audio input device
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
name = My Stream
description = Raspberry Pi Stream
```

### Decoder Configuration

Edit `play_stream.sh` and set your stream URL:

```bash
STREAM_URL="http://your-server.com:8000/stream"
```

## Troubleshooting

### Encoder Issues

**Problem: No audio input detected**
```bash
# Check audio devices
arecord -l

# Test recording
arecord -d 5 test.wav

# Adjust device in darkice.conf
```

**Problem: Connection refused**
- Check server address and port
- Verify firewall settings
- Check server password and mount point

**Problem: High CPU usage**
- Reduce sample rate in darkice.conf
- Lower bitrate
- Use hardware encoding if available

### Decoder Issues

**Problem: No audio output**
```bash
# Check audio devices
aplay -l

# Test playback
aplay test.wav

# Check volume
alsamixer
```

**Problem: Stream won't connect**
- Verify stream URL is correct
- Check network connection
- Try different player (mpg123 vs vlc)

### General Issues

**Check audio system:**
```bash
# List all audio devices
cat /proc/asound/cards

# Test ALSA
speaker-test -t wav -c 2
```

**Check network:**
```bash
# Test connection to server
curl -I http://your-server.com:8000/stream
```

## Advanced Configuration

### Multiple Streams
Run multiple Darkice instances with different config files:
```bash
darkice -c darkice1.conf &
darkice -c darkice2.conf &
```

### Recording While Streaming
Use `tee` to split audio:
```bash
arecord -f cd - | tee stream.wav | darkice -c darkice.conf
```

### Monitoring
Monitor stream quality:
```bash
# Check encoder status
sudo systemctl status darkice

# Monitor network usage
iftop -i wlan0

# Check CPU/memory
htop
```

## License

This project is provided as-is for educational and personal use.

## Support

For issues:
1. Check logs: `sudo journalctl -u darkice`
2. Verify configuration files
3. Test audio devices independently
4. Check network connectivity


