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
