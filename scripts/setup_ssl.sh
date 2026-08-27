#!/usr/bin/env bash
#
# scripts/setup_ssl.sh
# Issues (or renews) a wildcard Let's Encrypt certificate for
# *.azeonsystems.com.ng (+ the apex domain) via Certbot's DNS-01 challenge,
# installs scripts/nginx_master.conf as the live nginx site, and reloads
# nginx.
#
# DNS-01 is required here because a wildcard cert cannot use HTTP-01 —
# Let's Encrypt needs proof of control over the DNS zone (a TXT record),
# not a file served over HTTP, to issue a cert covering `*.domain`.
#
# Usage:
#   sudo DOMAIN=azeonsystems.com.ng EMAIL=you@azeonsystems.com.ng ./setup_ssl.sh
#
# Optional:
#   DNS_PLUGIN=manual (default) | dns-cloudflare | dns-route53 | ...
#     "manual" needs no provider credentials but pauses for you to create
#     a TXT record by hand — see the renewal caveat printed at the end.

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root (sudo ./setup_ssl.sh)" >&2
  exit 1
fi

DOMAIN="${DOMAIN:-azeonsystems.com.ng}"
EMAIL="${EMAIL:-}"
DNS_PLUGIN="${DNS_PLUGIN:-manual}"
NGINX_SITE_PATH="/etc/nginx/sites-available/azeon-systems.conf"
NGINX_ENABLED_PATH="/etc/nginx/sites-enabled/azeon-systems.conf"
REPO_TEMPLATE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/nginx_master.conf"

if [[ -z "${EMAIL}" ]]; then
  echo "Set EMAIL=<you@example.com> for Let's Encrypt registration/renewal notices." >&2
  exit 1
fi

if [[ ! -f "${REPO_TEMPLATE}" ]]; then
  echo "Cannot find nginx_master.conf next to this script at ${REPO_TEMPLATE}" >&2
  exit 1
fi

echo "== Installing certbot (if not already present) =="
if ! command -v certbot >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y certbot
fi

if [[ "${DNS_PLUGIN}" != "manual" ]]; then
  apt-get install -y "python3-certbot-${DNS_PLUGIN#dns-}" || {
    echo "Could not install python3-certbot-${DNS_PLUGIN#dns-} — check the plugin name." >&2
    exit 1
  }
fi

echo "== Requesting wildcard certificate for *.${DOMAIN} (and ${DOMAIN}) via DNS-01 =="
if [[ "${DNS_PLUGIN}" == "manual" ]]; then
  echo "MANUAL DNS-01 mode: certbot will pause and print a TXT record"
  echo "(_acme-challenge.${DOMAIN}) for you to create at your DNS provider"
  echo "before it continues — do that in another terminal/tab when prompted."
  certbot certonly \
    --manual \
    --preferred-challenges dns \
    --email "${EMAIL}" \
    --agree-tos \
    --no-eff-email \
    -d "${DOMAIN}" -d "*.${DOMAIN}"
else
  certbot certonly \
    --"${DNS_PLUGIN}" \
    --email "${EMAIL}" \
    --agree-tos \
    --no-eff-email \
    -d "${DOMAIN}" -d "*.${DOMAIN}"
fi

echo "== Installing the Azeon Systems nginx master template =="
cp "${REPO_TEMPLATE}" "${NGINX_SITE_PATH}"
# nginx_master.conf hardcodes the literal placeholder "azeonsystems.com" as
# the sed match target below — that string must stay exactly that in the
# template itself (do not "fix" it to azeonsystems.com.ng there), or this
# substitution breaks. DOMAIN's real value is substituted in here instead.
if [[ "${DOMAIN}" != "azeonsystems.com" ]]; then
  sed -i "s/azeonsystems\.com/${DOMAIN}/g" "${NGINX_SITE_PATH}"
fi

# bench's own `bench setup nginx` (run during scripts/vps_setup.sh) writes
# a plain HTTP-only site that would otherwise conflict with this one on
# the same server_name — disable it in favor of this wildcard-TLS version.
if [[ -f /etc/nginx/sites-enabled/frappe-bench.conf ]]; then
  rm -f /etc/nginx/sites-enabled/frappe-bench.conf
  echo "NOTE: disabled bench's auto-generated frappe-bench.conf to avoid a server_name conflict."
fi

ln -sf "${NGINX_SITE_PATH}" "${NGINX_ENABLED_PATH}"

nginx -t
systemctl reload nginx

echo "== Registering a certbot renewal hook to reload nginx =="
mkdir -p /etc/letsencrypt/renewal-hooks/deploy
cat > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh <<'EOF'
#!/usr/bin/env bash
systemctl reload nginx
EOF
chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh

cat <<EOF

============================================================
 Wildcard SSL configured for *.${DOMAIN}
============================================================
EOF

if [[ "${DNS_PLUGIN}" == "manual" ]]; then
  cat <<'EOF'
NOTE: manual DNS-01 certs do NOT auto-renew unattended — `certbot renew`
      will pause for the same TXT-record step every ~90 days, and a cron/
      systemd-timer renewal will just fail silently waiting for manual
      input. For real unattended production renewal, re-run this script
      with DNS_PLUGIN set to a supported provider plugin (dns-cloudflare,
      dns-route53, etc.) and that provider's credentials configured.
EOF
fi
