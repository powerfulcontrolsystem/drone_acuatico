#!/usr/bin/env bash
set -euo pipefail

# Uso: ./conectar_raspberry.sh <IP> [PUERTO] [COMANDO]
# Conecta por SSH al usuario 'admin' usando la contraseña 'admin' sin pedirla.
# Requiere 'sshpass'. Intentará instalarlo si no existe.

IP="${1:-}"
PORT="${2:-22}"
CMD="${3:-}"

if [[ -z "$IP" ]]; then
  echo "Uso: ./conectar_raspberry.sh <IP_DE_TU_RASPBERRY> [PUERTO] [COMANDO]" >&2
  exit 1
fi

if ! command -v sshpass >/dev/null 2>&1; then
  echo "Instalando sshpass..." >&2
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update && sudo apt-get install -y sshpass
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y sshpass
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --noconfirm sshpass
  else
    echo "Instala 'sshpass' manualmente para continuar." >&2
    exit 1
  fi
fi

if [[ -n "$CMD" ]]; then
  sshpass -p "admin" ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=no -p "$PORT" "admin@$IP" "$CMD"
else
  exec sshpass -p "admin" ssh -o StrictHostKeyChecking=no -p "$PORT" "admin@$IP"
fi