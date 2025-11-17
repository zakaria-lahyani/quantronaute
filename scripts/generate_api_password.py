#!/usr/bin/env python3
"""
Generate API password hash.

This script generates a bcrypt hash for API authentication passwords.
Usage:
    python scripts/generate_api_password.py

The script will prompt for a password and output the hash to add to api_credentials.json.
"""

import sys
import getpass
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import bcrypt


def main():
    """Generate password hash."""
    print("=== API Password Hash Generator ===\n")

    username = input("Enter username: ").strip()
    if not username:
        print("Error: Username cannot be empty")
        return

    password = getpass.getpass("Enter password: ")
    if not password:
        print("Error: Password cannot be empty")
        return

    password_confirm = getpass.getpass("Confirm password: ")
    if password != password_confirm:
        print("Error: Passwords do not match")
        return

    # Generate hash using bcrypt
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

    print("\n=== Generated Hash ===")
    print(f'Username: {username}')
    print(f'Hash: {hashed}')
    print("\n=== Add to configs/api_credentials.json ===")
    print(f'  "{username}": "{hashed}"')
    print()


if __name__ == "__main__":
    main()
