#!/usr/bin/env python3
"""
Generate VAPID keys for Web Push notifications

VAPID (Voluntary Application Server Identification) keys are used to identify
your server when sending push notifications via Web Push Protocol.

Usage:
    python scripts/generate_vapid_keys.py

Or in Docker:
    docker compose exec backend python scripts/generate_vapid_keys.py

Alternative methods:
    1. Node.js: npx web-push generate-vapid-keys
    2. OpenSSL: bash scripts/generate_vapid_keys_openssl.sh
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from vapid import Vapid01
    import base64
    
    # Generate new VAPID keys
    vapid = Vapid01()
    private_key = vapid.private_key
    public_key = vapid.public_key
    
    # Convert to base64 URL-safe format (as required by Web Push)
    private_key_b64 = base64.urlsafe_b64encode(private_key.private_bytes(
        encoding=base64.Encoding.DER,
        format=base64.PrivateFormat.PKCS8,
        encryption_algorithm=base64.NoEncryption()
    )).decode('utf-8').rstrip('=')
    
    public_key_b64 = base64.urlsafe_b64encode(public_key.public_bytes(
        encoding=base64.Encoding.DER,
        format=base64.PublicFormat.SubjectPublicKeyInfo
    )).decode('utf-8').rstrip('=')
    
    print("=" * 70)
    print("✅ VAPID Keys Generated Successfully!")
    print("=" * 70)
    print("\n📋 Add these to your backend/.env file:")
    print("-" * 70)
    print(f"VAPID_PUBLIC_KEY={public_key_b64}")
    print(f"VAPID_PRIVATE_KEY={private_key_b64}")
    print("-" * 70)
    print("\n⚠️  SECURITY WARNING:")
    print("   • Keep the PRIVATE key SECRET!")
    print("   • Never commit it to version control (git)")
    print("   • Only the PUBLIC key is safe to share")
    print("\n💡 The public key is sent to browsers for subscription.")
    print("   The private key is used by your server to sign push messages.")
    print("=" * 70)
    
except ImportError:
    print("❌ ERROR: py-vapid is not installed.")
    print("\n💡 RECOMMENDED: Use alternative methods (no installation needed):")
    print("\n   Option 1 - Node.js (easiest):")
    print("     cd hostflow-frontend")
    print("     npx web-push generate-vapid-keys")
    print("\n   Option 2 - OpenSSL (works everywhere):")
    print("     bash scripts/generate_vapid_keys_openssl.sh")
    print("\n   Option 3 - Online generator:")
    print("     https://vapidkeys.com/")
    print("\n📦 Or install py-vapid (if you prefer):")
    print("   docker compose exec backend pip install py-vapid")
    sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: {e}")
    print("\n💡 Alternative: Use openssl to generate keys manually")
    print("   See: https://web-push-codelab.glitch.me/")
    sys.exit(1)

