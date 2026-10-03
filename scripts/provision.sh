#!/usr/bin/env bash
# Provisions an Ubuntu/Debian host to run the phishing-sim-platform stack:
# Docker + Compose, plus local CLI tooling (Python, Node, psql, redis-cli)
# useful for running Alembic migrations or debugging outside containers.
#
# Usage: ./scripts/provision.sh
# Safe to re-run: every step checks current state before acting.

set -euo pipefail

if [[ $EUID -eq 0 ]]; then
    SUDO=""
else
    SUDO="sudo"
fi

log() { printf '\n\033[1;32m==> %s\033[0m\n' "$1"; }

log "Updating package index and installed packages"
$SUDO apt-get update
$SUDO apt-get upgrade -y

log "Installing base prerequisites"
$SUDO apt-get install -y ca-certificates curl gnupg lsb-release git make

log "Installing Docker Engine + Compose plugin"
if command -v docker &>/dev/null; then
    echo "Docker already installed: $(docker --version)"
else
    curl -fsSL https://get.docker.com | $SUDO sh
fi

if ! getent group docker | grep -qw "$USER"; then
    log "Adding $USER to the docker group"
    $SUDO usermod -aG docker "$USER"
    echo "Group membership won't take effect in this shell.
Log out and back in (or run 'newgrp docker') before using docker without sudo."
else
    echo "$USER is already in the docker group"
fi

log "Installing local CLI tooling (Python, Node, psql, redis-cli)"
if ! $SUDO apt-get install -y python3.11 python3.11-venv 2>/dev/null; then
    echo "python3.11 not available from apt on this release; falling back to python3"
    $SUDO apt-get install -y python3 python3-venv
fi
$SUDO apt-get install -y nodejs npm postgresql-client redis-tools

log "Verifying installed versions"
docker --version
docker compose version
git --version
python3 --version
node --version
npm --version

log "Provisioning complete"
