# CollabSims Test Suite

Bateria completa de testes para o backend do CollabSims com execução paralela otimizada.

## Estrutura

```
tests/
├── unit/                   # Testes unitários (< 1s)
│   ├── core/              # Eventos e lógica central
│   ├── persistence/       # SQLite repository
│   └── trackers/          # Event trackers
├── integration/           # Testes de integração (requerem Claude SDK)
│   ├── test_environment.py          # Validação de ambiente
│   ├── test_server_http.py          # Servidor HTTP real
│   ├── test_agent_integration.py   # Claude Agent SDK
│   └── test_bash_commands.py       # Comandos bash reais
├── conftest.py            # Fixtures compartilhadas
└── validate_basic.py      # Script de validação rápida
```

## Execução Rápida

```bash
# Testes unitários super rápidos (< 1s) - RECOMENDADO para desenvolvimento
pytest -m unit -n auto

# Todos os testes em paralelo (~4x mais rápido)
pytest -n auto

# Com cobertura
pytest -n auto --cov=collab_sims --cov-report=term-missing
```

## Comandos Úteis

### Execução Básica

```bash
# Todos os testes (serial - lento)
pytest

# Todos os testes (paralelo - RECOMENDADO)
pytest -n auto

# Arquivo específico
pytest tests/unit/core/test_events.py -n auto

# Teste específico
pytest tests/unit/core/test_events.py::TestEventTypeEnum::test_event_type_values
```

### Desenvolvimento

```bash
# Re-executar apenas testes que falharam
pytest --lf -n auto

# Parar no primeiro erro
pytest -x -n auto

# Modo verbose
pytest -v -n auto

# Modo extra verbose
pytest -vv -n auto
```

### Debugging

```bash
# Traceback completo + variáveis locais
pytest --lf -vv --tb=long --showlocals

# HTML report
pytest --html=report.html --self-contained-html
open report.html

# Sumário de falhas
pytest -ra  # All except passed
pytest -rfs # failed + skipped
```

### Cobertura

```bash
# Terminal (rápido)
pytest --cov=collab_sims --cov-report=term-missing -n auto

# HTML (navegável)
pytest --cov=collab_sims --cov-report=html -n auto
open htmlcov/index.html

# Falhar se cobertura < 80%
pytest --cov=collab_sims --cov-fail-under=80 -n auto
```

## Validação de Ambiente

Antes de executar outros testes, valide o ambiente:

```bash
# Validação rápida
python tests/integration/test_environment.py

# Ou com pytest
pytest tests/integration/test_environment.py -v
```

**O que verifica**:
- ✅ Python 3.13+
- ✅ Dependências instaladas
- ✅ Módulos podem ser importados
- ✅ FastAPI inicializa corretamente

## Requisitos

- Python 3.13+
- Dependências de desenvolvimento: `pip install -e ".[dev]"`
- Para testes de integração: Autenticação via Claude Code
- Plugins pytest: `pytest-xdist`, `pytest-timeout`, `pytest-html` (incluídos em `[dev]`)

## Configuração

Configurações em `pyproject.toml`:

- **Timeout padrão**: 30s (integration: 60s)
- **Marcadores**: Aplicados automaticamente
- **Fixtures**: Em `conftest.py` com escopo otimizado
