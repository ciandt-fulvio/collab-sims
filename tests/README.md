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
│   ├── test_environment.py          # Validação de ambiente e dependências
│   ├── test_server_http.py          # Testes HTTP reais do servidor
│   ├── test_agent_integration.py   # Testes com Claude Agent SDK
│   └── test_bash_commands.py       # Testes de comandos bash reais
├── conftest.py            # Fixtures compartilhadas
└── validate_basic.py      # Script de validação rápida
```

## Testes de Integração

### Teste de Ambiente (`test_environment.py`)

**Propósito**: Valida que o ambiente de desenvolvimento está configurado corretamente.

**O que verifica**:
- ✅ Versão do Python (3.13+)
- ✅ Dependências críticas instaladas (attrs, jsonschema, fastapi, etc)
- ✅ Todos os módulos principais podem ser importados
- ✅ API FastAPI pode ser inicializada
- ✅ Ambiente virtual está configurado
- ✅ Integração entre pacotes funciona

**Quando executar**:
- Após clonar o repositório
- Depois de instalar/atualizar dependências
- Quando encontrar erros de importação
- Antes de fazer deploy

**Como executar**:

```bash
# Executar apenas testes de ambiente
python tests/integration/test_environment.py

# Ou com pytest
pytest tests/integration/test_environment.py -v

# Ou todos os testes de integração
pytest tests/integration/ -v
```

**Exemplo de saída**:

```
✓ attrs version 25.4.0 (min: 22.2.0)
✓ jsonschema version 4.25.1 (min: 4.20.0)
✓ fastapi version 0.121.2 (min: 0.115.0)
✓ collab_sims imported successfully
✓ collab_sims.api.main imported successfully

26 passed in 0.74s

✅ VALIDATION PASSED - Environment is correctly configured
```

**Problemas comuns detectados**:

1. **ModuleNotFoundError: No module named 'attrs'**
   - Causa: Dependências não instaladas
   - Solução: `pip install -e .`

2. **Python 3.11.x ao invés de 3.13+**
   - Causa: Ambiente virtual não ativado ou criado com Python errado
   - Solução:
     ```bash
     python3.13 -m venv .venv
     source .venv/bin/activate
     pip install -e .
     ```

3. **Importação falhando mesmo com dependências instaladas**
   - Causa: Conflito entre instalações do sistema e venv
   - Solução: Recriar ambiente virtual limpo

### Teste de Servidor HTTP (`test_server_http.py`)

**Propósito**: Valida que o servidor pode ser iniciado e responde a requisições HTTP reais.

**O que verifica**:
- ✅ Servidor inicia com sucesso em uma porta
- ✅ Requisições HTTP funcionam corretamente
- ✅ Endpoints respondem conforme esperado
- ✅ Servidor lida com múltiplas requisições concorrentes
- ✅ Códigos de erro HTTP corretos (404, 422)
- ✅ Shutdown gracioso do servidor

**Diferença de outros testes**:
- Usa requisições HTTP **reais** (não TestClient)
- Inicia servidor **uvicorn** em processo separado
- Valida stack completa: uvicorn + FastAPI + código da aplicação

**Quando executar**:
- Antes de fazer deploy
- Depois de mudanças na configuração do servidor
- Para validar comportamento de rede
- Para testar timeouts e concorrência

**Como executar**:

```bash
# Executar apenas testes HTTP
python tests/integration/test_server_http.py

# Ou com pytest
pytest tests/integration/test_server_http.py -v
```

**Exemplo de saída**:

```
✓ Server started on port 60479
✓ Received message via HTTP: resposta para: 'say 'hello world' and nothing else'
✓ Concurrent requests handled: 10/10 successful
8 passed in 9.18s

✅ ALL HTTP SERVER TESTS PASSED

The server can:
  ✓ Start successfully on a port
  ✓ Respond to HTTP requests
  ✓ Handle concurrent requests
  ✓ Return proper error codes
  ✓ Execute agent queries via HTTP
```

**Testes específicos**:

1. **test_server_starts_and_responds**: Servidor inicia e responde
2. **test_hello_world_via_http**: Execução de query via HTTP real
3. **test_root_endpoint_via_http**: Endpoint raiz retorna info da API
4. **test_api_docs_accessible**: Documentação OpenAPI acessível
5. **test_concurrent_requests**: Múltiplas requisições simultâneas
6. **test_invalid_endpoint_returns_404**: Endpoints inválidos retornam 404
7. **test_invalid_json_returns_422**: JSON inválido retorna 422
8. **test_missing_required_field_returns_422**: Campos obrigatórios faltando

## Como Executar os Testes

### Todos os testes
```bash
pytest
```

### Testes específicos
```bash
# Apenas testes unitários
pytest tests/unit/

# Apenas testes de integração
pytest tests/integration/

# Um arquivo específico
pytest tests/integration/test_environment.py

# Uma classe específica
pytest tests/integration/test_environment.py::TestPythonVersion

# Um teste específico
pytest tests/integration/test_environment.py::TestPythonVersion::test_python_version_is_3_13_or_higher
```

### Com cobertura
```bash
pytest --cov=collab_sims --cov-report=html
open htmlcov/index.html
```

### Modo verboso
```bash
pytest -v -s
```

## Estratégia de Testes

**Ordem recomendada ao configurar ambiente**:

1. **Validação de Ambiente** (`test_environment.py`)
   - Garante que o ambiente está correto antes de executar outros testes

2. **Testes Unitários** (`tests/unit/`)
   - Verifica componentes isolados

3. **Testes de Integração** (`tests/integration/`)
   - Verifica integração com Claude SDK e outros sistemas

## Requisitos

- Python 3.13+
- Todas as dependências instaladas: `pip install -e .`
- Para testes de integração: Autenticação via Claude Code (sessão ativa)

