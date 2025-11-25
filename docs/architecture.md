# Arquitetura do CollabSims

## Visão Geral

CollabSims é uma aplicação full-stack que permite executar e monitorar agentes Claude em tempo real, com arquitetura baseada em eventos e streaming SSE.

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Browser   │◄────────┤   FastAPI    │◄────────┤   Claude    │
│  (Alpine.js)│  SSE    │   Backend    │  SDK    │   Agent     │
└─────────────┘         └──────────────┘         └─────────────┘
      │                        │
      │                        │
      ▼                        ▼
  UI Updates            ┌──────────────┐
                        │   SQLite     │
                        │   Database   │
                        └──────────────┘
```

## Componentes Principais

### 1. Backend (Python)

#### **FastAPI Application** (`collab_sims/api/`)
- **Routes**: Endpoints REST organizados por domínio
  - `sessions.py` - Gerenciamento de sessões multi-turn
  - `execute.py` - Execução single-turn
  - `approvals.py` - Workflow de aprovação de ferramentas
  - `library.py` - Biblioteca de projetos, agentes e activity scripts
- **Services**: Lógica de negócio
  - `session_manager.py` - Gerencia ciclo de vida de sessões
  - `execution_service.py` - Executa queries single-turn
  - `approval_manager.py` - Coordena aprovações de ferramentas
- **Schemas**: Validação Pydantic
  - Requests e responses tipados
  - Serialização/deserialização automática

#### **Core** (`collab_sims/core/`)
- **Agent**: Wrapper do Claude Agent SDK
- **Session**: Gerenciamento de conversas multi-turn
- **Events**: Sistema de eventos tipados
- **Config**: Configurações de sessão e aprovação
- **Prompts**: Templates de system prompts

#### **Persistence** (`collab_sims/persistence/`)
- **Repository Pattern**: Interface abstrata para persistência
- **SQLite Implementation**: Armazenamento em SQLite com aiosqlite
- **Schema Management**: Migrations automáticas

#### **Trackers** (`collab_sims/trackers/`)
- **Event Tracking**: Rastreamento de eventos de agente
- **Database Tracker**: Persiste eventos no SQLite
- **Stream Tracker**: Emite eventos via SSE
- **Console Tracker**: Log para debugging

### 2. Frontend (JavaScript)

#### **Alpine.js Components** (`web/js/components/`)
- **app.js**: Componente principal (`simsApp`)
- **Chat Panels**: Métricas, plano, eventos, aprovações
- **Sessions List**: Listagem e gerenciamento de sessões

#### **Services** (`web/js/services/`)
- **SimsAPI**: Cliente HTTP para comunicação com backend
- **EventStreamHandler**: Consumo de eventos SSE

#### **Handlers** (`web/js/handlers/`)
- **eventHandlers.js**: Roteamento e processamento de eventos

#### **State Management** (`web/js/state/`)
- **sessionState.js**: Gerenciamento de estado da sessão

#### **Utils** (`web/js/utils/`)
- **toolFormatters.js**: Formatação de inputs/outputs de ferramentas
- **rendering.js**: Markdown e HTML rendering
- **theme.js**: Dark/light mode

### 3. Database (SQLite)

Veja [database.md](database.md) para detalhes do schema.

## Fluxo de Dados

### Single-Turn Execution

```
1. Cliente → POST /api/execute/stream
2. Backend cria StreamTracker
3. Agent executa com Claude SDK
4. Eventos → StreamTracker → SSE → Cliente
5. Cliente processa eventos e atualiza UI
6. Execução completa → CompleteEvent → fim do stream
```

### Multi-Turn Session

```
1. Cliente → POST /api/sessions (cria sessão)
2. Backend cria Session + DatabaseTracker
3. Cliente → POST /api/sessions/{id}/query/stream
4. Backend adiciona query à sessão
5. Eventos → DatabaseTracker (persiste) + StreamTracker (SSE)
6. Cliente recebe eventos e atualiza UI
7. Histórico fica disponível para queries futuras
```

### Approval Workflow

```
1. Agent tenta usar ferramenta
2. ApprovalManager verifica configuração
3. Se requer aprovação → ApprovalRequestEvent
4. Cliente exibe UI de aprovação
5. Usuário aprova/rejeita → POST /api/sessions/{id}/approvals/{tool_id}/respond
6. Backend resume/pula execução da ferramenta
7. ApprovalResponseEvent notifica resultado
```

## Project Structure & Activity Management

### Self-Contained Projects

Projects no CollabSims são **self-contained** - cada projeto embute sua estrutura de processo completa no próprio arquivo markdown, eliminando dependências externas em runtime.

#### Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│ Project Markdown File                                   │
│ ─────────────────────────────────────────────────────── │
│ ---                                                      │
│ title: Meu Projeto                                      │
│ type: design-sprint  # Template usado na criação        │
│ updated_at: 2025-01-18T15:30:00Z  # Optimistic locking │
│ ---                                                      │
│                                                          │
│ ## Process Structure  # Estrutura embutida              │
│                                                          │
│ ### Stage 1: Understand                                 │
│ **Description:** Understanding phase                    │
│                                                          │
│ #### Activity: How Might We                            │
│ **ID:** activity-hmw                                    │
│ **Required:** Yes                                       │
│ **Path:** activities/how-might-we.md                   │
│                                                          │
│ **Definition of Done:**  # Estado persistido aqui       │
│ - [x] Problems identified                              │
│ - [ ] HMW questions created                            │
│                                                          │
│ **Activity Results:**  # Execuções concluídas          │
│ - how-might-we_v01.md (2025-01-15)                     │
│                                                          │
│ ---                                                      │
└─────────────────────────────────────────────────────────┘
```

