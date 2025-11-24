# Testing Strategy

Estratégia de testes do CollabSims, incluindo testes de unidade, integração e smoke tests.

## Visão Geral

```
┌─────────────────────────────────────────────────────────┐
│                  Testing Pyramid                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│     Manual/Exploratory (ocasional)                     │
│  ─────────────────────────────────────                  │
│                                                         │
│     Smoke Tests (< 1s) - 4 testes                       │
│  ──────────────────────────────────────────             │
│                                                         │
│     Integration Tests (~5s) - 105 testes                │
│  ───────────────────────────────────────────────────    │
│                                                         │
│     Unit Tests (ms) - [futuro]                          │
│  ─────────────────────────────────────────────────────  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Tipos de Testes

### 1. Smoke Tests (Integração Rápida)

**Objetivo:** Prevenir regressão dos bugs mais comuns em < 1 segundo.

**Localização:** `tests/integration/test_smoke_frontend_backend.py`

**Executar:**
```bash
pytest tests/integration/test_smoke_frontend_backend.py -v -m smoke
```

**Cobertura:**
- ✅ Library API endpoints acessíveis (GET 200)
- ✅ URL naming consistency (hyphen vs underscore)
- ✅ Response structure (campos obrigatórios presentes)

**Características:**
- Usa `TestClient` (sem startup event)
- Não requer Claude SDK ou DB completo
- Valida apenas rotas e estrutura de resposta
- Execução em paralelo (pytest-xdist)

**Exemplo:**
```python
def test_list_projects_endpoint_accessible(self, client):
    """Verify /api/library/projects returns 200 (not 404)."""
    response = client.get("/api/library/projects")

    assert response.status_code == 200, (
        f"Library projects endpoint should return 200, got {response.status_code}. "
        "Check that router prefix includes '/api'"
    )
    data = response.json()
    assert "projects" in data
    assert isinstance(data["projects"], list)
