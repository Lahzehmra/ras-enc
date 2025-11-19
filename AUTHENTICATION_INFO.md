# Authentication System

## Login Required for Configuration Changes

The web interface now requires login to make any configuration changes or control the encoder/decoder.

## Default Credentials

**Username:** `admin`  
**Password:** `admin123`

⚠️ **IMPORTANT:** Change these credentials in production!

## How to Change Password

Edit `/home/mra/Raspbery/app.py` and change:

```python
ADMIN_USERNAME = 'admin'  # Change username
ADMIN_PASSWORD_HASH = hashlib.sha256('admin123'.encode()).hexdigest()  # Change password
```

To generate a new password hash:
```python
import hashlib
hashlib.sha256('your_new_password'.encode()).hexdigest()
```

Then restart the service:
```bash
sudo systemctl restart shoutcast-web
```

## What Requires Login

- Saving configuration
- Starting/stopping encoder
- Starting/stopping decoder  
- Starting/stopping Icecast server

## What Doesn't Require Login

- Viewing status
- Viewing audio levels
- Viewing configuration (read-only)

## Layout Changes

- **Audio Meter**: Moved to left sidebar
- **Login Panel**: Left sidebar (when not logged in)
- **User Info**: Left sidebar (when logged in)
- **Main Controls**: Right side (requires login)

## Security Notes

1. Change default password immediately
2. Use strong passwords
3. Consider HTTPS for production
4. Session expires on browser close
5. Multiple login sessions supported


