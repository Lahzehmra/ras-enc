# Quick Setup Guide - Shoutcast Web UI

## For Fresh Raspberry Pi OS Installation

### Step 1: Flash Raspberry Pi OS

1. Download Raspberry Pi Imager: https://www.raspberrypi.com/software/
2. Flash Raspberry Pi OS (64-bit) to microSD card
3. Enable SSH during imaging (or create `ssh` file in boot partition)
4. Boot your Raspberry Pi

### Step 2: Transfer Files to Pi

**Option A: Using SCP (from your computer)**
```bash
# Replace 'pi' and 'raspberrypi.local' with your credentials
scp -r app.py requirements.txt install_clean.sh templates pi@raspberrypi.local:~/Raspbery/
```

**Option B: Using Git (if you have git on Pi)**
```bash
# On your Pi via SSH:
cd ~
git clone <your-repo-url> Raspbery
cd Raspbery
```

**Option C: Manual Transfer**
- Use FileZilla, WinSCP, or similar
- Transfer all files to `~/Raspbery/` on your Pi

### Step 3: Run Installation

```bash
# SSH into your Pi
ssh pi@raspberrypi.local

# Navigate to project directory
cd ~/Raspbery

# Make installation script executable
chmod +x install_clean.sh

# Run installation
./install_clean.sh
```

The installation will:
- Update system packages
- Install all dependencies (Darkice, mpg123, Python, Flask)
- Set up virtual environment
- Create systemd service
- Configure audio

### Step 4: Start Web Interface

**Option 1: Use Systemd Service (Recommended)**
```bash
sudo systemctl start shoutcast-web
sudo systemctl enable shoutcast-web
```

**Option 2: Manual Start**
```bash
cd ~/Raspbery
source venv/bin/activate
python app.py
```

### Step 5: Access Web UI

Open your web browser:
- `http://raspberrypi.local:5000`
- or `http://<pi-ip-address>:5000`

Find your Pi's IP address:
```bash
hostname -I
```

### Step 6: Configure and Use

1. **Configure Encoder:**
   - Enter Shoutcast server details
   - Set audio device (click "Refresh Devices")
   - Click "Start Streaming"

2. **Play Streams:**
   - Enter stream URL
   - Click "Start Playback"

## Troubleshooting

### Can't Access Web UI

```bash
# Check if service is running
sudo systemctl status shoutcast-web

# Check if port 5000 is listening
sudo netstat -tlnp | grep 5000

# Allow firewall (if enabled)
sudo ufw allow 5000
```

### Service Won't Start

```bash
# Check logs
sudo journalctl -u shoutcast-web -n 50

# Try manual start to see errors
cd ~/Raspbery
source venv/bin/activate
python app.py
```

### Audio Not Working

```bash
# Check audio group
groups  # Should include 'audio'

# If not, add yourself:
sudo usermod -aG audio $USER
# Then logout and login

# Test audio
speaker-test -t wav -c 2
```

## Files Needed

Make sure you have these files in `~/Raspbery/`:
- `app.py` - Flask web application
- `requirements.txt` - Python dependencies
- `install_clean.sh` - Installation script
- `templates/index.html` - Web UI template

## Next Steps

After installation:
1. Access web UI at `http://raspberrypi.local:5000`
2. Configure your Shoutcast server details
3. Start streaming or playing!

For detailed documentation, see `README_WEB_UI.md`