#### Componentes

**1. Parser Module** (`collab_sims/core/loaders/project_structure_parser.py`)

Responsável por extrair e serializar estruturas de processo em markdown:

```python
# Parse: Markdown → Dataclasses
structure = parse_project_structure(markdown_content)

# Serialize: Dataclasses → Markdown
markdown = serialize_project_structure(structure)

# Update DoD: Atualiza checkbox específico
updated = update_dod_checkbox(
    markdown_content=content,
    stage_id="stage-understand",
    activity_id="activity-hmw",
    item_index=0,
    checked=True
)

# Update timestamp: Para optimistic locking
updated = update_frontmatter_timestamp(content)
```

**Data Classes:**
- `ProjectStructure` - Estrutura completa do projeto
- `Stage` - Estágio com múltiplas atividades
- `Activity` - Atividade com DoD e resultados
- `DefinitionOfDoneItem` - Checkbox item (text + checked)
- `ActivityResult` - Referência a arquivo de resultado

**2. Process Types** (`library/process_types/`)

Process types são **templates** usados apenas na criação de novos projetos. Uma vez criado, o projeto não depende mais do process_type original:

```python
# Na criação (POST /api/library/projects)
1. Lê process_type YAML (template)
2. Expande estrutura completa
3. Embute no corpo do markdown
4. Salva projeto

# Em runtime (GET /api/library/projects/{name}/process-progress)
1. Lê apenas o arquivo do projeto
2. Parser extrai estrutura do markdown
3. Retorna estrutura com status
```

**Vantagens:**
- ✅ Projetos são portable (não dependem de YAMLs externos)
- ✅ Histórico completo no próprio arquivo
- ✅ Process types podem evoluir sem afetar projetos existentes
- ✅ Estado de DoD persiste no projeto

#### Fluxo de Dados

