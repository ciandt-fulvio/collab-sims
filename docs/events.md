# Events Reference

CollabSims usa um sistema de eventos tipados para comunicação em tempo real entre backend e frontend via Server-Sent Events (SSE).

## Event Types

Todos os eventos implementam a interface base:

```typescript
interface BaseEvent {
  type: EventType;
  event_id: string;        // UUID único
  timestamp: string;       // ISO 8601
  session_id?: string;
  user_id?: string;
  metadata?: Record<string, any>;
}
```

## Session Lifecycle

### `session_start`

Emitido quando uma nova sessão é criada.

```json
{
  "type": "session_start",
  "event_id": "evt_001",
  "timestamp": "2025-01-18T10:30:00.000Z",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "tags": ["development", "testing"],
  "system_prompt": "You are a helpful AI assistant..."
}
```

**Campos:**
- `tags` - Lista de tags da sessão
- `system_prompt` - Prompt de sistema enviado ao Claude Agent SDK

---

### `session_end`

Emitido quando uma sessão é encerrada.

```json
{
  "type": "session_end",
  "event_id": "evt_999",
  "timestamp": "2025-01-18T11:30:00.000Z",
  "session_id": "550e8400-...",
  "total_queries": 10,
  "total_duration_ms": 45000
}
```

---

## Query Lifecycle

### `query`

Emitido quando uma nova query é enviada na sessão.

```json
{
  "type": "query",
  "event_id": "evt_002",
  "timestamp": "2025-01-18T10:30:05.000Z",
  "session_id": "550e8400-...",
  "prompt": "Create a Python script",
  "query_number": 1
}
```

---

### `start`

Emitido no início de uma execução (legacy, mantido para compatibilidade).

```json
{
  "type": "start",
  "event_id": "evt_003",
  "timestamp": "2025-01-18T10:30:05.100Z",
  "prompt": "Create a Python script",
  "options": {
    "include_partial_messages": true
  }
}
```

---

### `complete`

Emitido quando a execução termina.

```json
{
  "type": "complete",
  "event_id": "evt_099",
  "timestamp": "2025-01-18T10:30:15.000Z",
  "duration_ms": 9900,
  "total_cost_usd": 0.0025,
  "num_turns": 3,
  "result": "Task completed successfully",
  "usage": {
    "input_tokens": 1250,
    "output_tokens": 850,
    "total_tokens": 2100
  }
}
```

**Campos:**
- `duration_ms` - Duração total em milissegundos
- `total_cost_usd` - Custo total estimado em USD
- `num_turns` - Número de turnos (round-trips com Claude)
- `result` - Resultado final (opcional)
- `usage` - Estatísticas de tokens

---

## Agent Messages

### `message`

Mensagem completa do agente ou usuário.

```json
{
  "type": "message",
  "event_id": "evt_010",
  "timestamp": "2025-01-18T10:30:06.000Z",
  "role": "assistant",
  "content": "I'll help you create that Python script.",
  "model": "claude-3-5-sonnet-20250122",
  "thinking": "The user wants a simple Python script..."
}
```

**Campos:**
- `role` - "assistant" | "user" | "system"
- `content` - Conteúdo da mensagem
- `model` - Modelo Claude usado (opcional)
- `thinking` - Reasoning interno do modelo (opcional)

---

### `partial_message`

Streaming incremental de texto (palavra-por-palavra).

```json
{
  "type": "partial_message",
  "event_id": "evt_011",
  "timestamp": "2025-01-18T10:30:06.050Z",
  "delta": "I'll ",
  "index": 0,
  "content_type": "text"
}
```

**Campos:**
- `delta` - Fragmento de texto recém-gerado
- `index` - Posição do fragmento na sequência
- `content_type` - Tipo do conteúdo (sempre "text")

**Uso:**
```javascript
let fullText = '';
if (event.type === 'partial_message') {
  fullText += event.delta;
  updateUI(fullText);
}
```

---

## Tool Execution

### `tool_use`

Emitido quando o agente usa uma ferramenta.

```json
{
  "type": "tool_use",
  "event_id": "evt_020",
  "timestamp": "2025-01-18T10:30:07.000Z",
  "tool_name": "Write",
  "tool_use_id": "tool_001",
  "input": {
    "file_path": "/app/hello.py",
    "content": "print('Hello World')"
  },
  "originated_from_message_id": "msg_001"
}
```

**Campos:**
- `tool_name` - Nome da ferramenta (Bash, Write, Read, etc.)
- `tool_use_id` - ID único desta execução
- `input` - Parâmetros passados para a ferramenta
- `originated_from_message_id` - ID da mensagem que anunciou esta ferramenta

**Ferramentas comuns:**
- `Bash` - Execução de comandos shell
- `Write` - Criar/sobrescrever arquivo
- `Edit` - Editar arquivo existente
- `Read` - Ler arquivo
- `Grep` - Buscar em arquivos
- `Glob` - Listar arquivos por padrão

---

### `tool_result`

Emitido quando a ferramenta termina de executar.

```json
{
  "type": "tool_result",
  "event_id": "evt_021",
  "timestamp": "2025-01-18T10:30:07.500Z",
  "tool_use_id": "tool_001",
  "tool_name": "Write",
  "output": "File created successfully at /app/hello.py",
  "is_error": false,
  "originated_from_message_id": "msg_001"
}
```

**Campos:**
- `tool_use_id` - ID da execução (mesmo de `tool_use`)
- `output` - Resultado da execução
- `is_error` - Se houve erro
- `originated_from_message_id` - ID da mensagem original

---

## Plan & Progress

### `plan`

Emitido quando o agente cria ou atualiza um plano de tarefas.

