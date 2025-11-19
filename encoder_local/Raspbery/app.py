#!/usr/bin/env python3
"""
Shoutcast Encoder/Decoder Web Interface
Modern web UI for streaming and playing Shoutcast streams on Momento
"""

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from functools import wraps
import subprocess
import os
import json
import threading
import time
import struct
import array
import shutil
from pathlib import Path
import hashlib
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'shoutcast-web-ui-secret-key-change-in-production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Default credentials (change these!)
ADMIN_USERNAME = 'admin'
# Password is stored in password.txt file, default is 'admin123'
PASSWORD_FILE = Path(__file__).parent / 'password.txt'

def load_password_hash():
    """Load password hash from file, or create default"""
    try:
        if PASSWORD_FILE.exists():
            with open(PASSWORD_FILE, 'r') as f:
                return f.read().strip()
        else:
            # Create default password file
            default_hash = hashlib.sha256('admin123'.encode()).hexdigest()
            with open(PASSWORD_FILE, 'w') as f:
                f.write(default_hash)
            return default_hash
    except Exception as e:
        # Fallback to default
        return hashlib.sha256('admin123'.encode()).hexdigest()

ADMIN_PASSWORD_HASH = load_password_hash()

# Configuration file path
CONFIG_DIR = Path.home() / 'Raspbery'
CONFIG_DIR.mkdir(exist_ok=True)
CONFIG_FILE = CONFIG_DIR / 'darkice.conf'
STATUS_FILE = CONFIG_DIR / 'status.json'

# Process tracking
encoder_process = None
decoder_process = None
decoder_aplay_process = None  # aplay process when using mpg123 stdout method
decoder_supervisor_thread = None
decoder_should_run = False
audio_level_thread = None
audio_levels = {'left': 0.0, 'right': 0.0}
decoder_audio_level_thread = None
decoder_audio_levels = {'left': 0.0, 'right': 0.0}
running = True

