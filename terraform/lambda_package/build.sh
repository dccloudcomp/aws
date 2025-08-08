#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

rm -rf dist build .venv
mkdir -p dist build/python

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Copiar dependencias al paquete
cp -r .venv/lib/python*/site-packages/* build/python/ || true
# Añadir tu código
cp main.py build/

cd build
zip -r ../dist/function.zip .
echo "ZIP generado en dist/function.zip"
