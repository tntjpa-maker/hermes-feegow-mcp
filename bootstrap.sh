#!/bin/bash

set -e

echo "========================================"
echo "ANA Bootstrap"
echo "========================================"

echo "[1/6] Instalando dependências..."
uv sync

echo "[2/6] Validando ambiente..."
python --version

echo "[3/6] Executando testes..."
pytest

echo "[4/6] Validando MCP..."
hermes mcp list || true

echo "[5/6] Ambiente pronto."

echo
echo "Para iniciar:"
echo
echo "hermes mcp serve"
