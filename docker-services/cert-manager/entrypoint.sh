#!/bin/sh
set -e

apk add --no-cache openssl curl >/dev/null

ACME_HOME="/acme"
CERT_DIR="/certs"
SERVER_CERT="$CERT_DIR/private_ca_cert.crt"
SERVER_KEY="$CERT_DIR/private_ca_cert.key"

# ---------------------------------------------------------------------------
# Validate environment
# ---------------------------------------------------------------------------
if [ -z "$CERT_DOMAIN" ]; then
  echo "ERROR: CERT_DOMAIN environment variable is not set." >&2
  exit 1
fi

if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
  echo "ERROR: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set." >&2
  exit 1
fi

export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY

# ---------------------------------------------------------------------------
# Install acme.sh (first run only — persisted in volume)
# ---------------------------------------------------------------------------
if [ ! -f "$ACME_HOME/acme.sh" ]; then
  echo "Installing acme.sh..."
  curl -sL -o /tmp/acme.tar.gz https://github.com/acmesh-official/acme.sh/archive/master.tar.gz
  tar xzf /tmp/acme.tar.gz -C /tmp
  (cd /tmp/acme.sh-master && ./acme.sh --install --home "$ACME_HOME")
  rm -rf /tmp/acme.tar.gz /tmp/acme.sh-master
fi

# ---------------------------------------------------------------------------
# Issue certificate if not already issued for this domain
# ---------------------------------------------------------------------------
ACME_CERT_DIR="$ACME_HOME/${CERT_DOMAIN}_ecc"

if [ ! -f "$ACME_CERT_DIR/fullchain.cer" ]; then
  echo "Issuing certificate for $CERT_DOMAIN..."
  "$ACME_HOME/acme.sh" --issue \
    --dns dns_aws \
    -d "$CERT_DOMAIN" \
    --server letsencrypt \
    --keylength ec-256 \
    --home "$ACME_HOME"
fi

# ---------------------------------------------------------------------------
# Install certificate to shared volume
# ---------------------------------------------------------------------------
echo "Installing certificate to $CERT_DIR..."
"$ACME_HOME/acme.sh" --install-cert \
  -d "$CERT_DOMAIN" \
  --ecc \
  --fullchain-file "$SERVER_CERT" \
  --key-file "$SERVER_KEY" \
  --home "$ACME_HOME"

# Signal readiness
touch /tmp/certs-ready
echo "Cert-manager ready. Certificate issued for $CERT_DOMAIN."

# ---------------------------------------------------------------------------
# Renewal loop — check daily (acme.sh renews at 60 days)
# ---------------------------------------------------------------------------
while true; do
  sleep 86400
  echo "Running daily certificate renewal check..."
  "$ACME_HOME/acme.sh" --cron --home "$ACME_HOME" || true
done