```json
{
  "type": "plan",
  "event_id": "evt_030",
  "timestamp": "2025-01-18T10:30:08.000Z",
  "todos": [
    {
      "content": "Create Python file",
      "status": "completed",
      "active_form": "Creating Python file"
    },
    {
      "content": "Test the script",
      "status": "in_progress",
      "active_form": "Testing the script"
    },
    {
      "content": "Document the code",
      "status": "pending",
      "active_form": "Documenting the code"
    }
  ],
  "total_tasks": 3,
  "completed": 1,
  "in_progress": 1,
  "pending": 1,
  "changes": {
    "added": ["Document the code"],
    "removed": [],
    "status_changed": [
      {"task": "Create Python file", "from": "in_progress", "to": "completed"}
    ]
  },
  "tool_use_id": "tool_002"
}
```

**Status de tarefa:**
- `pending` - Não iniciada
- `in_progress` - Em execução
- `completed` - Concluída

---

### `progress`

Atualizações de progresso genéricas.

```json
{
  "type": "progress",
  "event_id": "evt_035",
  "timestamp": "2025-01-18T10:30:09.000Z",
  "completed": 5,
  "total": 10,
  "percentage": 50.0,
  "current_task": "Processing file 5 of 10"
}
```

---

## Approval Workflow

### `approval_request`

Ferramenta requer aprovação do usuário antes de executar.

```json
{
  "type": "approval_request",
  "event_id": "evt_040",
  "timestamp": "2025-01-18T10:30:10.000Z",
  "tool_use_id": "tool_003",
  "tool_name": "Bash",
  "tool_input": {
    "command": "rm important_file.txt"
  },
  "status": "pending",
  "risk_level": "high"
}
```

**Risk Levels:**
- `safe` - Operação segura (Read, Grep)
- `medium` - Operação moderada (Write, Edit)
- `high` - Operação arriscada (Bash, Delete)

---

### `approval_response`

Usuário aprovou ou rejeitou a ferramenta.

```json
{
  "type": "approval_response",
  "event_id": "evt_041",
  "timestamp": "2025-01-18T10:30:12.000Z",
  "tool_use_id": "tool_003",
  "approved": false,
  "remember": false,
  "reason": "Cannot delete important files"
}
```

**Campos:**
- `approved` - true se aprovado, false se rejeitado
- `remember` - Se true, auto-aprova esta ferramenta no futuro
- `reason` - Motivo da decisão (opcional)

---

## System & Metrics

### `metrics`

Métricas em tempo real durante a execução.

```json
{
  "type": "metrics",
  "event_id": "evt_050",
  "timestamp": "2025-01-18T10:30:11.000Z",
  "duration_ms": 5000,
  "input_tokens": 800,
  "output_tokens": 450,
  "total_cost_usd": 0.0015
}
```

**Uso:** Atualizar UI de métricas em tempo real enquanto a query executa.

---

### `error`

Erros durante a execução.

```json
{
  "type": "error",
  "event_id": "evt_099",
  "timestamp": "2025-01-18T10:30:14.000Z",
  "error": "Tool execution failed",
  "error_type": "ToolExecutionError",
  "context": {
    "tool_name": "Bash",
    "command": "invalid_command"
  },
  "traceback": "Traceback (most recent call last):\n  ..."
}
```

---

## Event Flow Examples

### Successful Query

```
1. query          - "Create a Python file"
2. message        - "I'll create that for you."
3. tool_use       - Write tool
4. tool_result    - File created
5. message        - "File created successfully!"
6. complete       - Execution finished
```

### Query with Approval

```
1. query               - "Delete all files"
2. message             - "I'll delete the files."
3. approval_request    - Bash tool (high risk)
   ... wait for user ...
4. approval_response   - User rejected
5. message             - "Deletion cancelled per your request."
6. complete            - Execution finished
```

### Query with Plan

```
1. query          - "Build a web app"
2. message        - "I'll create a plan."
3. plan           - 5 tasks created
4. tool_use       - Write (create structure)
5. tool_result    - Files created
6. plan           - Task 1 completed
7. tool_use       - Write (add code)
8. plan           - Task 2 in progress
   ... continues ...
9. complete       - All tasks done
```

## Consuming Events (Frontend)

### JavaScript (EventSource)

```javascript
const eventSource = new EventSource('/api/sessions/123/query/stream');

eventSource.onmessage = (e) => {
  const event = JSON.parse(e.data);

  switch(event.type) {
    case 'message':
      displayMessage(event.content);
      break;
    case 'tool_use':
      showTool(event.tool_name, event.input);
      break;
    case 'complete':
      showMetrics(event.usage);
      break;
  }
};

eventSource.onerror = (err) => {
  console.error('SSE error:', err);
  eventSource.close();
};
```

### Python (requests)

```python
import requests
import json

response = requests.post(
    'http://localhost:3007/api/sessions/123/query/stream',
    json={'prompt': 'Hello'},
    stream=True
)

for line in response.iter_lines():
    if line.startswith(b'data: '):
        event_data = json.loads(line[6:])
        print(f"{event_data['type']}: {event_data}")
```

## Event Deduplication

Todos os eventos têm `event_id` único. Use para prevenir duplicatas:

```javascript
const seenEventIds = new Set();

function handleEvent(event) {
  if (seenEventIds.has(event.event_id)) {
    return; // Skip duplicate
  }
  seenEventIds.add(event.event_id);
  // Process event...
}
```

## Próximos Passos

- 🌐 [API Reference](api.md) - Endpoints que emitem eventos
- 💻 [Frontend](frontend.md) - Como processar eventos na UI
- 🏗️ [Architecture](architecture.md) - Sistema de eventos no backend
