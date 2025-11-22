#!/bin/bash

# Script para executar o Web Server do collab_sims

echo "🌐 Iniciando CollabSims Web Server..."
echo ""
echo "Web interface será executada em: http://localhost:3005"
echo "Certifique-se de que a API está rodando em: http://localhost:3007"
echo ""


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

cd "$(dirname "$0")/web"

# Verifica se Python está disponível
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Por favor, instale Python 3."
    exit 1
fi

# Inicia o servidor HTTP
echo "📡 Iniciando servidor HTTP na porta 3005..."
python3 -m http.server 3005
