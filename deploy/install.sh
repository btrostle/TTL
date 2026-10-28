#!/bin/sh
# Install or update ttl-broker on the broker box. Run as root from the
# unpacked TTL source directory: sudo sh deploy/install.sh
set -eu

ranges="${LUDUS_ALLOWED_RANGES:-ThreatTrails-MVP}"

if ! command -v uv >/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh
fi

mkdir -p /opt/ttl-broker
cp -r pyproject.toml uv.lock .python-version src /opt/ttl-broker/
cd /opt/ttl-broker
# Keep the interpreter under /opt so the service's dynamic user can run it.
UV_PYTHON_INSTALL_DIR=/opt/ttl-broker/python uv sync --frozen --no-dev
# Pin the certificate Ludus presents now (Proxmox's, issued to "ludus").
if [ ! -f /opt/ttl-broker/ludus.pem ]; then
    echo | openssl s_client -connect 198.51.100.1:8080 2>/dev/null \
        | openssl x509 > /opt/ttl-broker/ludus.pem
fi
chmod -R a+rX /opt/ttl-broker

if [ ! -f /etc/ttl-broker/env ]; then
    mkdir -p /etc/ttl-broker
    umask 077
    cat > /etc/ttl-broker/env <<EOF
LUDUS_URL=https://198.51.100.1:8080
LUDUS_ALLOWED_RANGES=$ranges
LUDUS_CA_FILE=/opt/ttl-broker/ludus.pem
LUDUS_TLS_SERVER_NAME=ludus
BROKER_TOKEN=$(head -c 32 /dev/urandom | base64 | tr -d '/+=')
EOF
fi

cp "$OLDPWD/deploy/ttl-broker.service" /etc/systemd/system/ttl-broker.service
systemctl daemon-reload
systemctl enable ttl-broker
systemctl restart ttl-broker
