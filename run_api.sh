#!/bin/bash

# Script para executar a API do collab_sims

echo "🚀 Iniciando CollabSims API..."
echo ""
echo "API será executada em: http://localhost:3007"
echo "Docs disponíveis em: http://localhost:3007/docs"
echo ""

cd "$(dirname "$0")"

# Ativa o ambiente virtual se existir
if [ -d ".venv" ]; then
    echo "📦 Ativando ambiente virtual..."
    source .venv/bin/activate
else
    echo "⚠️  Ambiente virtual não encontrado. Criando..."
    python3.13 -m venv .venv
    source .venv/bin/activate
    echo "📦 Instalando dependências..."
    pip install -e .
    echo ""
fi

# Verifica se as dependências estão instaladas
python -c "import claude_agent_sdk" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Instalando dependências do projeto..."
    pip install -e .
    echo ""
fi

# Inicia a API
python -m uvicorn collab_sims.api.main:app --reload --port 3007 --host 0.0.0.0
