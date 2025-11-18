#!/bin/bash

# Script para executar a API do collab_sims

echo "🚀 Iniciando CollabSims API..."
echo ""
echo "API será executada em: http://localhost:3007"
echo "Docs disponíveis em: http://localhost:3007/docs"
echo ""

cd "$(dirname "$0")"

# Verifica se aiosqlite está instalado
python3 -c "import aiosqlite" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  aiosqlite não está instalado. Instalando..."
    pip3 install aiosqlite
    echo ""
fi

# Inicia a API
python3 -m uvicorn collab_sims.api.main:app --reload --port 3007 --host 0.0.0.0
