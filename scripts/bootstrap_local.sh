#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${VENV_DIR:-$HOME/.venvs/PortalRecruit}"
FORCE_RECREATE="${FORCE_RECREATE:-0}"

echo "[PortalRecruit] Using venv: $VENV_DIR"

echo "[PortalRecruit] Creating/using Python 3.13 venv (recommended)"

if [[ -d "$VENV_DIR" && "$FORCE_RECREATE" != "1" ]]; then
  echo "[PortalRecruit] Venv already exists. Set FORCE_RECREATE=1 to recreate it."
else
  rm -rf "$VENV_DIR"
  python3.13 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install -U pip

# IMPORTANT:
# Installing torch from PyPI will often pull CUDA wheels and can be ~1GB+.
# For this project, CPU wheels are typically sufficient.
# If you want CUDA-enabled torch, install it manually following PyTorch docs.

echo "[PortalRecruit] Installing CPU torch wheel (avoids huge CUDA downloads)"
"$VENV_DIR/bin/pip" install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio

echo "[PortalRecruit] Installing project requirements"
"$VENV_DIR/bin/pip" install -r requirements.txt

echo ""
echo "Done. Activate with:"
echo "  source \"$VENV_DIR/bin/activate\""