```

---

### 2. Integration Tests

**Objetivo:** Testar fluxos completos com Claude SDK e banco de dados.

**Localização:** `tests/integration/` (105 testes existentes)

**Executar:**
```bash
pytest tests/integration/ -v
```

**Cobertura:**
- Session creation e lifecycle
- Query execution com streaming
- Tool approval workflow
- Event persistence
- Error handling

**Características:**
- Requer servidor completo (startup event)
- Inicializa Claude SDK
- Usa SQLite real
- Testes mais lentos (~5s cada)

---

### 3. Unit Tests (Futuro)

**Objetivo:** Testar funções isoladas sem dependências externas.

**Planejamento:**
- Formatadores de ferramentas
- Event handlers
- Validações Pydantic
- Utilitários

---

## Bugs Descobertos e Prevenidos

Durante teste exploratório com Chrome DevTools MCP, 4 bugs críticos foram descobertos:

### Bug #1: Alpine.js Plugin Import

**Sintoma:** Página completamente branca, sem conteúdo

**Arquivo:** `web/sessions/index.html:209`

**Causa:**
```javascript
// ❌ INCORRETO
import collapse from 'https://cdn.jsdelivr.net/npm/@alpinejs/collapse@3/dist/cdn.min.js';
```

**Fix:**
```javascript
// ✅ CORRETO
import Collapse from 'https://cdn.jsdelivr.net/npm/@alpinejs/collapse@3/dist/module.esm.js';
Alpine.plugin(Collapse);
```

**Prevenção:** Smoke test não previne (requer browser real), mas documentado em troubleshooting.

---

### Bug #2: Library API Missing `/api` Prefix

**Sintoma:** Todos os endpoints `/api/library/*` retornavam 404

**Arquivo:** `collab_sims/api/routes/library.py:11`

**Causa:**
```python
# ❌ INCORRETO
router = APIRouter(prefix="/library", tags=["library"])
```

**Fix:**
```python
# ✅ CORRETO
router = APIRouter(prefix="/api/library", tags=["library"])
```

**Prevenção:** ✅ **Smoke test** `test_list_projects_endpoint_accessible()`

---

### Bug #3: Session Metadata Missing Required Fields

**Sintoma:** POST `/api/sessions` retornava 500 (Pydantic validation error)

**Erro:** `Field required [type=missing, input_value={...}]`

**Arquivo:** `collab_sims/api/services/session_manager.py:872-886`

**Causa:**
```python
# ❌ INCORRETO - faltavam campos
def _get_session_metadata(self, session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_data["session_id"],
        "created_at": session_data["created_at"],
        "status": session_data["status"],
        # ... faltavam project_name, agent_name, session_name
    }
```

**Fix:**
```python
# ✅ CORRETO - inclui todos os campos
def _get_session_metadata(self, session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_data["session_id"],
        "project_name": session_data["project_name"],       # ADDED
        "agent_name": session_data.get("agent_name"),      # ADDED
        "session_name": session_data.get("session_name"),  # ADDED
        "created_at": session_data["created_at"],
        "status": session_data["status"],
        # ...
    }
```

**Prevenção:** ⏭️ Smoke test skipped (requer servidor completo), mas coberto por 105 integration tests.

---

### Bug #4: Activity Scripts URL Naming Inconsistency

**Sintoma:** Frontend mostrava "No activity scripts available" (404 no console)

**Arquivo:** `web/js/services/api.js:299, 314, 329`

**Causa:**
```javascript
// ❌ INCORRETO - underscore
const response = await fetch(`${this.baseURL}/api/library/activity_scripts`);
```

**Fix:**
```javascript
// ✅ CORRETO - hyphen
const response = await fetch(`${this.baseURL}/api/library/activity-scripts`);
```

**Prevenção:** ✅ **Smoke test** `test_activity_scripts_uses_hyphen_not_underscore()`

---

## Estratégia de Smoke Tests

### Filosofia

Smoke tests devem ser:

1. **Rápidos** - < 1 segundo total
2. **Simples** - Validar apenas rotas e estrutura básica
3. **Focados** - Prevenir os bugs mais comuns (50%)
4. **Independentes** - Não requerem setup complexo

### O que INCLUIR em smoke tests

✅ Endpoints retornam status code correto
✅ Response tem estrutura esperada
✅ URL naming conventions
✅ Router prefix configuration

### O que NÃO incluir em smoke tests

❌ Lógica de negócio complexa
❌ Integração com Claude SDK
❌ Persistência de dados
❌ Workflows multi-step
❌ Validação de conteúdo detalhado

**Razão:** Esses casos já são cobertos por integration tests completos.

---

## Rodando os Testes

### Apenas Smoke Tests (< 1s)

```bash
pytest tests/integration/test_smoke_frontend_backend.py -v -m smoke
```

**Output esperado:**
```
test_smoke_frontend_backend.py::TestLibraryAPIEndpoints::test_list_projects_endpoint_accessible PASSED
test_smoke_frontend_backend.py::TestLibraryAPIEndpoints::test_list_agents_endpoint_accessible PASSED
test_smoke_frontend_backend.py::TestLibraryAPIEndpoints::test_list_activity_scripts_endpoint_accessible PASSED
test_smoke_frontend_backend.py::TestEndpointNamingConsistency::test_activity_scripts_uses_hyphen_not_underscore PASSED

==== 4 passed, 3 skipped in 0.89s ====
```

---

### Todos os Integration Tests (~5min)

```bash
pytest tests/integration/ -v
```

---

### Com Coverage Report

```bash
pytest tests/integration/ --cov=collab_sims --cov-report=html
open htmlcov/index.html
```

---

### Modo Watch (desenvolvimento)

```bash
pytest-watch tests/integration/test_smoke_frontend_backend.py -v
```

---

## Testes Skipped

Alguns smoke tests são marcados com `@pytest.mark.skip()` porque requerem servidor completo:

```python
@pytest.mark.skip(reason="Requires full server with startup event and Claude SDK")
def test_create_session_returns_required_fields(self, client):
    """Verify session creation returns project_name, agent_name, session_name."""
    # ...
```

**Razão:** Bug #3 já é coberto por 105 integration tests existentes, duplicar em smoke tests seria redundante.

**Quando rodar tests completos:**
```bash
# Iniciar servidores primeiro
./manage_servers.sh start

# Rodar com servidor real (futuro - requer fixture especial)
pytest tests/integration/test_smoke_frontend_backend.py -v --no-skip
```

---

## Exploratory Testing

### Ferramenta: Chrome DevTools MCP

Permite testar a UI real através do Claude Code.

**Como executar:**

1. **Iniciar servidores:**
```bash
./manage_servers.sh start
```

2. **Solicitar teste exploratório:**
```
faça um teste exploratório, subindo o servidor de backend e
rodando o front, e usando o chrome devtools MCP
```

3. **Benefícios:**
   - Testa fluxo completo usuário
   - Descobre bugs de integração frontend-backend
   - Valida UX e comportamento real
   - Complementa testes automatizados

4. **Quando usar:**
   - Após mudanças significativas na UI
   - Antes de releases importantes
   - Quando suspeitar de bugs visuais
   - Para validar novos fluxos

---

## Gerenciamento de Servidores para Testes

### Script de Gerenciamento

```bash
# Iniciar API e Web servers
./manage_servers.sh start

# Ver logs do API
./manage_servers.sh logs api

# Reiniciar apenas backend (após mudanças de código)
./manage_servers.sh restart api

# Parar tudo
./manage_servers.sh stop

# Status
./manage_servers.sh status
```

### Portas

- **API**: `http://localhost:3007`
- **Web**: `http://localhost:3005`
- **API Docs**: `http://localhost:3007/docs`

---

## Métricas Atuais

| Tipo | Quantidade | Tempo | Cobertura |
|------|-----------|-------|-----------|
| Smoke Tests | 4 | < 1s | Rotas críticas |
| Integration Tests | 105 | ~5min | Fluxos completos |
| Unit Tests | 0 | - | (futuro) |
| **Total** | **109** | **~5min** | - |

---

## CI/CD (Futuro)

### GitHub Actions Workflow

```yaml
name: Tests
on: [push, pull_request]
jobs:
  smoke-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run smoke tests
        run: pytest tests/integration/test_smoke_frontend_backend.py -v -m smoke

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run full integration tests
        run: pytest tests/integration/ -v
```

**Estratégia:**
1. Smoke tests rodam em todos os commits (< 1s)
2. Integration tests rodam apenas em PRs/main (~5min)

---

## Debugging Tests

### Ver output detalhado

```bash
pytest tests/integration/test_smoke_frontend_backend.py -v -s
```

### Parar no primeiro erro

```bash
pytest tests/integration/test_smoke_frontend_backend.py -x
```

### Rodar teste específico

```bash
pytest tests/integration/test_smoke_frontend_backend.py::TestLibraryAPIEndpoints::test_list_projects_endpoint_accessible -v
```

### Debug com breakpoint

```python
def test_example(self, client):
    response = client.get("/api/library/projects")
    import pdb; pdb.set_trace()  # Breakpoint
    assert response.status_code == 200
```

---

## Próximos Passos

- 📘 [API Reference](api.md) - Endpoints testados
- 💻 [Frontend](frontend.md) - Troubleshooting de bugs UI
- 🏗️ [Architecture](architecture.md) - Visão geral do sistema
