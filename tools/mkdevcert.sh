#!/usr/bin/env bash
set -euo pipefail

DIR="certs"
mkdir -p "$DIR"

CN=${CN:-localhost}
DAYS=${DAYS:-3650}

CRT="$DIR/server.crt"
KEY="$DIR/server.key"
CONF="$DIR/openssl.cnf"

cat > "$CONF" <<'EOF'
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = localhost

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
IP.1 = 127.0.0.1
EOF

openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout "$KEY" -out "$CRT" \
  -subj "/CN=$CN" -days "$DAYS" \
  -extensions v3_req -config "$CONF"

echo "Created $CRT and $KEY with SANs (DNS:localhost, IP:127.0.0.1)"

