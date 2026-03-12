#!/bin/bash
# Generate VAPID keys using OpenSSL (works everywhere)

echo "=========================================="
echo "Generating VAPID keys with OpenSSL..."
echo "=========================================="

# Create temp directory
TMPDIR=$(mktemp -d)
cd "$TMPDIR"

# Generate private key
openssl ecparam -genkey -name prime256v1 -noout -out private_key.pem

# Extract public key in DER format, then convert to base64url
PUBLIC_KEY=$(openssl ec -in private_key.pem -pubout -outform DER 2>/dev/null | \
    tail -c 65 | \
    openssl base64 -e | \
    tr -d '\n' | \
    tr '+/' '-_' | \
    sed 's/=//g')

# Extract private key in PKCS8 format, then convert to base64url
PRIVATE_KEY=$(openssl ec -in private_key.pem -outform DER 2>/dev/null | \
    tail -c +8 | \
    head -c 32 | \
    openssl base64 -e | \
    tr -d '\n' | \
    tr '+/' '-_' | \
    sed 's/=//g')

# Cleanup
cd - > /dev/null
rm -rf "$TMPDIR"

echo ""
echo "✅ VAPID Keys Generated!"
echo "=========================================="
echo ""
echo "Add these to your backend/.env file:"
echo ""
echo "VAPID_PUBLIC_KEY=$PUBLIC_KEY"
echo "VAPID_PRIVATE_KEY=$PRIVATE_KEY"
echo ""
echo "=========================================="
echo "⚠️  IMPORTANT: Keep the private key SECRET!"
echo "   Never commit it to version control."
echo "=========================================="
