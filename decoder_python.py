#!/usr/bin/env python3
"""
Shoutcast/Icecast Stream Decoder (Python Alternative)
This script provides a Python-based alternative to mpg123 for playing streams
"""

import sys
import argparse
import subprocess
import signal
import time

def check_dependencies():
    """Check if required Python packages are available"""
    try:
        import pyaudio
        import requests
        return True
    except ImportError as e:
        print(f"Error: Missing dependency - {e.name}")
        print("\nInstall dependencies with:")
        print("  pip3 install pyaudio requests")
        print("\nOr use the shell script: ./play_stream.sh")
        return False

def play_stream_mpg123(url):
    """Fallback to mpg123 if available"""
    try:
        subprocess.run(['mpg123', '-v', '-C', url], check=True)
    except FileNotFoundError:
        print("Error: mpg123 not found")
        print("Install with: sudo apt install mpg123")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nPlayback stopped by user")
        sys.exit(0)

def play_stream_python(url):
    """Play stream using Python libraries"""
    try:
        import pyaudio
        import requests
    except ImportError:
        return False
    
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    RATE = 44100
    
    # Initialize PyAudio
    p = pyaudio.PyAudio()
    
    # Open stream
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True,
                    frames_per_buffer=CHUNK)
    
    print(f"Connecting to: {url}")
    print("Press Ctrl+C to stop")
    
    try:
        # Stream audio data
        response = requests.get(url, stream=True, timeout=5)
        response.raise_for_status()
        
        for chunk in response.iter_content(chunk_size=CHUNK):
            if chunk:
                stream.write(chunk)
                
    except KeyboardInterrupt:
        print("\nPlayback stopped by user")
    except requests.RequestException as e:
        print(f"Error connecting to stream: {e}")
        return False
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
    
    return True

def main():
    parser = argparse.ArgumentParser(
        description='Shoutcast/Icecast Stream Player (Python)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s http://stream.example.com:8000/stream
  %(prog)s http://icecast.example.com:8000/live.mp3 --use-mpg123
        """
    )
    
    parser.add_argument('url', 
                       help='Stream URL (e.g., http://server.com:8000/stream)')
    parser.add_argument('--use-mpg123', 
                       action='store_true',
                       help='Use mpg123 instead of Python (recommended)')
    parser.add_argument('--test', 
                       action='store_true',
                       help='Test connection without playing')
    
    args = parser.parse_args()
    
    # Test connection
    if args.test:
        print(f"Testing connection to: {args.url}")
        try:
            import requests
            response = requests.head(args.url, timeout=5)
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
            return 0
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    # Use mpg123 if requested or if Python dependencies missing
    if args.use_mpg123 or not check_dependencies():
        play_stream_mpg123(args.url)
    else:
        if not play_stream_python(args.url):
            print("Falling back to mpg123...")
            play_stream_mpg123(args.url)

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)


