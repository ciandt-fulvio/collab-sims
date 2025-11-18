# API Reference

CollabSims expõe uma API REST completa via FastAPI. Todos os endpoints estão disponíveis em:
- **Base URL**: `http://localhost:3007/api`
- **Docs interativa**: `http://localhost:3007/docs`
- **ReDoc**: `http://localhost:3007/redoc`

## Endpoints

### Sessions (Multi-Turn)

#### `POST /api/sessions`

Cria uma nova sessão de conversação multi-turn.

**Request:**
```json
{
  "config": {
    "include_partial_messages": true,
    "approval_config": {
      "mode": "auto",
      "tool_policies": {
        "Bash": "high",
        "Write": "medium"
      },
      "auto_approved_tools": []
    }
  },
  "session_type": "worker"
}
```

**Response:** (201 Created)
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-01-18T10:30:00",
  "status": "active",
  "role": "worker",
  "agent_name": null,
  "swarm_id": null,
  "execution_state": "idle",
  "query_count": 0
}
```

**Session Types:**
- `worker` - Agente com execução de código e artifacts
- `scout` - Coordenador de swarm para delegação de tarefas

---

#### `GET /api/sessions`

Lista todas as sessões.

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "550e8400-...",
      "created_at": "2025-01-18T10:30:00",
      "status": "active",
      "role": "worker",
      "query_count": 3
    }
  ],
  "total": 1
}
```

---

#### `GET /api/sessions/{session_id}`

Obtém detalhes de uma sessão específica.

**Response:**
```json
{
  "session_id": "550e8400-...",
  "created_at": "2025-01-18T10:30:00",
  "status": "active",
  "role": "worker",
  "execution_state": "executing",
  "query_count": 5
}
```

---

#### `POST /api/sessions/{session_id}/query/stream`

Envia uma query para a sessão com streaming SSE.

**Request:**
```json
{
  "prompt": "Create a Python script that prints 'Hello World'"
}
```

**Response:** (Server-Sent Events)
```
data: {"type": "query", "prompt": "Create a Python...", "event_id": "evt_001", "timestamp": "..."}

data: {"type": "message", "role": "assistant", "content": "I'll create that for you.", ...}

data: {"type": "tool_use", "tool_name": "Write", "tool_use_id": "tool_001", "input": {...}}

data: {"type": "tool_result", "tool_use_id": "tool_001", "output": "File created"}

data: {"type": "complete", "duration_ms": 1250, "usage": {...}}
```

Ver [events.md](events.md) para detalhes dos eventos.

---

#### `POST /api/sessions/{session_id}/interrupt`

Interrompe a execução de uma query em andamento.

**Response:**
```json
{
  "status": "interrupted",
  "session_id": "550e8400-..."
}
```

---

#### `DELETE /api/sessions/{session_id}`

Deleta uma sessão e todos os seus eventos.

**Response:** (204 No Content)

---

#### `GET /api/sessions/{session_id}/events`

Busca eventos históricos de uma sessão (paginado).

**Query Parameters:**
- `page` (int): Número da página (padrão: 1)
- `page_size` (int): Itens por página (padrão: 100)
- `event_type` (string): Filtrar por tipo de evento

**Response:**
```json
{
  "events": [
    {
      "event_id": 1,
      "event_type": "message",
      "timestamp": "2025-01-18T10:30:05",
      "data": {...}
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 100
}
```

---

### Execute (Single-Turn)

#### `POST /api/execute/stream`

Executa uma tarefa única com streaming SSE (sem manter sessão).

**Request:**
```json
{
  "prompt": "What is 2 + 2?",
  "config": {
    "include_partial_messages": false
  }
}
```

**Response:** (Server-Sent Events)
```
data: {"type": "start", "prompt": "What is 2 + 2?", ...}

data: {"type": "message", "content": "2 + 2 equals 4.", ...}

data: {"type": "complete", "duration_ms": 850, ...}
```

---

#### `POST /api/execute`

Executa uma tarefa única com resposta bufferizada (sem streaming).

**Request:**
```json
{
  "prompt": "What is the capital of France?"
}
```

**Response:**
```json
{
  "events": [
    {"type": "start", ...},
    {"type": "message", "content": "The capital of France is Paris.", ...},
    {"type": "complete", ...}
  ],
  "status": "success",
  "error": null
}
```

---

### Approvals

#### `GET /api/sessions/{session_id}/approvals/pending`

Lista aprovações pendentes para a sessão.

**Response:**
```json
{
  "pending_approvals": [
    {
      "tool_use_id": "tool_001",
      "tool_name": "Bash",
      "tool_input": {"command": "rm -rf /"},
      "status": "pending",
      "risk_level": "high",
      "timestamp": "2025-01-18T10:31:00"
    }
  ],
  "total": 1
}
```

---

#### `POST /api/sessions/{session_id}/approvals/{tool_use_id}/respond`

