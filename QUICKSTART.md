# Quick Start Guide - Shoutcast Encoder/Decoder

## 5-Minute Setup

### 1. Install Everything
```bash
chmod +x install.sh
./install.sh
```

### 2. Find Your Audio Devices
```bash
# Input devices (microphone)
arecord -l

# Output devices (speakers)
aplay -l
```

### 3. Configure Encoder
```bash
# Copy example config
cp darkice.conf.example darkice.conf

# Edit with your details
nano darkice.conf
```

**Important settings to change:**
- `device = hw:1,0` (use number from `arecord -l`)
- `server = your-server.com`
- `port = 8000`
- `password = yourpassword`
- `mountPoint = /stream`

### 4. Test Audio Input
```bash
# Record 5 seconds
arecord -d 5 -f cd test.wav

# Play it back
aplay test.wav
```

### 5. Start Streaming
```bash
# Start encoder
./start_encoder.sh
```

### 6. Test Decoder
```bash
# Play a stream (use your server URL)
./play_stream.sh http://your-server.com:8000/stream
```

## Common Configurations

### USB Microphone
```ini
device = plughw:1,0
sampleRate = 44100
channel = 1  # Mono for voice
```

### Line Input
```ini
device = hw:1,0
sampleRate = 44100
channel = 2  # Stereo
```

### HDMI Audio (Pi 5)
```ini
device = hw:0,3  # HDMI audio device
```

## Troubleshooting Quick Fixes

**No audio input:**
```bash
alsamixer  # Adjust volume levels
```

**Can't connect to server:**
```bash
# Test connection
curl -I http://your-server.com:8000/stream
```

**High CPU usage:**
- Lower `sampleRate` to 22050
- Lower `bitrate` to 64

**Service won't start:**
```bash
sudo systemctl status darkice
sudo journalctl -u darkice -n 50
```


