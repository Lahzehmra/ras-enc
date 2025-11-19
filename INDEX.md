# Project Index - Shoutcast Encoder/Decoder

## 📚 Documentation Files

| File | Purpose | When to Use |
|------|---------|-------------|
| **README.md** | Complete reference guide | Full documentation, troubleshooting |
| **QUICKSTART.md** | 5-minute setup guide | Fast setup if you're experienced |
| **SETUP_GUIDE.md** | Detailed step-by-step walkthrough | First time setup, learning |
| **PROJECT_SUMMARY.md** | Overview and quick reference | Understanding project structure |
| **INDEX.md** | This file - navigation guide | Finding what you need |

## 🚀 Getting Started

**New to this project?** Start here:
1. Read **SETUP_GUIDE.md** for complete walkthrough
2. Or **QUICKSTART.md** for fast setup
3. Use **README.md** as reference

**Just need a reminder?** Check **PROJECT_SUMMARY.md**

## 📋 Scripts Reference

### Installation & Setup
- `install.sh` - Install all dependencies
- `setup_pi5.sh` - Raspberry Pi 5 specific configuration
- `test_audio.sh` - Test and identify audio hardware

### Encoder (Streaming)
- `start_encoder.sh` - Start streaming
- `stop_encoder.sh` - Stop streaming
- `darkice.conf.example` - Configuration template

### Decoder (Receiving)
- `play_stream.sh` - Play Shoutcast streams
- `decoder_python.py` - Python alternative player

### Services
- `darkice.service` - Auto-start encoder on boot
- `stream_player.service` - Auto-play stream on boot

## 🔧 Configuration Files

- `darkice.conf.example` → Copy to `darkice.conf` and edit
- `requirements.txt` - Python dependencies (optional)

## 📖 Documentation by Topic

### Installation
- **SETUP_GUIDE.md** - Part 1 & 2
- **QUICKSTART.md** - Steps 1-2

### Encoder Setup
- **SETUP_GUIDE.md** - Part 3
- **README.md** - "Encoder Setup" section
- **QUICKSTART.md** - Steps 3-5

### Decoder Setup
- **SETUP_GUIDE.md** - Part 4
- **README.md** - "Decoder Setup" section
- **QUICKSTART.md** - Step 6

### Services & Automation
- **SETUP_GUIDE.md** - Part 5
- **README.md** - "Usage" section

### Troubleshooting
- **README.md** - "Troubleshooting" section
- **SETUP_GUIDE.md** - "Troubleshooting" section
- **PROJECT_SUMMARY.md** - "Troubleshooting Quick Fixes"

## 🎯 Common Tasks

### First Time Setup
```
1. Read SETUP_GUIDE.md
2. Run: ./setup_pi5.sh
3. Run: ./install.sh
4. Run: ./test_audio.sh
5. Configure: darkice.conf
```

### Start Streaming
```
./start_encoder.sh
# Or with service:
sudo systemctl start darkice
```

### Play a Stream
```
./play_stream.sh http://server.com:8000/stream
```

### Check Status
```
sudo systemctl status darkice
sudo journalctl -u darkice -f
```

### Troubleshoot Audio
```
./test_audio.sh
arecord -l
aplay -l
alsamixer
```

## 📁 File Locations

All files are in: `/home/pi/Raspbery/` (or your project directory)

After installation:
- Config: `darkice.conf` (create from example)
- Logs: `logs/` directory
- Services: `/etc/systemd/system/`

## 🔍 Quick Search

**Need to find...**

- **How to install?** → `install.sh` or SETUP_GUIDE.md Part 2
- **How to configure?** → `darkice.conf.example` or SETUP_GUIDE.md Part 3
- **How to test?** → `test_audio.sh` or SETUP_GUIDE.md Part 6
- **How to troubleshoot?** → README.md "Troubleshooting"
- **What are the scripts?** → PROJECT_SUMMARY.md "File Descriptions"
- **Quick commands?** → PROJECT_SUMMARY.md "Quick Reference"

## 💡 Tips

1. **Always test first**: Use `test_audio.sh` before configuring
2. **Start simple**: Use default settings, then optimize
3. **Check logs**: `sudo journalctl -u darkice` for issues
4. **Backup config**: Copy `darkice.conf` before major changes
5. **Read errors**: Error messages usually tell you what's wrong

## 🆘 Getting Help

1. Check **README.md** troubleshooting section
2. Run **test_audio.sh** to verify hardware
3. Check service logs: `sudo journalctl -u darkice`
4. Verify configuration syntax
5. Test network connectivity

## 📝 Next Steps After Setup

1. ✅ Test encoder and decoder
2. ✅ Set up systemd services
3. ✅ Configure auto-start on boot
4. ✅ Monitor performance
5. ✅ Optimize settings for your use case

---

**Ready to start?** Begin with **SETUP_GUIDE.md** or **QUICKSTART.md**!


