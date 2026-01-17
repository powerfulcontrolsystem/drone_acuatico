#!/bin/bash

# Script para actualizar el repositorio con los últimos cambios

cd /home/admin/drone_acuatico

echo "=== Estado actual del repositorio ==="
git status

echo ""
echo "=== Agregando todos los cambios ==="
git add .

echo ""
echo "=== Estado después de git add ==="
git status

echo ""
read -p "Ingresa el mensaje del commit: " mensaje

git commit -m "$mensaje"

echo ""
echo "=== Subiendo cambios al repositorio remoto ==="
git push

echo ""
echo "=== Actualización completada ==="
