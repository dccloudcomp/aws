#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

rm -rf dist build .venv
mkdir -p dist build

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Copia dependencias a la RAÍZ del paquete (no a build/python)
cp -r .venv/lib/python*/site-packages/* build/

# Añade tu código
cp main.py build/

cd build
zip -r ../dist/function.zip .
echo "ZIP generado en dist/function.zip"
