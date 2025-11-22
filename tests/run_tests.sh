#!/bin/bash
# Script para rodar todos os testes

echo "================================"
echo "CollabSims Test Suite"
echo "================================"
echo ""

# Ativa virtual environment
source .venv/bin/activate

# Roda testes unitários
echo "Running unit tests..."
python -m pytest tests/unit/ -v --tb=short

echo ""
echo "================================"
echo "Test Summary"
echo "================================"

# Conta testes
UNIT_COUNT=$(python -m pytest tests/unit/ --collect-only -q | grep "test session" | awk '{print $1}')
INTEGRATION_COUNT=$(python -m pytest tests/integration/ --collect-only -q | grep "test session" | awk '{print $1}')

echo "Unit tests: $UNIT_COUNT"
echo "Integration tests: $INTEGRATION_COUNT (require Claude Code authentication)"
echo ""
echo "To run integration tests:"
echo "  # Ensure you're authenticated with Claude Code"
echo "  python -m pytest tests/integration/ -v"
