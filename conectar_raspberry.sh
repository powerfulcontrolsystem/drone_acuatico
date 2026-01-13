#!/usr/bin/env bash
set -euo pipefail

# Uso: ./conectar_raspberry.sh <IP> [PUERTO] [COMANDO]
# Conecta por SSH al usuario 'admin' usando autenticación por clave pública.
# Requiere la clave privada en ~/.ssh/id_raspberrypi

IP="${1:-}"
PORT="${2:-22}"
CMD="${3:-}"
KEY="${HOME}/.ssh/id_raspberrypi"

if [[ -z "$IP" ]]; then
  echo "Uso: ./conectar_raspberry.sh <IP_DE_TU_RASPBERRY> [PUERTO] [COMANDO]" >&2
  exit 1
fi

if [[ ! -f "$KEY" ]]; then
  echo "Error: No se encontró la clave privada en $KEY" >&2
  exit 1
fi

if [[ -n "$CMD" ]]; then
  ssh -i "$KEY" -o ConnectTimeout=8 -o StrictHostKeyChecking=no -p "$PORT" "admin@$IP" "$CMD"
else
  exec ssh -i "$KEY" -o StrictHostKeyChecking=no -p "$PORT" "admin@$IP"
fi