**Criação de Projeto:**
```
1. Cliente → POST /api/library/projects
   {
     "name": "meu-projeto",
     "content": "---\ntype: design-sprint\n---\n..."
   }

2. Backend:
   a) Extrai type do frontmatter
   b) Lê process_type YAML (template)
   c) Serializa estrutura completa
   d) Embute no markdown após frontmatter
   e) Salva arquivo em library/projects/

3. Resposta: Projeto criado com estrutura embutida
```

**Consulta de Progresso:**
```
1. Cliente → GET /api/library/projects/{name}/process-progress

2. Backend:
   a) Lê arquivo do projeto
   b) Parser extrai estrutura do markdown
   c) Calcula completion_count, activity.completed
   d) Retorna estrutura com status

3. Resposta:
   {
     "stages": [...],
     "updated_at": "2025-01-18T15:30:00Z"
   }
```

**Update de Definition of Done:**
```
1. Cliente → PATCH /api/library/projects/{name}/dod
   {
     "stage_id": "stage-understand",
     "activity_id": "activity-hmw",
     "item_index": 0,
     "checked": true,
     "expected_last_modified": "2025-01-18T15:30:00Z"  # Optimistic lock
   }

2. Backend:
   a) Lê arquivo do projeto
   b) Valida expected_last_modified com updated_at
      → Se diferente: 409 Conflict (prevenção de conflito)
   c) update_dod_checkbox() modifica markdown
   d) update_frontmatter_timestamp() atualiza updated_at
   e) Salva arquivo atualizado

3. Resposta:
   {
     "success": true,
     "new_last_modified": "2025-01-18T15:45:00Z"
   }
```

#### Optimistic Locking

Para prevenir conflitos em updates concorrentes, usamos **optimistic locking** baseado em timestamp:

```python
# Cliente envia timestamp que conhece
PATCH /api/library/projects/meu-projeto/dod
{
  "expected_last_modified": "2025-01-18T15:30:00Z",
  ...
}

# Backend valida
if file_updated_at != expected_last_modified:
    raise HTTPException(409, "Conflict: file was modified")

# Update bem-sucedido retorna novo timestamp
{
  "new_last_modified": "2025-01-18T15:45:00Z"
}
```

**Comportamento no Cliente:**
- Cliente mantém `updated_at` recebido na última leitura
- Envia esse valor em updates subsequentes
- Se receber 409: recarrega projeto e pede usuário resolver conflito

#### Parsing de Markdown

O parser usa regex para extrair estruturas do markdown:

**Estrutura esperada:**
```markdown
## Process Structure

### Stage N: Title
**Description:** Stage description

#### Activity: Activity Title
**ID:** activity-id
**Required:** Yes/No
**Path:** path/to/script.md
**Description:** Activity description

**Definition of Done:**
- [ ] Unchecked item
- [x] Checked item

**Activity Results:**
- filename.md (2025-01-15)

---
```

**Patterns importantes:**
- `\Z` para end-of-string (não `$` com MULTILINE)
- Lookahead `(?=^\*\*|^---|\Z)` para capturar múltiplos checkboxes
- Captura de checkboxes: `^- \[([ x])\] (.+?)$`

#### Testes

Cobertura completa em `tests/unit/core/loaders/test_project_structure_parser.py`:

- ✅ Parse de estruturas (vazia, single stage, múltiplos stages)
- ✅ Serialização (roundtrip preserva dados)
- ✅ Update de DoD checkboxes (checked/unchecked)
- ✅ Update de timestamps (frontmatter)
- ✅ Validação de erros (stage/activity/item não encontrados)
- ✅ Conversão para dicionário (API responses)

Ver também: [api.md](api.md) para detalhes dos endpoints.

## Padrões de Arquitetura

### Event-Driven Architecture

Todos os eventos de agente são capturados e processados através de:
- **Event Types**: Enum tipado (`EventType`)
- **Event Classes**: Dataclasses com validação
- **Trackers**: Observadores que reagem a eventos
- **SSE Streaming**: Comunicação real-time com frontend

### Repository Pattern

