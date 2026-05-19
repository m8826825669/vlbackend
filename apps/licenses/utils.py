# utils.py
import secrets
import string


def generate_license_key():
    """Generate a formatted license key: XXXX-XXXX-XXXX-XXXX-XXXX"""
    chars = string.ascii_uppercase + string.digits
    segments = [''.join(secrets.choice(chars) for _ in range(5)) for _ in range(5)]
    return '-'.join(segments)
