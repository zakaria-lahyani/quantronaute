#!/usr/bin/env python3
"""
Setup API for testing - Generate credentials and update .env.api file.

This script:
1. Generates a secure JWT secret key
2. Generates a test user with password hash
3. Updates .env.api with the credentials
4. Provides next steps for testing
"""

import secrets
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import bcrypt


def generate_secret_key() -> str:
    """Generate a secure random secret key."""
    return secrets.token_hex(32)


def generate_password_hash(password: str) -> str:
    """Generate bcrypt hash for password."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def update_env_file(secret_key: str, username: str, password_hash: str):
    """Update .env.api file with credentials."""
    env_file = project_root / '.env.api'

    if not env_file.exists():
        print(f"[-] Error: {env_file} not found")
        return False

    # Read current content
    with open(env_file, 'r') as f:
        lines = f.readlines()

    # Update lines
    updated_lines = []
    for line in lines:
        if line.startswith('API_SECRET_KEY='):
            updated_lines.append(f'API_SECRET_KEY={secret_key}\n')
        elif line.startswith('API_USER_ADMIN='):
            updated_lines.append(f'API_USER_ADMIN={password_hash}\n')
        else:
            updated_lines.append(line)

    # Write back
    with open(env_file, 'w') as f:
        f.writelines(updated_lines)

    print(f"[+] Updated {env_file}")
    return True


def main():
    """Main setup function."""
    print("=" * 70)
    print("API Testing Setup")
    print("=" * 70)
    print()

    # Configuration
    username = "admin"
    password = "admin123"  # Default test password

    print("Test Credentials:")
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    print()

    print("[*] Generating JWT secret key...")
    secret_key = generate_secret_key()
    print(f"[+] Generated secret key: {secret_key[:16]}...{secret_key[-16:]}")
    print()

    print("[*] Generating password hash...")
    password_hash = generate_password_hash(password)
    print(f"[+] Generated hash: {password_hash[:30]}...")
    print()

    print("[*] Updating .env.api file...")
    if update_env_file(secret_key, username, password_hash):
        print()
        print("=" * 70)
        print("[+] Setup Complete!")
        print("=" * 70)
        print()
        print("Next Steps:")
        print()
        print("1. Build and start the Docker container:")
        print("   docker-compose -f docker-compose.api.yml build")
        print("   docker-compose -f docker-compose.api.yml --env-file .env.api up -d")
        print()
        print("2. Test the health endpoint:")
        print("   curl http://localhost:8080/health")
        print()
        print("3. Login to get a token:")
        print("   curl -X POST http://localhost:8080/auth/login \\")
        print("     -H \"Content-Type: application/json\" \\")
        print("     -d '{\"username\": \"admin\", \"password\": \"admin123\"}'")
        print()
        print("4. Use the token to test endpoints:")
        print("   export TOKEN=\"your_access_token_here\"")
        print("   curl http://localhost:8080/positions -H \"Authorization: Bearer $TOKEN\"")
        print()
        print("[*] See docs/api-testing-guide.md for complete testing guide")
        print()
        print("=" * 70)
        print()
        print("CREDENTIALS SUMMARY:")
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        print(f"  Secret Key: {secret_key}")
        print(f"  Password Hash: {password_hash}")
        print()
        print("[!] WARNING: These are TEST credentials. Change them for production!")
        print("=" * 70)
    else:
        print("[-] Setup failed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