Aprova ou rejeita a execução de uma ferramenta.

**Request:**
```json
{
  "approved": true,
  "remember": false,
  "reason": null
}
```

**Response:**
```json
{
  "status": "approved",
  "tool_use_id": "tool_001"
}
```

**Parâmetros:**
- `approved` (bool): true para aprovar, false para rejeitar
- `remember` (bool): Se true, auto-aprova esta ferramenta no futuro
- `reason` (string?): Motivo da rejeição (opcional)

---

#### `GET /api/sessions/{session_id}/approvals/config`

Obtém configuração de aprovações da sessão.

**Response:**
```json
{
  "mode": "interactive",
  "tool_policies": {
    "Bash": "high",
    "Write": "medium",
    "Read": "safe"
  },
  "auto_approved_tools": ["Read", "Grep"]
}
```

---

#### `PUT /api/sessions/{session_id}/approvals/config`

Atualiza configuração de aprovações durante a sessão.

**Request:**
```json
{
  "mode": "manual",
  "tool_policies": {
    "Bash": "high"
  },
  "auto_approved_tools": []
}
```

**Approval Modes:**
- `auto` - Todas as ferramentas executam automaticamente
- `interactive` - Apenas ferramentas de alto risco requerem aprovação
- `manual` - Todas as ferramentas requerem aprovação

**Risk Levels:**
- `safe` - Sempre auto-aprovado (ex: Read, Grep)
- `medium` - Requer aprovação em modo interactive/manual
- `high` - Sempre requer aprovação (ex: Bash, Write)

---

### Health & Info

#### `GET /health`

Verifica status da API.

**Response:**
```json
{
  "status": "healthy",
  "service": "collab-sims-api"
}
```

---

#### `GET /`

Informações gerais da API.

**Response:**
```json
{
  "name": "CollabSims API",
  "version": "0.2.0",
  "status": "running",
  "docs": "/docs",
  "endpoints": {
    "execute_buffered": "POST /api/execute",
    "execute_stream": "POST /api/execute/stream",
    ...
  }
}
```

---

## Códigos de Status

| Código | Significado |
|--------|-------------|
| 200 | OK - Requisição bem-sucedida |
| 201 | Created - Recurso criado |
| 204 | No Content - Sucesso sem corpo de resposta |
| 400 | Bad Request - Parâmetros inválidos |
| 404 | Not Found - Recurso não encontrado |
| 500 | Internal Server Error - Erro no servidor |

## Tipos de Dados

### SessionConfig

```typescript
{
  include_partial_messages?: boolean;  // Streaming palavra-por-palavra
  approval_config?: ApprovalConfig;
}
```

### ApprovalConfig

```typescript
{
  mode: "auto" | "interactive" | "manual";
  tool_policies: Record<string, "safe" | "medium" | "high">;
  auto_approved_tools: string[];
}
```

## Exemplos de Uso

### cURL

```bash
# Criar sessão
curl -X POST http://localhost:3007/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"session_type": "worker"}'

# Query com streaming
curl -X POST http://localhost:3007/api/sessions/{id}/query/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello"}' \
  --no-buffer

# Aprovar ferramenta
curl -X POST http://localhost:3007/api/sessions/{id}/approvals/{tool_id}/respond \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

### Python (requests)

```python
import requests

# Criar sessão
response = requests.post(
    "http://localhost:3007/api/sessions",
    json={"session_type": "worker"}
)
session_id = response.json()["session_id"]

# Query bufferizada
response = requests.post(
    f"http://localhost:3007/api/sessions/{session_id}/query",
    json={"prompt": "What is Python?"}
)
print(response.json())
```

### JavaScript (Fetch)

```javascript
// Criar sessão
const response = await fetch('http://localhost:3007/api/sessions', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({session_type: 'worker'})
});
const {session_id} = await response.json();

// Query com SSE
const eventSource = new EventSource(
  `http://localhost:3007/api/sessions/${session_id}/query/stream`
);
eventSource.onmessage = (e) => {
  const event = JSON.parse(e.data);
  console.log(event.type, event);
};
```

## Rate Limiting

Atualmente **sem rate limiting**. Para produção, recomenda-se implementar:
- Limite por IP
- Limite por usuário
- Limite por sessão

## CORS

Configurado para desenvolvimento local:
```python
allow_origins = [
    "http://localhost:3005",
    "http://127.0.0.1:3005"
]
```

Para produção, ajuste em `collab_sims/api/middleware/cors.py`.

## Autenticação

Atualmente **sem autenticação**. Para produção, implemente:
- JWT tokens
- OAuth 2.0
- API keys

## Próximos Passos

- 📡 [Events Reference](events.md) - Detalhes de cada tipo de evento
- 🗄️ [Database Schema](database.md) - Estrutura de dados
- 💻 [Frontend](frontend.md) - Consumindo a API
