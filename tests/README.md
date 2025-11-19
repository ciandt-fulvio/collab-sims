# CollabSims Test Suite

Bateria completa de testes para o backend do CollabSims.

## Estrutura de Testes

```
tests/
├── unit/                   # Testes unitários
│   ├── core/              # Testes de eventos e lógica central
│   ├── persistence/       # Testes do SQLite repository
│   └── trackers/          # Testes de event trackers
├── integration/           # Testes de integração
│   ├── test_agent_integration.py   # Testes com Claude Agent SDK
│   └── test_bash_commands.py       # Testes de comandos bash reais
├── conftest.py            # Fixtures compartilhadas
└── validate_basic.py      # Script de validação rápida