Abstração da camada de persistência:
```python
class SessionRepository(ABC):
    async def create_session(...)
    async def get_session(...)
    async def save_event(...)
```

Implementações:
- `SQLiteRepository`: Produção
- `InMemoryRepository`: Testes (futuro)

### Dependency Injection

Services são injetados via FastAPI:
```python
@router.post("/sessions")
async def create_session(
    manager: SessionManager = Depends(get_session_manager)
):
    ...
```

### Component Composition (Frontend)

Alpine.js components usam composição:
```javascript
export function simsApp() {
  return {
    ...metricsPanel(),
    ...planPanel(),
    ...eventsPanel(),
    // ... outros painéis
  };
}
```

## Escalabilidade

### Limitações Atuais

- SQLite (single-file database)
- In-memory session storage
- Single-process FastAPI

### Melhorias Futuras

- **PostgreSQL**: Para multi-tenant e maior throughput
- **Redis**: Cache de sessões ativas
- **Message Queue**: Para processar eventos assíncronos
- **Horizontal Scaling**: Múltiplas instâncias FastAPI
- **Load Balancer**: Distribuir carga entre instâncias

## Segurança

### Implementado

- CORS configurado para localhost
- Foreign keys no SQLite
- Validação de inputs (Pydantic)
- Sanitização de HTML no frontend

### Recomendações para Produção

- [ ] Autenticação (JWT, OAuth)
- [ ] Rate limiting
- [ ] HTTPS obrigatório
- [ ] Sanitização de prompts
- [ ] Validação de tool approvals
- [ ] Audit logging

## Performance

### Backend

- **Async/await**: Operações I/O não bloqueantes
- **Connection pooling**: SQLite com aiosqlite
- **Streaming**: SSE para reduzir latência

### Frontend

- **No build step**: ES6 modules nativos
- **Lazy loading**: Componentes carregados sob demanda
- **Event deduplication**: Previne re-renders desnecessários

## Monitoramento

### Logs

```python
# Configurado em collab_sims/api/main.py
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Métricas

Disponíveis via eventos:
- Tokens (input/output)
- Custo (USD)
- Duração (ms)
- Número de turns

### Health Check

```bash
GET /health
→ {"status": "healthy", "service": "collab-sims-api"}
```

## Gerenciamento de Servidores

### Script de Gerenciamento (`manage_servers.sh`)

Script bash com tmux para gerenciar API e Web servers:

```bash
# Iniciar servidores
./manage_servers.sh start

# Visualizar logs
./manage_servers.sh logs [api|web]

# Reiniciar servidor específico
./manage_servers.sh restart api

# Parar todos os servidores
./manage_servers.sh stop

# Ver status
./manage_servers.sh status
```

**Características:**
- Gerenciamento via tmux (sessão `collab-sims`)
- Duas janelas: `api` (porta 3007) e `web` (porta 3005)
- Restart independente de cada servidor
- Logs isolados por servidor
- Comandos coloridos com feedback visual

## Testing

### Smoke Tests

Smoke tests de integração em `tests/integration/test_smoke_frontend_backend.py`:

```bash
# Rodar smoke tests
pytest tests/integration/test_smoke_frontend_backend.py -v -m smoke
```

**Cobertura:**
- ✅ Library API endpoints (projetos, agentes, activity scripts)
- ✅ URL naming consistency (hyphen vs underscore)
- ⏭️ Session creation metadata (requer servidor completo, skipped)

**Bugs prevenidos:**
1. **Bug #2**: Library endpoints retornando 404 (faltava `/api` prefix)
2. **Bug #4**: Frontend usando underscore mas backend usando hyphen

Ver [testing.md](testing.md) para detalhes completos.

## Próximos Passos

- 📘 [API Documentation](api.md)
- 🗄️ [Database Schema](database.md)
- 📡 [Events Reference](events.md)
- 💻 [Frontend Architecture](frontend.md)
