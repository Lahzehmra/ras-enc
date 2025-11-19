#!/bin/bash

# Audio Device Test Script
# This script helps you identify and test your audio devices

echo "========================================="
echo "Audio Device Test for Raspberry Pi 5"
echo "========================================="
echo ""

# Check ALSA
echo "[1] Checking ALSA installation..."
if command -v arecord &> /dev/null && command -v aplay &> /dev/null; then
    echo "✓ ALSA tools installed"
else
    echo "✗ ALSA tools not found"
    echo "Install with: sudo apt install alsa-utils"
    exit 1
fi

echo ""
echo "[2] Available Audio Input Devices:"
echo "-----------------------------------"
arecord -l
echo ""

echo "[3] Available Audio Output Devices:"
echo "-----------------------------------"
aplay -l
echo ""

# Test recording
echo "[4] Testing Audio Input..."
echo "Recording 3 seconds of audio..."
echo "Speak into your microphone now!"
arecord -d 3 -f cd -t wav test_input.wav 2>/dev/null

if [ -f test_input.wav ]; then
    echo "✓ Recording successful"
    FILE_SIZE=$(stat -f%z test_input.wav 2>/dev/null || stat -c%s test_input.wav 2>/dev/null)
    if [ "$FILE_SIZE" -gt 1000 ]; then
        echo "✓ Audio data detected (file size: $FILE_SIZE bytes)"
    else
        echo "⚠ Warning: File is very small, may be silent"
    fi
else
    echo "✗ Recording failed"
fi

echo ""
echo "[5] Testing Audio Output..."
if [ -f test_input.wav ]; then
    echo "Playing back recorded audio..."
    aplay test_input.wav 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✓ Playback successful"
    else
        echo "✗ Playback failed"
    fi
    echo ""
    read -p "Did you hear the audio? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "✓ Audio system working correctly"
    else
        echo "⚠ Audio output may have issues"
        echo "Try: alsamixer (to adjust volume)"
    fi
else
    echo "Skipping playback test (no recording available)"
fi

# Test speaker
echo ""
echo "[6] Testing Speaker Output..."
echo "Playing test tone (left channel)..."
speaker-test -t wav -c 2 -l 1 -s 1 2>/dev/null &
SPEAKER_PID=$!
sleep 2
kill $SPEAKER_PID 2>/dev/null
echo "Did you hear the test tone?"

# Check Darkice
echo ""
echo "[7] Checking Darkice Installation..."
if command -v darkice &> /dev/null; then
    echo "✓ Darkice installed"
    darkice --version 2>/dev/null || echo "  Version check unavailable"
else
    echo "✗ Darkice not installed"
    echo "Install with: sudo apt install darkice"
fi

# Check mpg123
echo ""
echo "[8] Checking Audio Players..."
if command -v mpg123 &> /dev/null; then
    echo "✓ mpg123 installed"
else
    echo "✗ mpg123 not installed"
fi

if command -v vlc &> /dev/null; then
    echo "✓ VLC installed"
else
    echo "✗ VLC not installed"
fi

# Cleanup
echo ""
echo "[9] Cleaning up..."
if [ -f test_input.wav ]; then
    read -p "Delete test file? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm test_input.wav
        echo "✓ Test file deleted"
    else
        echo "Test file kept: test_input.wav"
    fi
fi

echo ""
echo "========================================="
echo "Test Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Note the card/device numbers from step 2"
echo "2. Edit darkice.conf with your device: device = hw:CARD,DEVICE"
echo "3. Configure your Shoutcast server details"
echo "4. Run: ./start_encoder.sh"