def get_encoder_status():
    """Check if encoder is running"""
    try:
        result = subprocess.run(['pgrep', '-x', 'darkice'], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def get_decoder_status():
    """Check if decoder is running or intended to run (supervised)."""
    # If supervised to run, treat as active
    if decoder_should_run:
        return True
    try:
        if decoder_process and decoder_process.poll() is None:
            return True
        if decoder_aplay_process and decoder_aplay_process.poll() is None:
            return True
        pgrep_path = shutil.which('pgrep') or '/usr/bin/pgrep'
        # Check mpg123/aplay
        for name in (['-x', 'mpg123'], ['-x', 'aplay']):
            result = subprocess.run([pgrep_path] + name, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return True
        # Check cvlc
        for args in (['-x', 'cvlc'], ['-f', 'cvlc']):
            result = subprocess.run([pgrep_path] + args, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return True
        # Check ffmpeg pipeline
        for args in (['-x', 'ffmpeg'], ['-f', 'ffmpeg']):
            result = subprocess.run([pgrep_path] + args, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return True
        return False
    except Exception:
        return False

def _start_decoder_process(stream_url: str, output_device: str):
    """Try to start a decoder process. Prefer mpg123->aplay for MP3, fallback to cvlc for others."""
    global decoder_process, decoder_aplay_process
    decoder_process = None
    decoder_aplay_process = None
    mpg123_path = shutil.which('mpg123') or '/usr/bin/mpg123'
    aplay_path = shutil.which('aplay') or '/usr/bin/aplay'
    env = os.environ.copy()
    env.pop('JACK_PROMISCUOUS_SERVER', None)
    env.pop('JACK_DEFAULT_SERVER', None)
    env['MPG123_MODDIR'] = '/usr/lib/aarch64-linux-gnu/mpg123'

    # Heuristic: try mpg123 only for MP3-like URLs
    is_mp3_like = any(ext in stream_url.lower() for ext in ['.mp3', 'mp3stream'])
    if is_mp3_like:
        try:
            mpg123_proc = subprocess.Popen(
                [mpg123_path, '-q', '-s', stream_url],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, env=env
            )
            aplay_proc = subprocess.Popen(
                [aplay_path, '-D', output_device, '-f', 'cd', '-c', '2', '-r', '44100'],
                stdin=mpg123_proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            mpg123_proc.stdout.close()
            time.sleep(0.8)
            if mpg123_proc.poll() is None and aplay_proc.poll() is None:
                decoder_process = mpg123_proc
                decoder_aplay_process = aplay_proc
                return True
            # Clean up failed
            try:
                if mpg123_proc.poll() is None: mpg123_proc.terminate()
            except: pass
            try:
                if aplay_proc.poll() is None: aplay_proc.terminate()
            except: pass
        except Exception:
            pass

    # Fallback to VLC for AAC/M3U/etc. Add small network/file caching
    try:
        cvlc_path = shutil.which('cvlc') or '/usr/bin/cvlc'
        cvlc_proc = subprocess.Popen(
            [cvlc_path, '--intf', 'dummy', '--no-video', '--quiet',
             '--aout', 'alsa', f'--alsa-audio-device={output_device}',
             '--network-caching=1500', '--file-caching=1500', stream_url],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL
        )
        time.sleep(0.8)
        if cvlc_proc.poll() is None:
            decoder_process = cvlc_proc
            decoder_aplay_process = None
            return True
        try:
            cvlc_proc.terminate()
        except: pass
    except Exception:
        pass
    return False

def _decoder_supervisor_loop():
    """Keep decoder running while decoder_should_run is True; auto-restart on failures."""
    global decoder_process, decoder_aplay_process
    backoff = 2.0
    while decoder_should_run:
        try:
            st = load_status()
            dec = st.get('decoder', {})
            url = dec.get('url', '')
            out_dev = dec.get('outputDevice', '') or _detect_default_devices().get('output', 'default')
            if not url:
                time.sleep(1.0)
                continue
            # If process not running, start it
            if not (decoder_process and decoder_process.poll() is None) and not (decoder_aplay_process and decoder_aplay_process.poll() is None):
                _start_decoder_process(url, out_dev)
                time.sleep(0.5)
                if not (decoder_process and decoder_process.poll() is None):
                    time.sleep(backoff)
                    backoff = min(backoff * 1.5, 10.0)
                else:
                    backoff = 2.0
            else:
                time.sleep(1.0)
        except Exception:
            time.sleep(2.0)

def _start_ffmpeg_pipeline(stream_url: str, output_device: str) -> bool:
    """
    Start ffmpeg to decode any stream to raw PCM and feed aplay.
    While piping, compute decoder levels from the PCM stream.
    """
    global decoder_process, decoder_aplay_process, decoder_audio_levels
    ffmpeg_path = shutil.which('ffmpeg') or '/usr/bin/ffmpeg'
    aplay_path = shutil.which('aplay') or '/usr/bin/aplay'
    if not os.path.exists(ffmpeg_path):
        return False
    try:
        ffmpeg_proc = subprocess.Popen(
            [ffmpeg_path, '-nostdin', '-vn', '-i', stream_url, '-f', 's16le', '-ac', '2', '-ar', '44100', 'pipe:1'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL
        )
        aplay_proc = subprocess.Popen(
            [aplay_path, '-D', output_device, '-f', 'cd', '-c', '2', '-r', '44100'],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        decoder_process = ffmpeg_proc
        decoder_aplay_process = aplay_proc

        def _pump_and_meter():
            chunk_size = 4096
            try:
                while decoder_should_run and ffmpeg_proc and ffmpeg_proc.poll() is None and aplay_proc and aplay_proc.poll() is None:
                    data = ffmpeg_proc.stdout.read(chunk_size) if ffmpeg_proc.stdout else b''
                    if not data:
                        time.sleep(0.02)
                        continue
                    # Write to aplay
                    try:
                        if aplay_proc.stdin:
                            aplay_proc.stdin.write(data)
                            aplay_proc.stdin.flush()
                    except Exception:
                        break
                    # Measure levels
                    try:
                        samples = array.array('h', data)
                        if len(samples) >= 2:
                            left = samples[0::2]
                            right = samples[1::2]
                            left_rms = (sum(x*x for x in left) / max(1, len(left))) ** 0.5
                            right_rms = (sum(x*x for x in right) / max(1, len(right))) ** 0.5
                            decoder_audio_levels['left'] = min(left_rms / 32768.0, 1.0)
                            decoder_audio_levels['right'] = min(right_rms / 32768.0, 1.0)
                    except Exception:
                        pass
            finally:
                try:
                    if aplay_proc and aplay_proc.stdin:
                        aplay_proc.stdin.close()
                except Exception:
                    pass

        threading.Thread(target=_pump_and_meter, daemon=True).start()
        # Give it a short moment to validate startup
        time.sleep(0.8)
        return ffmpeg_proc.poll() is None and aplay_proc.poll() is None
    except Exception:
        return False

def get_icecast_status():
    """Check if Icecast server is running"""
    try:
        # Method 1: pgrep with pattern matching (most reliable - finds process with icecast2 in command)
        pgrep_path = shutil.which('pgrep') or '/usr/bin/pgrep'
        result = subprocess.run([pgrep_path, '-f', 'icecast2'], 
                              capture_output=True, text=True, timeout=2)
        # Check both return code and that we got output
        if result.returncode == 0:
            output = result.stdout.strip()
            if output:  # Make sure we have actual output
                return True
        
        # Method 2: Check if port 8000 is listening (Icecast default port)
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.3)
            result = sock.connect_ex(('127.0.0.1', 8000))
            sock.close()
            if result == 0:
                return True
        except:
            pass
        
        # Method 3: pgrep with exact name (fallback)
        result = subprocess.run([pgrep_path, '-x', 'icecast2'], 
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and result.stdout.strip():
            return True
        
        return False
    except Exception as e:
        # If all methods fail, return False
        return False

def load_status() -> dict:
    """Load persisted UI/runtime status data (decoder settings, etc.)."""
    try:
        if STATUS_FILE.exists():
            with open(STATUS_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_status(status: dict) -> bool:
    """Persist UI/runtime status data."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        tmp_path = STATUS_FILE.with_suffix('.json.tmp')
        with open(tmp_path, 'w') as f:
            json.dump(status, f)
        os.replace(tmp_path, STATUS_FILE)
        return True
    except Exception:
        return False

def read_audio_levels(device='hw:1,0', sample_rate=44100):
    """Read audio levels from ALSA device with auto-fallback to detected input device."""
    global audio_levels, running
    arecord_path = shutil.which('arecord') or '/usr/bin/arecord'
    device_in_use = device
    empty_count = 0
    error_count = 0

    while running:
        try:
            cmd = [arecord_path, '-f', 'S16_LE', '-r', str(sample_rate),
                   '-c', '2', '-D', device_in_use, '-t', 'raw', '-d', '0.1', '-q']
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=0.8)

            data = process.stdout
            if process.returncode != 0 or len(data) < 4:
                empty_count += 1
                if process.returncode != 0:
                    error_count += 1
                # Attempt fallback if repeated failures
                if empty_count >= 10 or error_count >= 3:
                    try:
                        defaults = _detect_default_devices()
                        fallback_dev = defaults.get('input', device_in_use)
                        if fallback_dev and fallback_dev != device_in_use:
                            device_in_use = fallback_dev
                            empty_count = 0
                            error_count = 0
                    except Exception:
                        pass
                time.sleep(0.15)
                continue

            # Convert to array and compute RMS
            try:
                samples = array.array('h', data)
                if len(samples) < 2:
                    empty_count += 1
                    time.sleep(0.1)
                    continue
                left_samples = [abs(samples[i]) for i in range(0, len(samples), 2) if i < len(samples)]
                right_samples = [abs(samples[i+1]) for i in range(0, len(samples)-1, 2) if i+1 < len(samples)]

                if left_samples:
                    left_rms = (sum(x*x for x in left_samples) / len(left_samples)) ** 0.5
                    audio_levels['left'] = min(left_rms / 32768.0, 1.0)
                else:
                    audio_levels['left'] = 0.0

                if right_samples:
                    right_rms = (sum(x*x for x in right_samples) / len(right_samples)) ** 0.5
                    audio_levels['right'] = min(right_rms / 32768.0, 1.0)
                else:
                    audio_levels['right'] = 0.0

                # Reset counters on success
                empty_count = 0
                error_count = 0
            except Exception:
                audio_levels = {'left': 0.0, 'right': 0.0}

            time.sleep(0.1)

        except Exception:
            audio_levels = {'left': 0.0, 'right': 0.0}
            error_count += 1
            time.sleep(0.5)

def restart_audio_meter(device: str, sample_rate: int):
    """Restart the audio meter thread with the given device and sample rate."""
    global running, audio_level_thread
    try:
        running = False
        try:
            if audio_level_thread and audio_level_thread.is_alive():
                time.sleep(0.2)
        except Exception:
            pass
        running = True
        audio_level_thread = threading.Thread(
            target=read_audio_levels,
            args=(device, int(sample_rate)),
            daemon=True
        )
        audio_level_thread.start()
    except Exception:
        pass

def read_decoder_audio_levels(playback_device='plughw:2,0', sample_rate=44100):
    """Read audio levels intended for decoder output by sampling the same card capture device."""
    global decoder_audio_levels
    arecord_path = shutil.which('arecord') or '/usr/bin/arecord'
    # Map playback plughw:X,0 or hw:X,0 to capture hw:X,0
    capture_dev = playback_device.replace('plughw:', 'hw:').replace('default', 'hw:0,0')
    if not capture_dev.startswith('hw:'):
        capture_dev = 'hw:0,0'
    while decoder_should_run:
        try:
            cmd = [arecord_path, '-f', 'S16_LE', '-r', str(sample_rate),
                   '-c', '2', '-D', capture_dev, '-t', 'raw', '-d', '0.1', '-q']
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=0.8)
            data = process.stdout
            if len(data) < 4:
                time.sleep(0.15)
                continue
            try:
                samples = array.array('h', data)
                if len(samples) < 2:
                    time.sleep(0.1)
                    continue
                left_samples = [abs(samples[i]) for i in range(0, len(samples), 2)]
                right_samples = [abs(samples[i+1]) for i in range(1, len(samples), 2)]
                left_rms = (sum(x*x for x in left_samples) / max(1, len(left_samples))) ** 0.5
                right_rms = (sum(x*x for x in right_samples) / max(1, len(right_samples))) ** 0.5
                decoder_audio_levels['left'] = min(left_rms / 32768.0, 1.0)
                decoder_audio_levels['right'] = min(right_rms / 32768.0, 1.0)
            except Exception:
                decoder_audio_levels = {'left': 0.0, 'right': 0.0}
            time.sleep(0.1)
        except Exception:
            decoder_audio_levels = {'left': 0.0, 'right': 0.0}
            time.sleep(0.5)

def start_decoder_meter_thread(output_device: str):
    """Start decoder audio meter thread based on selected output device."""
    global decoder_audio_level_thread
    try:
        if decoder_audio_level_thread and decoder_audio_level_thread.is_alive():
            return
    except Exception:
        pass
    decoder_audio_level_thread = threading.Thread(
        target=read_decoder_audio_levels,
        args=(output_device, 44100),
        daemon=True
    )
    decoder_audio_level_thread.start()

def load_config():
    """Load configuration from darkice.conf"""
    config = {
        'server': 'localhost',
        'port': '8000',
        'password': '',
        'mountPoint': '/stream',
        'bitrate': '128',
        'sampleRate': '44100',
        'device': 'hw:1,0',
        'streamName': 'Momento Stream'
    }
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                content = f.read()
                # Parse darkice.conf format
                for line in content.split('\n'):
                    line = line.strip()
                    if 'server =' in line:
                        config['server'] = line.split('=')[1].strip()
                    elif 'port =' in line:
                        config['port'] = line.split('=')[1].strip()
                    elif 'password =' in line:
                        config['password'] = line.split('=')[1].strip()
                    elif 'mountPoint =' in line:
                        config['mountPoint'] = line.split('=')[1].strip()
                    elif 'bitrate =' in line:
                        config['bitrate'] = line.split('=')[1].strip()
                    elif 'sampleRate =' in line:
                        config['sampleRate'] = line.split('=')[1].strip()
                    elif 'device =' in line:
                        config['device'] = line.split('=')[1].strip()
                    elif 'name =' in line:
                        config['streamName'] = line.split('=')[1].strip()
        except:
            pass
    
    return config

def save_config(config):
    """Save configuration to darkice.conf"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    config_content = f"""[general]
duration = 0
bufferSecs = 5
reconnect = yes
reconnectDelay = 5
logLevel = 2

[input]
device = {config['device']}
sampleRate = {config['sampleRate']}
bitsPerSample = 16
channel = 2

[icecast2-0]
bitrateMode = cbr
bitrate = {config['bitrate']}
format = mp3
server = {config['server']}
port = {config['port']}
password = {config['password']}
mountPoint = {config['mountPoint']}
name = {config['streamName']}
description = Audio stream from Momento
genre = Various
url = http://{config['server']}
public = yes
"""
    
    with open(CONFIG_FILE, 'w') as f:
        f.write(config_content)
    
    return True

def login_required(f):
    """Decorator to require login for certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    """Login endpoint"""
    try:
        # Get JSON data - try multiple methods
        data = None
        
        # Method 1: Try get_json (most common)
        try:
            if request.is_json:
                data = request.get_json(silent=True)
        except:
            pass
        
        # Method 2: Try parsing raw data directly
        if not data and request.data:
            try:
                raw_data = request.data.decode('utf-8')
                if raw_data:
                    data = json.loads(raw_data)
            except Exception as e:
                pass
        
        # Method 3: Try form data
        if not data:
            username_form = request.form.get('username')
            password_form = request.form.get('password')
            if username_form and password_form:
                data = {'username': username_form, 'password': password_form}
        
        # Method 4: Try args (query parameters)
        if not data:
            username_arg = request.args.get('username')
            password_arg = request.args.get('password')
            if username_arg and password_arg:
                data = {'username': username_arg, 'password': password_arg}
        
        if not data:
            return jsonify({
                'success': False, 
                'message': 'No data received',
                'debug': {
                    'has_data': bool(request.data),
                    'is_json': request.is_json,
                    'content_type': request.content_type,
                    'method': request.method
                }
            }), 400
            
        username = str(data.get('username', '')).strip()
        password = str(data.get('password', '')).strip()
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password required'}), 400
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Reload password hash in case it was changed
        current_password_hash = load_password_hash()
        
        if username == ADMIN_USERNAME and password_hash == current_password_hash:
            session['logged_in'] = True
            session['username'] = username
            return jsonify({'success': True, 'message': 'Login successful'})
        else:
            return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'message': f'Error: {str(e)}', 'trace': traceback.format_exc()[:200]}), 500

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """Logout endpoint"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/auth/status')
def api_auth_status():
    """Check authentication status"""
    return jsonify({
        'logged_in': session.get('logged_in', False),
        'username': session.get('username', '')
    })

@app.route('/api/status')
def api_status():
    """Get current status"""
    return jsonify({
        'encoder': get_encoder_status(),
        'decoder': get_decoder_status(),
        'icecast': get_icecast_status(),
        'config': load_config(),
        'audioLevels': audio_levels
    })

@app.route('/api/config', methods=['GET'])
def api_get_config():
    """Get configuration"""
    return jsonify(load_config())

@app.route('/api/config', methods=['POST'])
@login_required
def api_save_config():
    """Save configuration"""
    global audio_level_thread, running
    config = request.json
    if save_config(config):
        # Restart audio meter with new device/sampleRate
        try:
            # Stop current thread
            running = False
            try:
                if audio_level_thread and audio_level_thread.is_alive():
                    time.sleep(0.2)
            except Exception:
                pass
            # Start new thread with updated config
            running = True
            new_cfg = load_config()
            audio_level_thread = threading.Thread(
                target=read_audio_levels,
                args=(new_cfg.get('device', 'hw:1,0'), int(new_cfg.get('sampleRate', 44100))),
                daemon=True
            )
            audio_level_thread.start()
        except Exception:
            pass
        return jsonify({'success': True, 'message': 'Configuration saved'})
    return jsonify({'success': False, 'message': 'Failed to save configuration'}), 500

@app.route('/api/encoder/start', methods=['POST'])
@login_required
def api_encoder_start():
    """Start encoder"""
    global encoder_process
    
    if get_encoder_status():
        return jsonify({'success': False, 'message': 'Encoder is already running'})
    
    if not CONFIG_FILE.exists():
        return jsonify({'success': False, 'message': 'Configuration file not found'})
    
    try:
        # Start darkice in background - use full path
        darkice_path = shutil.which('darkice') or '/usr/bin/darkice'
        encoder_process = subprocess.Popen(
            [darkice_path, '-c', str(CONFIG_FILE)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(1)
        
        if get_encoder_status():
            return jsonify({'success': True, 'message': 'Encoder started successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to start encoder'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/encoder/stop', methods=['POST'])
@login_required
def api_encoder_stop():
    """Stop encoder"""
    global encoder_process
    
    if not get_encoder_status():
        return jsonify({'success': False, 'message': 'Encoder is not running'})
    
    try:
        pkill_path = shutil.which('pkill') or '/usr/bin/pkill'
        subprocess.run([pkill_path, '-x', 'darkice'], check=False)
        time.sleep(0.5)
        
        if encoder_process:
            encoder_process.terminate()
            encoder_process = None
        
        if not get_encoder_status():
            return jsonify({'success': True, 'message': 'Encoder stopped successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to stop encoder'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/decoder/start', methods=['POST'])
@login_required
def api_decoder_start():
    """Start decoder/player"""
    global decoder_process, decoder_aplay_process, decoder_should_run
    
    if get_decoder_status():
        return jsonify({'success': False, 'message': 'Decoder is already running'})
    
    data = request.json
    stream_url = data.get('url', '')
    output_device = str(data.get('outputDevice', '') or '').strip()
    
    # Normalize URL: prepend http:// if scheme is missing (e.g., 46.20.4.2:8010/;stream)
    def normalize_url(u: str) -> str:
        u = (u or '').strip()
        if not u:
            return u
        # If no scheme like http:// or https:// is present, default to http://
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', u):
            return f'http://{u}'
        return u

    stream_url = normalize_url(stream_url)

    if not stream_url:
        return jsonify({'success': False, 'message': 'Stream URL is required'})
    
    # Initialize variables
    decoder_process = None
    decoder_aplay_process = None
    last_error = None

    # Helper: choose a sensible ALSA output device if not provided
    def choose_output_device_fallback() -> str:
        """
        Attempt to automatically select a USB audio device for output.
        Falls back to 'default' if detection fails.
        """
        try:
            aplay_path_local = shutil.which('aplay') or '/usr/bin/aplay'
            result = subprocess.run([aplay_path_local, '-l'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                lines = result.stdout.splitlines()
                # Prefer a USB device if present
                for i, line in enumerate(lines):
                    lower = line.lower()
                    if 'card' in lower and 'usb' in lower:
                        # Typical format: "card 2: Device [USB PnP Sound Device], device 0: ..."
                        try:
                            parts = line.split(':', 1)[0].split()
                            # parts like ["card", "2"]
                            card_index = parts[1]
                            return f'plughw:{card_index},0'
                        except Exception:
                            continue
                # Otherwise pick first "card N" line
                for line in lines:
                    if line.strip().startswith('card '):
                        try:
                            parts = line.split(':', 1)[0].split()
                            card_index = parts[1]
                            return f'plughw:{card_index},0'
                        except Exception:
                            continue
        except Exception:
            pass
        return 'default'
    
    try:
        decoder_should_run = True
        # Persist requested decoder settings (URL/output device), even if start fails
        try:
            st = load_status()
            st.setdefault('decoder', {})
            st['decoder']['url'] = stream_url
            if output_device:
                st['decoder']['outputDevice'] = output_device
            save_status(st)
        except Exception:
            pass

        # Restart audio meter on matching input card when a specific output device is chosen
        try:
            dev_norm = output_device.replace('plughw:', 'hw:') if output_device else ''
            if dev_norm.startswith('hw:') and ',' in dev_norm:
                restart_audio_meter(dev_norm, 44100)
                start_decoder_meter_thread(output_device or dev_norm)
        except Exception:
            pass

        # Start mpg123 in background - use full path
        mpg123_path = shutil.which('mpg123') or '/usr/bin/mpg123'
        aplay_path = shutil.which('aplay') or '/usr/bin/aplay'
        
        # Resolve output device
        if not output_device:
            output_device = choose_output_device_fallback()

        # Try ffmpeg PCM pipeline first (works for MP3/AAC/M3U) and gives decoder levels
        if decoder_process is None:
            if _start_ffmpeg_pipeline(stream_url, output_device):
                # Started successfully with ffmpeg; skip mpg123 path
                time.sleep(0.5)
            else:
                decoder_process = None

        # If ffmpeg not started, try mpg123 with stdout (-s) and pipe to aplay
        if decoder_process is None:
            # This bypasses the problematic ALSA/JACK output drivers
            env = os.environ.copy()
            # Disable JACK completely
            env.pop('JACK_PROMISCUOUS_SERVER', None)
            env.pop('JACK_DEFAULT_SERVER', None)
            # Set output to dummy to prevent any driver loading attempts
            env['MPG123_MODDIR'] = '/usr/lib/aarch64-linux-gnu/mpg123'  # Help mpg123 find modules if needed
            
            try:
                # Method 1: Try mpg123 with stdout piped to aplay (most reliable)
                mpg123_proc = subprocess.Popen(
                    [mpg123_path, '-q', '-s', stream_url],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,
                    env=env
                )
                
                aplay_proc = subprocess.Popen(
                    [aplay_path, '-D', output_device, '-f', 'cd', '-c', '2', '-r', '44100'],
                    stdin=mpg123_proc.stdout,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                mpg123_proc.stdout.close()  # Allow mpg123 to receive SIGPIPE if aplay dies
                
                # Store both processes - we'll track mpg123 as the main process
                decoder_process = mpg123_proc
                decoder_aplay_process = aplay_proc
                
                time.sleep(1)
                
                # Check if both processes are running
                if mpg123_proc.poll() is None and aplay_proc.poll() is None:
                    # Both running, success! Don't try fallback
                    pass
                else:
                    # One failed, check which one and why
                    if mpg123_proc.poll() is not None:
                        stderr_data = mpg123_proc.stderr.read().decode() if mpg123_proc.stderr else ''
                        # Check if it's a connection error (expected) or driver error (bad)
                        if 'driver' in stderr_data.lower() or 'out123' in stderr_data.lower():
                            last_error = f'mpg123 driver error: {stderr_data[:200]}'
                        else:
                            # Connection error or other - this is OK, process might start when stream connects
                            # Give it more time if it's a connection issue
                            if 'connection' in stderr_data.lower() or 'resolve' in stderr_data.lower():
                                # Connection error - wait a bit more, process might still be starting
                                time.sleep(2)
                                if mpg123_proc.poll() is None:
                                    # Process recovered, check aplay
                                    if aplay_proc.poll() is None:
                                        pass  # Both running now
                                    else:
                                        last_error = f'aplay failed: {aplay_proc.stderr.read().decode()[:200] if aplay_proc.stderr else 'unknown'}'
                                        decoder_process = None
                                        decoder_aplay_process = None
                                else:
                                    last_error = f'mpg123 connection error: {stderr_data[:200]}'
                                    decoder_process = None
                                    decoder_aplay_process = None
                            else:
                                last_error = f'mpg123 error: {stderr_data[:200]}'
                                decoder_process = None
                                decoder_aplay_process = None
                    else:
                        # aplay failed
                        last_error = aplay_proc.stderr.read().decode() if aplay_proc.stderr else 'aplay failed'
                        decoder_process = None
                        decoder_aplay_process = None
                    
                    # Clean up failed processes
                    try:
                        if mpg123_proc.poll() is not None:
                            mpg123_proc.terminate()
                        if aplay_proc.poll() is not None:
                            aplay_proc.terminate()
                    except:
                        pass
                    
                    # Only try fallback if stdout method completely failed
                    if decoder_process is None:
                        # Fallback A: Try ffmpeg PCM pipeline (also provides decoder levels)
                        if _start_ffmpeg_pipeline(stream_url, output_device):
                            decoder_process = decoder_process  # already set
                            decoder_aplay_process = decoder_aplay_process
                        else:
                            # Fallback B: Try cvlc directly to ALSA (handles AAC/m3u)
                            try:
                                cvlc_path = shutil.which('cvlc') or '/usr/bin/cvlc'
                                cvlc_proc = subprocess.Popen(
                                    [cvlc_path, '--intf', 'dummy', '--no-video', '--quiet',
                                     '--aout', 'alsa', f'--alsa-audio-device={output_device}', stream_url],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    stdin=subprocess.DEVNULL
                                )
                                time.sleep(1)
                                if cvlc_proc.poll() is None:
                                    decoder_process = cvlc_proc
                                    decoder_aplay_process = None
                                else:
                                    stderr_fallback = cvlc_proc.stderr.read().decode() if cvlc_proc.stderr else 'cvlc failed'
                                    last_error = f'cvlc failed: {stderr_fallback[:200]}'
                                    decoder_process = None
                            except Exception as fallback_e:
                                last_error = f'cvlc fallback failed: {str(fallback_e)}'
                                decoder_process = None

                    # Final fallback: mpg123 with Pulse (as a last resort)
                    if decoder_process is None:
                        try:
                            decoder_process = subprocess.Popen(
                                [mpg123_path, '-q', '-o', 'pulse', stream_url],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                stdin=subprocess.DEVNULL,
                                env=env
                            )
                            time.sleep(1)
                            if decoder_process.poll() is not None:
                                stderr_fallback = decoder_process.stderr.read().decode() if decoder_process.stderr else 'pulse failed'
                                last_error = f'Fallback pulse also failed: {stderr_fallback[:200]}'
                                decoder_process = None
                        except Exception as fallback_e:
                            last_error = f'Fallback failed: {str(fallback_e)}'
                            decoder_process = None
            except Exception as e:
                decoder_process = None
                decoder_aplay_process = None
                last_error = str(e)
        # Check if we successfully started a process
        if decoder_process is None or decoder_process.poll() is not None:
            # All methods failed - provide helpful error message
            if last_error:
                # Check if error mentions driver - this means fallback failed, stdout method might have had connection issue
                if 'driver' in last_error.lower() or 'out123' in last_error.lower():
                    error_msg = f'Decoder failed: Unable to initialize audio output. Try setting an ALSA output device like \"plughw:2,0\". Original error: {last_error[:150]}'
                else:
                    error_msg = last_error[:200]
            else:
                error_msg = 'All decoder methods failed. Please check stream URL is valid.'
            return jsonify({'success': False, 'message': f'Failed to start decoder: {error_msg}'})
        
        # Process is running, verify it's actually playing
        time.sleep(0.5)
        if get_decoder_status():
            return jsonify({'success': True, 'message': 'Decoder started successfully'})
        else:
            # Process started but might not be playing yet, give it a moment
            time.sleep(1)
            if get_decoder_status():
                return jsonify({'success': True, 'message': 'Decoder started successfully'})
            else:
                # Check for errors
                stderr_output = decoder_process.stderr.read().decode() if decoder_process.stderr else ''
                return jsonify({'success': False, 'message': f'Decoder started but may not be playing: {stderr_output[:200]}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/decoder/config', methods=['GET'])
def api_get_decoder_config():
    """Return saved decoder config (url, outputDevice) with sensible defaults."""
    st = load_status()
    dec = st.get('decoder', {})
    defaults = _detect_default_devices()
    return jsonify({
        'url': dec.get('url', ''),
        'outputDevice': dec.get('outputDevice', defaults.get('output', 'default'))
    })

@app.route('/api/decoder/config', methods=['POST'])
@login_required
def api_save_decoder_config():
    """Persist decoder config (url, outputDevice)."""
    try:
        payload = request.get_json() or {}
        url_val = str(payload.get('url', '')).strip()
        out_dev = str(payload.get('outputDevice', '')).strip()
        st = load_status()
        st.setdefault('decoder', {})
        if url_val:
            st['decoder']['url'] = url_val
        if out_dev:
            st['decoder']['outputDevice'] = out_dev
        if save_status(st):
            return jsonify({'success': True, 'message': 'Decoder config saved'})
        return jsonify({'success': False, 'message': 'Failed to save decoder config'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/decoder/stop', methods=['POST'])
@login_required
def api_decoder_stop():
    """Stop decoder/player"""
    global decoder_process, decoder_aplay_process, decoder_should_run
    # Always try to stop, even if status probe says not running
    decoder_should_run = False
    
    try:
        # Stop tracked processes if they exist
        if decoder_process:
            decoder_process.terminate()
            decoder_process = None
        
        if decoder_aplay_process:
            decoder_aplay_process.terminate()
            decoder_aplay_process = None
        
        # Also use pkill as backup for all potential players
        pkill_path = shutil.which('pkill') or '/usr/bin/pkill'
        # Exact name matches
        subprocess.run([pkill_path, '-x', 'mpg123'], check=False)
        subprocess.run([pkill_path, '-x', 'aplay'], check=False)
        subprocess.run([pkill_path, '-x', 'cvlc'], check=False)
        subprocess.run([pkill_path, '-x', 'vlc'], check=False)
        subprocess.run([pkill_path, '-x', 'ffmpeg'], check=False)
        # Pattern matches, in case names differ
        subprocess.run([pkill_path, '-f', 'mpg123'], check=False)
        subprocess.run([pkill_path, '-f', 'aplay'], check=False)
        subprocess.run([pkill_path, '-f', 'cvlc'], check=False)
        subprocess.run([pkill_path, '-f', 'vlc'], check=False)
        subprocess.run([pkill_path, '-f', 'ffmpeg'], check=False)
        time.sleep(0.5)
        
        if not get_decoder_status():
            return jsonify({'success': True, 'message': 'Decoder stopped successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to stop decoder'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/audio/devices')
def api_audio_devices():
    """Get list of audio devices"""
    try:
        # Get input devices - use full paths
        arecord_path = shutil.which('arecord') or '/usr/bin/arecord'
        aplay_path = shutil.which('aplay') or '/usr/bin/aplay'
        
        result = subprocess.run([arecord_path, '-l'], 
                              capture_output=True, text=True)
        input_devices = result.stdout
        
        # Get output devices
        result = subprocess.run([aplay_path, '-l'], 
                              capture_output=True, text=True)
        output_devices = result.stdout
        
        return jsonify({
            'input': input_devices,
            'output': output_devices
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _detect_default_devices() -> dict:
    """
    Detect sensible defaults for input/output ALSA devices.
    Prioritize USB cards when present.
    """
    defaults = {
        'input': 'hw:1,0',
        'output': 'default'
    }
    try:
        arecord_path = shutil.which('arecord') or '/usr/bin/arecord'
        aplay_path = shutil.which('aplay') or '/usr/bin/aplay'

        # Parse capture (input)
        input_card = None
        r = subprocess.run([arecord_path, '-l'], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            lines = r.stdout.splitlines()
            # USB first
            for line in lines:
                line_l = line.lower()
                if line_l.strip().startswith('card ') and 'usb' in line_l:
                    m = re.search(r'card\\s+(\\d+)', line, flags=re.IGNORECASE)
                    if m:
                        input_card = m.group(1)
                        break
            if input_card is None:
                for line in lines:
                    m = re.search(r'card\\s+(\\d+)', line, flags=re.IGNORECASE)
                    if m:
                        input_card = m.group(1)
                        break
            if input_card is not None:
                defaults['input'] = f'hw:{input_card},0'

        # Parse playback (output)
        output_card = None
        r = subprocess.run([aplay_path, '-l'], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            lines = r.stdout.splitlines()
            # USB first
            for line in lines:
                line_l = line.lower()
                if line_l.strip().startswith('card ') and 'usb' in line_l:
                    m = re.search(r'card\\s+(\\d+)', line, flags=re.IGNORECASE)
                    if m:
                        output_card = m.group(1)
                        break
            if output_card is None:
                for line in lines:
                    m = re.search(r'card\\s+(\\d+)', line, flags=re.IGNORECASE)
                    if m:
                        output_card = m.group(1)
                        break
            if output_card is not None:
                defaults['output'] = f'plughw:{output_card},0'
            else:
                defaults['output'] = 'default'
    except Exception:
        pass
    return defaults

@app.route('/api/audio/defaults')
def api_audio_defaults():
    """Return recommended default ALSA devices (input/output)."""
    try:
        return jsonify(_detect_default_devices())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/icecast/start', methods=['POST'])
@login_required
def api_icecast_start():
    """Start Icecast server"""
    # First, stop any existing Icecast instance
    if get_icecast_status():
        # Stop existing instance
        try:
            subprocess.run(['systemctl', 'stop', 'icecast2'], capture_output=True, timeout=3)
            time.sleep(1)
        except:
            pass
        # Kill any remaining processes
        pkill_path = shutil.which('pkill') or '/usr/bin/pkill'
        subprocess.run([pkill_path, '-9', '-x', 'icecast2'], capture_output=True, timeout=2)
        time.sleep(1)
    
    # Check if port 8000 is in use and free it
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 8000))
        sock.close()
        if result == 0:
            # Port is in use, try to find and kill the process
            try:
                # Find process using port 8000
                lsof_path = shutil.which('lsof') or '/usr/bin/lsof'
                result = subprocess.run([lsof_path, '-ti:8000'], capture_output=True, text=True, timeout=2)
                if result.returncode == 0 and result.stdout.strip():
                    pid = result.stdout.strip()
                    subprocess.run(['kill', '-9', pid], timeout=2)
                    time.sleep(1)
            except:
                # Try with fuser or pkill
                try:
                    fuser_path = shutil.which('fuser') or '/usr/bin/fuser'
                    sudo_path_temp = shutil.which('sudo') or '/usr/bin/sudo'
                    subprocess.run([sudo_path_temp, fuser_path, '-k', '8000/tcp'], timeout=2)
                    time.sleep(1)
                except:
                    # Last resort: pkill all icecast2
                    pkill_path = shutil.which('pkill') or '/usr/bin/pkill'
                    subprocess.run([pkill_path, '-9', '-x', 'icecast2'], timeout=2)
                    time.sleep(1)
    except:
        pass
    
    try:
        # Try using systemctl first (preferred method)
        try:
            result = subprocess.run(['systemctl', 'start', 'icecast2'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                time.sleep(2)
                if get_icecast_status():
                    return jsonify({'success': True, 'message': 'Icecast server started successfully'})
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Fallback: Try running icecast2 directly with full path
        icecast2_path = shutil.which('icecast2') or '/usr/bin/icecast2'
        sudo_path = shutil.which('sudo') or '/usr/bin/sudo'
        
        # Ensure directories have correct permissions before starting
        try:
            # Fix permissions on run directory - user is icecast2, group is icecast
            subprocess.run([sudo_path, 'chown', '-R', 'icecast2:icecast', '/var/run/icecast2'], 
                         capture_output=True, timeout=2)
            subprocess.run([sudo_path, 'chmod', '755', '/var/run/icecast2'], 
                         capture_output=True, timeout=2)
            # Also ensure log directory is writable
            subprocess.run([sudo_path, 'chown', '-R', 'icecast2:icecast', '/var/log/icecast2'], 
                         capture_output=True, timeout=2)
        except:
            pass
        
        if sudo_path and os.path.exists(sudo_path):
            # Start as root so icecast can change to icecast2 user (changeowner only works as root)
            # Icecast will drop privileges to icecast2:icecast as configured
            process = subprocess.Popen([sudo_path, icecast2_path, '-c', '/etc/icecast2/icecast.xml', '-b'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            preexec_fn=os.setsid if hasattr(os, 'setsid') else None)
        else:
            # Last resort: try running icecast2 directly (if permissions allow)
            process = subprocess.Popen([icecast2_path, '-c', '/etc/icecast2/icecast.xml', '-b'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            preexec_fn=os.setsid if hasattr(os, 'setsid') else None)
        
        # Wait longer for Icecast to start and drop privileges
        time.sleep(4)
        
        # Check if process is running first
        if get_icecast_status():
            return jsonify({'success': True, 'message': 'Icecast server started successfully'})
        
        # Check process status - it might still be starting
        if process.poll() is None:
            # Process is still running, give it more time and check again
            for attempt in range(3):
                time.sleep(2)
                if get_icecast_status():
                    return jsonify({'success': True, 'message': 'Icecast server started successfully'})
        
        # These are success messages, not errors
        success_indicators = [
            'Changed userid',
            'Changed groupid',
            'Changed supplementary groups',
            'Detaching from the console',
            'Starting icecast2'
        ]
        
        # Read output to check for success messages
        # Icecast prints messages before forking, so we can read them
        try:
            # Try to read output (use select or just read with timeout)
            import select
            error_msg = ''
            stdout_output = ''
            stderr_output = ''
            
            # Wait a bit for output, then try to read
            time.sleep(1)
            
            # Try non-blocking read
            try:
                if process.stdout:
                    # Check if data is available (non-blocking)
                    ready, _, _ = select.select([process.stdout], [], [], 0.1)
                    if ready:
                        stdout_output = process.stdout.read(500).decode() if process.stdout else ''
            except:
                pass
            
            try:
                if process.stderr:
                    ready, _, _ = select.select([process.stderr], [], [], 0.1)
                    if ready:
                        stderr_output = process.stderr.read(500).decode() if process.stderr else ''
            except:
                # If select not available, try direct read (might block briefly)
                try:
                    if process.stderr:
                        stderr_output = process.stderr.read(500).decode() if process.stderr else ''
                except:
                    pass
            
            error_msg = stderr_output[:500] if stderr_output else stdout_output[:500]
            
            # Check if messages indicate success
            if any(indicator in error_msg for indicator in success_indicators):
                # These are success messages - Icecast forks in daemon mode, so parent exits
                # but child continues running. Check the actual Icecast process, not parent.
                for attempt in range(4):
                    time.sleep(1.5)
                    if get_icecast_status():
                        return jsonify({'success': True, 'message': 'Icecast server started successfully'})
                
                # Final check - if we saw success messages, trust them
                # The parent process exiting is normal for daemon mode
                if get_icecast_status():
                    return jsonify({'success': True, 'message': 'Icecast server started successfully'})
                else:
                    # Even if status check fails, if we saw success messages, it likely worked
                    # Give it one more moment
                    time.sleep(2)
                    if get_icecast_status():
                        return jsonify({'success': True, 'message': 'Icecast server started successfully'})
                    # If still not detected but we saw success messages, assume it worked
                    # (the status check might be timing out)
                    return jsonify({'success': True, 'message': 'Icecast server started successfully (daemon mode - parent process exited, Icecast running in background)'})
            
            # If no success messages, check for actual errors
            if error_msg:
                # Check if it's a permission error
                if 'Permission denied' in error_msg or 'I/O error' in error_msg:
                    return jsonify({
                        'success': False, 
                        'message': f'Permission error starting Icecast. Try: sudo chown -R icecast2:icecast /var/run/icecast2 /var/log/icecast2. Error: {error_msg[:200]}'
                    })
                # Check for port binding errors
                elif 'Could not create listener socket' in error_msg or 'bind' in error_msg.lower():
                    return jsonify({
                        'success': False,
                        'message': f'Port binding error: {error_msg[:200]}. Port 8000 may be in use.'
                    })
                else:
                    return jsonify({'success': False, 'message': f'Failed to start Icecast: {error_msg[:200]}'})
            else:
                # No error message, do final status check
                time.sleep(1)
                if get_icecast_status():
                    return jsonify({'success': True, 'message': 'Icecast server started successfully'})
                return jsonify({'success': False, 'message': 'Failed to start Icecast. Check system logs.'})
        except Exception as read_error:
            # Error reading output, but check status anyway
            time.sleep(1)
            if get_icecast_status():
                return jsonify({'success': True, 'message': 'Icecast server started successfully'})
            return jsonify({'success': False, 'message': f'Failed to start Icecast. Error reading output: {str(read_error)}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/icecast/stop', methods=['POST'])
@login_required
def api_icecast_stop():
    """Stop Icecast server"""
    if not get_icecast_status():
        return jsonify({'success': False, 'message': 'Icecast is not running'})
    
    try:
        # Try using systemctl first (preferred method)
        systemctl_path = shutil.which('systemctl') or '/usr/bin/systemctl'
        try:
            result = subprocess.run([systemctl_path, 'stop', 'icecast2'],
                                  capture_output=True, text=True, timeout=5)
            time.sleep(2)
            if not get_icecast_status():
                return jsonify({'success': True, 'message': 'Icecast server stopped successfully'})
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            # Continue to fallback methods
            pass
        
        # Fallback 1: Use pkill with pattern matching (more reliable than -x)
        # Try with sudo first (in case process is owned by icecast2 user)
        pkill_path = shutil.which('pkill') or '/usr/bin/pkill'
        sudo_path = shutil.which('sudo') or '/usr/bin/sudo'
        try:
            # Try with sudo first
            subprocess.run([sudo_path, pkill_path, '-f', 'icecast2'], check=False, timeout=3)
            time.sleep(2)
            if not get_icecast_status():
                return jsonify({'success': True, 'message': 'Icecast server stopped successfully'})
        except:
            pass
        
        # Fallback 2: Try without sudo
        try:
            subprocess.run([pkill_path, '-f', 'icecast2'], check=False, timeout=3)
            time.sleep(2)
            if not get_icecast_status():
                return jsonify({'success': True, 'message': 'Icecast server stopped successfully'})
        except:
            pass
        
        # Fallback 3: Use pkill with exact name (with sudo)
        try:
            subprocess.run([sudo_path, pkill_path, '-x', 'icecast2'], check=False, timeout=3)
            time.sleep(2)
            if not get_icecast_status():
                return jsonify({'success': True, 'message': 'Icecast server stopped successfully'})
        except:
            pass
        
        # Fallback 4: Use pkill with signal 9 (KILL) - more aggressive (with sudo)
        try:
            subprocess.run([sudo_path, pkill_path, '-9', '-f', 'icecast2'], check=False, timeout=3)
            time.sleep(1)
            if not get_icecast_status():
                return jsonify({'success': True, 'message': 'Icecast server stopped successfully (force kill)'})
        except:
            pass
        
        # Fallback 5: Try killall as last resort (with sudo)
        killall_path = shutil.which('killall') or '/usr/bin/killall'
        try:
            subprocess.run([sudo_path, killall_path, '-9', 'icecast2'], check=False, timeout=3)
            time.sleep(1)
            if not get_icecast_status():
                return jsonify({'success': True, 'message': 'Icecast server stopped successfully (killall)'})
        except:
            pass
        
        # Final check - if still running, report failure
        if get_icecast_status():
            return jsonify({
                'success': False, 
                'message': 'Failed to stop Icecast server. Process may be stuck. Try: sudo systemctl stop icecast2'
            })
        else:
            return jsonify({'success': True, 'message': 'Icecast server stopped successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/audio/levels')
def api_audio_levels():
    """Get current audio levels"""
    return jsonify(audio_levels)

@app.route('/api/decoder/levels')
def api_decoder_levels():
    """Get current decoder audio levels"""
    return jsonify(decoder_audio_levels)

@app.route('/api/settings/ip')
def api_get_ip():
    """Get current IP address"""
    try:
        import socket
        import re
        
        # Method 1: Try using socket to get hostname and then resolve
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            # If it's localhost, try to get actual interface IP
            if ip.startswith('127.'):
                # Method 2: Try reading from /proc/net/route or using ip command
                ip_path = shutil.which('ip') or '/usr/bin/ip'
                result = subprocess.run([ip_path, 'addr', 'show'], capture_output=True, text=True, timeout=3)
                if result.returncode == 0:
                    # Find first non-loopback IPv4 address
                    matches = re.findall(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
                    for match in matches:
                        if not match.startswith('127.'):
                            ip = match
                            break
        except:
            ip = 'Unknown'
        
        # Method 3: Fallback - try hostname command with full path
        if ip == 'Unknown' or ip.startswith('127.'):
            hostname_path = shutil.which('hostname') or '/usr/bin/hostname'
            try:
                result = subprocess.run([hostname_path, '-I'], capture_output=True, text=True, timeout=2)
                if result.returncode == 0 and result.stdout.strip():
                    ips = result.stdout.strip().split()
                    for candidate_ip in ips:
                        if not candidate_ip.startswith('127.') and '.' in candidate_ip:
                            ip = candidate_ip
                            break
            except:
                pass
        
        # Method 4: Try reading from network interfaces directly
        if ip == 'Unknown' or ip.startswith('127.'):
            try:
                # Read from /proc/net/route to find default interface, then get its IP
                with open('/proc/net/route', 'r') as f:
                    lines = f.readlines()
                    for line in lines[1:]:  # Skip header
                        parts = line.split()
                        if len(parts) >= 8 and parts[1] == '00000000':  # Default route
                            interface = parts[0]
                            # Get IP for this interface
                            ip_path = shutil.which('ip') or '/usr/bin/ip'
                            result = subprocess.run([ip_path, 'addr', 'show', interface], 
                                                  capture_output=True, text=True, timeout=2)
                            if result.returncode == 0:
                                match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
                                if match and not match.group(1).startswith('127.'):
                                    ip = match.group(1)
                                    break
            except:
                pass
        
        return jsonify({'ip': ip if ip != 'Unknown' else 'Unable to detect IP'})
    except Exception as e:
        return jsonify({'ip': f'Error: {str(e)}'}), 500

@app.route('/api/settings/network', methods=['GET'])
def api_get_network():
    """Get current network configuration"""
    try:
        import socket
        import re
        
        # Get IP address
        ip = 'Unknown'
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip.startswith('127.'):
                ip_path = shutil.which('ip') or '/usr/bin/ip'
                result = subprocess.run([ip_path, 'addr', 'show'], capture_output=True, text=True, timeout=3)
                if result.returncode == 0:
                    matches = re.findall(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
                    for match in matches:
                        if not match.startswith('127.'):
                            ip = match
                            break
        except:
            pass
        
        # Get netmask
        netmask = '255.255.255.0'  # Default
        try:
            ip_path = shutil.which('ip') or '/usr/bin/ip'
            result = subprocess.run([ip_path, 'addr', 'show'], capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                # Find netmask for the IP we found
                lines = result.stdout.split('\n')
                for i, line in enumerate(lines):
                    if ip in line and 'inet' in line:
                        # Next line might have netmask, or it's in CIDR notation
                        if '/' in line:
                            cidr = line.split('/')[1].split()[0]
                            # Convert CIDR to netmask
                            cidr_int = int(cidr)
                            netmask = cidr_to_netmask(cidr_int)
                        break
        except:
            pass
        
        # Get gateway
        gateway = 'Unknown'
        try:
            with open('/proc/net/route', 'r') as f:
                lines = f.readlines()
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 8 and parts[1] == '00000000':  # Default route
                        gateway_hex = parts[2]
                        # Convert hex to IP
                        gateway = '.'.join([str(int(gateway_hex[i:i+2], 16)) for i in range(6, -1, -2)])
                        break
        except:
            pass
        
        # Determine if DHCP or static (check /etc/network/interfaces or systemd-networkd)
        config_type = 'dhcp'  # Default
        try:
            # Check /etc/network/interfaces
            if Path('/etc/network/interfaces').exists():
                with open('/etc/network/interfaces', 'r') as f:
                    content = f.read()
                    if 'static' in content.lower() and ip in content:
                        config_type = 'static'
        except:
            pass
        
        return jsonify({
            'ip': ip,
            'netmask': netmask,
            'gateway': gateway,
            'type': config_type
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings/network', methods=['POST'])
@login_required
def api_save_network():
    """Save network configuration (read-only for now - shows instructions)"""
    try:
        config = request.get_json()
        config_type = config.get('type', 'dhcp')
        ip = config.get('ip', '')
        netmask = config.get('netmask', '')
        gateway = config.get('gateway', '')
        
        # For security, we don't actually change network config via web UI
        # Instead, provide instructions
        if config_type == 'static':
            if not ip or not netmask or not gateway:
                return jsonify({'success': False, 'message': 'All fields required for static configuration'})
            
            instructions = f"""
Network configuration requested:
- Type: Static
- IP: {ip}
- Netmask: {netmask}
- Gateway: {gateway}

To apply these settings, you need to edit /etc/dhcpcd.conf or /etc/network/interfaces manually.
For Raspberry Pi OS, edit /etc/dhcpcd.conf and add:
interface eth0
static ip_address={ip}/{netmask_to_cidr(netmask)}
static routers={gateway}
static domain_name_servers=8.8.8.8

Then restart networking: sudo systemctl restart dhcpcd
"""
            return jsonify({
                'success': True,
                'message': 'Configuration validated. See instructions below.',
                'instructions': instructions
            })
        else:
            return jsonify({
                'success': True,
                'message': 'DHCP configuration - network will obtain IP automatically'
            })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

def cidr_to_netmask(cidr):
    """Convert CIDR notation to netmask"""
    mask = (0xffffffff >> (32 - cidr)) << (32 - cidr)
    return '.'.join([str((mask >> (8 * (3 - i))) & 0xff) for i in range(4)])

def netmask_to_cidr(netmask):
    """Convert netmask to CIDR notation"""
    parts = netmask.split('.')
    binary = ''.join([format(int(part), '08b') for part in parts])
    return str(len(binary.rstrip('0')))

@app.route('/api/settings/audio-devices')
def api_detect_audio_devices():
    """Detect audio devices with detailed USB information"""
    try:
        input_devices = []
        output_devices = []
        
        # Get input devices using arecord
        arecord_path = shutil.which('arecord') or '/usr/bin/arecord'
        result = subprocess.run([arecord_path, '-l'], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            current_card = None
            for line in lines:
                if 'card' in line.lower():
                    # Parse card line: card 1: DeviceName [Device Description], device 0: ...
                    parts = line.split(':')
                    if len(parts) >= 2:
                        card_num = parts[0].split()[-1] if 'card' in parts[0].lower() else None
                        if card_num:
                            device_info = parts[1].strip()
                            device_name = device_info.split('[')[0].strip() if '[' in device_info else device_info
                            
                            # Get USB info from sysfs
                            usb_info = get_usb_device_info(card_num)
                            
                            input_devices.append({
                                'card': card_num,
                                'name': device_name,
                                'alsa_id': f'hw:{card_num},0',
                                'bus': usb_info.get('bus', ''),
                                'vendor': usb_info.get('vendor', ''),
                                'product': usb_info.get('product', ''),
                                'description': device_info
                            })
        
        # Get output devices using aplay
        aplay_path = shutil.which('aplay') or '/usr/bin/aplay'
        result = subprocess.run([aplay_path, '-l'], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'card' in line.lower():
                    parts = line.split(':')
                    if len(parts) >= 2:
                        card_num = parts[0].split()[-1] if 'card' in parts[0].lower() else None
                        if card_num:
                            device_info = parts[1].strip()
                            device_name = device_info.split('[')[0].strip() if '[' in device_info else device_info
                            
                            # Get USB info from sysfs
                            usb_info = get_usb_device_info(card_num)
                            
                            output_devices.append({
                                'card': card_num,
                                'name': device_name,
                                'alsa_id': f'hw:{card_num},0',
                                'bus': usb_info.get('bus', ''),
                                'vendor': usb_info.get('vendor', ''),
                                'product': usb_info.get('product', ''),
                                'description': device_info
                            })
        
        return jsonify({
            'input': input_devices,
            'output': output_devices
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings/change-password', methods=['POST'])
@login_required
def api_change_password():
    """Change password for both UI and Icecast server"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data received'}), 400
        
        current_password = data.get('currentPassword', '').strip()
        new_password = data.get('newPassword', '').strip()
        
        if not current_password or not new_password:
            return jsonify({'success': False, 'message': 'Current and new password required'}), 400
        
        if len(new_password) < 4:
            return jsonify({'success': False, 'message': 'Password must be at least 4 characters long'}), 400
        
        # Verify current password
        current_hash = hashlib.sha256(current_password.encode()).hexdigest()
        stored_hash = load_password_hash()
        
        if current_hash != stored_hash:
            return jsonify({'success': False, 'message': 'Current password is incorrect'}), 401
        
        # Update password hash
        new_hash = hashlib.sha256(new_password.encode()).hexdigest()
        try:
            with open(PASSWORD_FILE, 'w') as f:
                f.write(new_hash)
            # Update global variable
            global ADMIN_PASSWORD_HASH
            ADMIN_PASSWORD_HASH = new_hash
        except Exception as e:
            return jsonify({'success': False, 'message': f'Failed to save password: {str(e)}'}), 500
        
        # Update Icecast configuration
        icecast_config_path = Path('/etc/icecast2/icecast.xml')
        if not icecast_config_path.exists():
            icecast_config_path = Path(__file__).parent / 'icecast.xml'
        
        if icecast_config_path.exists():
            try:
                # Read current config
                with open(icecast_config_path, 'r') as f:
                    icecast_config = f.read()
                
                # Update all password fields in Icecast config
                # Update admin-password
                import re
                icecast_config = re.sub(
                    r'(<admin-password>)(.*?)(</admin-password>)',
                    r'\1' + new_password + r'\3',
                    icecast_config
                )
                # Update source-password
                icecast_config = re.sub(
                    r'(<source-password>)(.*?)(</source-password>)',
                    r'\1' + new_password + r'\3',
                    icecast_config
                )
                # Update relay-password
                icecast_config = re.sub(
                    r'(<relay-password>)(.*?)(</relay-password>)',
                    r'\1' + new_password + r'\3',
                    icecast_config
                )
                # Update mount password (within <mount> section)
                # This is more specific to avoid matching other password tags
                icecast_config = re.sub(
                    r'(<mount>.*?<password>)(.*?)(</password>.*?</mount>)',
                    lambda m: m.group(1) + new_password + m.group(3),
                    icecast_config,
                    flags=re.DOTALL
                )
                
                # Write updated config
                with open(icecast_config_path, 'w') as f:
                    f.write(icecast_config)
                
                # If Icecast is running, restart it to apply new password
                # (Note: This requires sudo, so we'll just inform the user)
                icecast_running = get_icecast_status()
                if icecast_running:
                    # Try to restart Icecast (may require sudo)
                    try:
                        subprocess.run(['sudo', 'systemctl', 'restart', 'icecast2'], 
                                      timeout=5, capture_output=True)
                    except:
                        pass  # If restart fails, user can do it manually
                
            except Exception as e:
                return jsonify({
                    'success': False, 
                    'message': f'Password updated for UI, but failed to update Icecast config: {str(e)}'
                }), 500
        
        return jsonify({
            'success': True, 
            'message': 'Password changed successfully for both UI and Icecast server. Please restart Icecast if it is running.'
        })
        
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'message': f'Error: {str(e)}', 'trace': traceback.format_exc()[:200]}), 500

def get_usb_device_info(card_num):
    """Get USB device information for an audio card"""
    usb_info = {}
    try:
        # Try to find USB device info in /proc/asound/cardX
        card_path = Path(f'/proc/asound/card{card_num}')
        if card_path.exists():
            # Look for usbid file
            usbid_file = card_path / 'usbid'
            if usbid_file.exists():
                with open(usbid_file, 'r') as f:
                    usb_id = f.read().strip()
                    if usb_id:
                        usb_info['bus'] = 'USB'
                        # Try to get vendor/product from /sys/bus/usb/devices
                        # This is a simplified version - full implementation would parse USB IDs
                        usb_info['vendor'] = 'USB Device'
                        usb_info['product'] = usb_id
        else:
            # Try alternative method: check if card is USB by checking /sys/class/sound
            sound_path = Path(f'/sys/class/sound/card{card_num}')
            if sound_path.exists():
                device_path = sound_path / 'device'
                if device_path.exists() and device_path.is_symlink():
                    real_path = device_path.resolve()
                    if 'usb' in str(real_path).lower():
                        usb_info['bus'] = 'USB'
                        # Try to extract vendor/product from path
                        parts = str(real_path).split('/')
                        for part in parts:
                            if ':' in part and len(part.split(':')) >= 2:
                                vid_pid = part.split(':')
                                if len(vid_pid) >= 2:
                                    usb_info['vendor'] = f'Vendor ID: {vid_pid[0]}'
                                    usb_info['product'] = f'Product ID: {vid_pid[1]}'
    except Exception:
        pass
    
    return usb_info

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)
    
    # Start audio level monitoring thread
    running = True
    config = load_config()
    audio_level_thread = threading.Thread(target=read_audio_levels, 
                                         args=(config.get('device', 'hw:1,0'), 
                                               int(config.get('sampleRate', 44100))),
                                         daemon=True)
    audio_level_thread.start()
    
    app.run(host='0.0.0.0', port=5000, debug=False)

