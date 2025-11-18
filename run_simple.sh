#!/bin/bash

# Script para executar a API simplificada (sem CollabSims SDK)

echo "🚀 Iniciando CollabSims API (Simple Version)..."
echo ""
echo "✅ Esta versão NÃO requer CollabSims SDK"
echo "✅ Usa apenas collab_sims/persistence"
echo "✅ Simula respostas do agente para testar o frontend"
echo ""
echo "API: http://localhost:3007"
echo "Docs: http://localhost:3007/docs"
echo "Frontend: http://localhost:3005 (em outro terminal)"
echo ""

cd "$(dirname "$0")"

# Verificar se aiosqlite está instalado
python3 -c "import aiosqlite" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  aiosqlite não instalado. Instalando..."
    pip3 install aiosqlite
    echo ""
fi

# Iniciar API
python3 api_simple.py
