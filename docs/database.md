# Database Schema

CollabSims usa SQLite para persistência de sessões e eventos.

## Visão Geral

- **Database**: SQLite 3
- **Driver**: aiosqlite (async)
- **Location**: `./data/sessions.db` (padrão)
- **Migrations**: Schema automático na inicialização

## Tabelas

### `session`

Armazena informações de sessões multi-turn.

| Coluna | Tipo | Constraints | Descrição |
|--------|------|-------------|-----------|
| `session_id` | TEXT | PRIMARY KEY | ID único da sessão (UUID) |
| `user_id` | TEXT | NULL | ID do usuário (futuro uso) |
| `created_at` | TIMESTAMP | NOT NULL | Data/hora de criação |
| `closed_at` | TIMESTAMP | NULL | Data/hora de encerramento |
| `status` | TEXT | NOT NULL, CHECK | Status: 'active', 'closed', 'error' |
| `query_count` | INTEGER | DEFAULT 0 | Número de queries executadas |
| `metadata` | TEXT | NULL | JSON com metadados adicionais |

**Índices:**
- `idx_session_user_id` - Busca por usuário
- `idx_session_created_at` - Ordenação temporal
- `idx_session_status` - Filtro por status

**Exemplo de registro:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": null,
  "created_at": "2025-01-18T10:30:00",
  "closed_at": null,
  "status": "active",
  "query_count": 3,
  "metadata": "{\"role\": \"worker\", \"tags\": [\"development\"]}"
}
```

### `event`

Armazena todos os eventos de execução de agentes.

| Coluna | Tipo | Constraints | Descrição |
|--------|------|-------------|-----------|
| `event_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | ID sequencial do evento |
| `session_id` | TEXT | NOT NULL, FOREIGN KEY | Referência à sessão |
| `event_type` | TEXT | NOT NULL | Tipo do evento (query, message, tool_use, etc.) |
| `timestamp` | TIMESTAMP | NOT NULL | Data/hora do evento |
| `query_index` | INTEGER | NULL | Índice da query na sessão |
| `message_id` | TEXT | NULL | ID da mensagem (para eventos relacionados) |
| `data` | TEXT | NOT NULL | JSON com dados completos do evento |

**Índices:**
- `idx_event_session_id` - Busca por sessão
- `idx_event_event_type` - Filtro por tipo
- `idx_event_timestamp` - Ordenação temporal
- `idx_event_query_index` - Busca por query específica

**Exemplo de registro:**
```json
{
  "event_id": 1,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "message",
  "timestamp": "2025-01-18T10:30:05",
  "query_index": 1,
  "message_id": "msg_001",
  "data": "{\"role\": \"assistant\", \"content\": \"I'll help you with that.\", \"model\": \"claude-3-5-sonnet-20250122\"}"
}
```

## Relacionamentos

```
session (1) ──────< (N) event
  │                    │
  │                    │
  └──── ON DELETE CASCADE
```

- Uma sessão pode ter múltiplos eventos
- Eventos são deletados automaticamente quando a sessão é removida (CASCADE)

## Queries Comuns

### Buscar sessão com contagem de eventos

```sql
SELECT
  s.session_id,
  s.created_at,
  s.status,
  s.query_count,
  COUNT(e.event_id) as total_events
FROM session s
LEFT JOIN event e ON s.session_id = e.session_id
WHERE s.session_id = ?
GROUP BY s.session_id;
```

### Buscar eventos de uma query específica

```sql
SELECT
  event_id,
  event_type,
  timestamp,
  data
FROM event
WHERE session_id = ? AND query_index = ?
ORDER BY timestamp ASC;
```

### Buscar eventos por tipo

```sql
SELECT
  event_id,
  timestamp,
  data
FROM event
WHERE session_id = ? AND event_type IN ('tool_use', 'tool_result')
ORDER BY timestamp ASC;
```

### Listar sessões ativas

```sql
SELECT
  session_id,
  created_at,
  query_count
FROM session
WHERE status = 'active'
ORDER BY created_at DESC;
```

## Performance

### Estratégias de Otimização

1. **Índices Compostos**: Query index + session_id para queries complexas
2. **VACUUM**: Executar periodicamente para reclamar espaço
3. **ANALYZE**: Atualizar estatísticas para melhor query planning
4. **Connection Pooling**: aiosqlite mantém conexões abertas

### Tamanho Esperado

- **Sessão**: ~200 bytes
- **Evento médio**: ~500 bytes
- **Sessão completa (50 eventos)**: ~25 KB
- **1000 sessões**: ~25 MB

## Backup e Recuperação

### Backup Manual

```bash
sqlite3 data/sessions.db ".backup 'backup.db'"
```

### Backup Automático (Python)

```python
import shutil
shutil.copy('data/sessions.db', f'backup_{datetime.now().isoformat()}.db')
```

### Restauração

```bash
cp backup.db data/sessions.db
```

## Migrations

### Schema Atual: v1

Criado automaticamente em `collab_sims/persistence/sqlite_repository.py`:

```python
async def initialize(self):
    schema_path = Path(__file__).parent / "schema.sql"
    schema = schema_path.read_text()
    await self.db.executescript(schema)
    await self.db.commit()
```

### Futuras Migrations

Quando necessário adicionar tabelas/colunas:

1. Criar arquivo `schema_v2.sql`
2. Adicionar lógica de versioning
3. Aplicar migrations incrementalmente

## Ferramentas

### SQLite CLI

```bash
# Abrir database
sqlite3 data/sessions.db

# Ver schema
.schema

# Listar tabelas
.tables

# Ver registros
SELECT * FROM session LIMIT 10;
```

### DB Browser for SQLite

GUI gratuita: https://sqlitebrowser.org/

### Python (aiosqlite)

```python
import aiosqlite

async def query_sessions():
    async with aiosqlite.connect('data/sessions.db') as db:
        async with db.execute('SELECT * FROM session') as cursor:
            async for row in cursor:
                print(row)
```

## Integridade de Dados

### Constraints

- **Foreign Keys**: Habilitadas (`PRAGMA foreign_keys = ON`)
- **CHECK Constraints**: Status válidos apenas
- **NOT NULL**: Campos obrigatórios protegidos

### Transações

Todas as operações de escrita usam transações:

```python
async with db.execute(...) as cursor:
    # Operações
await db.commit()  # Ou rollback em caso de erro
```

## Troubleshooting

### Database Locked

```bash
# Verificar processos usando o arquivo
lsof data/sessions.db

# Fechar conexões ociosas
sqlite3 data/sessions.db "PRAGMA optimize"
```

### Corrupção

```bash
# Verificar integridade
sqlite3 data/sessions.db "PRAGMA integrity_check"

# Reparar (se possível)
sqlite3 data/sessions.db ".recover" | sqlite3 recovered.db
```

## Referências

- [SQLite Documentation](https://sqlite.org/docs.html)
- [aiosqlite](https://aiosqlite.omnilib.dev/)
- [SQL Schema](../collab_sims/persistence/schema.sql)
