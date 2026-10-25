#!/usr/bin/env bash
# Prepare a FRESH Ubuntu 22.04/24.04 server for the DG stand. Run once, as root.
#   - installs Docker Engine + Compose plugin from Docker's official apt repository
#   - firewall: only SSH (22), HTTP (80), HTTPS (443) are reachable from outside
# Note: Docker publishes container ports through its own iptables rules and can bypass ufw.
# That is why docker-compose.server.yml publishes ONLY the edge's 80 and 443 (checked by
# deploy/hosted/tests/test_server_kit.py). Do not add other `ports:` to the stack.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "run as root (sudo -i)" >&2
    exit 1
fi
. /etc/os-release
case "${ID:-}" in
    ubuntu) ;;
    *) echo "this script supports Ubuntu only (found: ${ID:-unknown})" >&2; exit 1 ;;
esac

export DEBIAN_FRONTEND=noninteractive
# A fresh VPS often runs unattended-upgrades, which holds the dpkg lock: wait instead of failing.
APT=(apt-get -o DPkg::Lock::Timeout=300 -y)
"${APT[@]}" update
"${APT[@]}" install ca-certificates curl gnupg ufw git python3

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
"${APT[@]}" update
"${APT[@]}" install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

# Enabling the firewall while SSH listens elsewhere would lock the owner out: refuse instead.
# awk must read to EOF (no early exit): an early exit SIGPIPEs sshd and pipefail+set -e then aborts the script.
ssh_port="$(sshd -T 2>/dev/null | awk '/^port /&&!seen{print $2; seen=1}')"
if [ "${ssh_port:-22}" != "22" ]; then
    echo "sshd listens on port ${ssh_port}, not 22: not enabling the firewall. Adjust the script deliberately." >&2
    exit 1
fi
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

docker --version
docker compose version
ufw status verbose
echo "server prepared. Next: copy the repository export here, run make_env.py, then deploy.sh"
