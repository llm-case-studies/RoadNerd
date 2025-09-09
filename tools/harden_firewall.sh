#!/usr/bin/env bash
# RoadNerd Firewall Hardening Helper
# Restrict port 8080 to a specific patient IP using UFW (or iptables fallback).

set -euo pipefail

PATIENT_IP="${1:-}"
PORT="${2:-8080}"

usage(){
  cat << USAGE
Usage: sudo $(basename "$0") <patient_ip> [port]

Examples:
  sudo $(basename "$0") 10.55.0.2            # allow only 10.55.0.2 to TCP/8080
  sudo $(basename "$0") 10.55.0.2 8080       # explicit port

Notes:
  - Requires root privileges.
  - If UFW is available, this adds allow-from rule for the patient IP, then denies the port for others.
  - If UFW is not available, falls back to iptables rules (ipv4).
USAGE
}

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root (sudo)." >&2
  exit 1
fi

if [[ -z "$PATIENT_IP" ]]; then
  usage; exit 1
fi

echo "Hardening: allow TCP/$PORT from $PATIENT_IP; deny others"

if command -v ufw >/dev/null 2>&1; then
  echo "Using UFW..."
  ufw allow from "$PATIENT_IP" to any port "$PORT" proto tcp
  ufw deny "$PORT"/tcp
  echo "UFW rules updated. Current status:" 
  ufw status numbered || true
else
  echo "UFW not found. Using iptables fallback..."
  iptables -A INPUT -p tcp -s "$PATIENT_IP" --dport "$PORT" -j ACCEPT
  iptables -A INPUT -p tcp --dport "$PORT" -j REJECT
  echo "iptables rules added (not persistent across reboot)."
fi

echo "Done. Review rules and test connectivity."

