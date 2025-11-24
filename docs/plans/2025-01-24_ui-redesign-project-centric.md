# Plano: UI Redesign - Project-Centric Workflow

**Nome:** UI Redesign - Project-Centric Workflow
**Descrição:** Reestruturar UI para foco em projetos, remover conceito de agente fixo, melhorar UX
**Data/Hora:** 2025-01-24 16:45
**Status:** Planejamento

---

## Contexto

Feedback do usuário sobre estado atual da aplicação identificou problemas conceituais e de UX:

### Problemas Identificados

1. **Rota confusa**: `/sessions/` deveria ser `/projects`
2. **Conceito de agente fixo errado**: Agentes devem ser dinâmicos, não escolhidos ao criar sessão
3. **Header pouco informativo**: Mostra ID técnico em vez de conteúdo relevante
4. **Painel lateral desorganizado**: Library com sub-abas, métricas muito proeminentes
5. **Falta contexto de atividades**: Não mostra atividades completas

---

## Objetivos

### 1. Mudança Conceitual: Dynamic Agents

**Antes:**
- Usuário escolhe agente ao criar sessão
- Agente fica "ativo" durante toda sessão

**Depois:**
- Sessão associada apenas a projeto
- Agentes são chamados e dispensados dinamicamente durante conversa
- Sistema orquestra automaticamente qual agente usar em cada momento

### 2. Reestruturação de Rotas

**Antes:**
```
/sessions/              → Lista de sessões
/sessions/chat.html     → Interface de chat
```

**Depois:**
```
/projects/              → Lista de projetos (com sessões por projeto)
/projects/{name}/chat   → Chat de uma sessão do projeto
```

### 3. UI Redesign: Project-Centric

**Foco principal:** Projeto → Atividades → Agentes são infraestrutura

---

## Implementação

### Fase 1: Mudanças no Backend

#### 1.1. Session Creation (Remover campo `agent_name`)

**Arquivo:** `collab_sims/api/routes/sessions.py`

**Mudanças:**
```python
# ANTES
@router.post("/sessions")
async def create_session(
    project_name: str,
    agent_name: str | None = None,  # ← REMOVER
    config: SessionConfig = None
):
    ...

# DEPOIS
@router.post("/sessions")
async def create_session(
    project_name: str,  # ← Obrigatório
    config: SessionConfig = None
):
    session_id = await session_manager.create_session(
        project_name=project_name,
        # Sem agent_name fixo
    )
```

#### 1.2. Session Metadata (Campo agent_name opcional/dinâmico)

**Arquivo:** `collab_sims/api/services/session_manager.py`

**Mudanças:**
```python
def _get_session_metadata(self, session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_data["session_id"],
        "project_name": session_data["project_name"],
        "current_agent": session_data.get("current_agent"),  # ← Dinâmico
        "session_name": session_data.get("session_name"),   # ← Primeiros 30 chars da 1ª msg
        "completed_activities": session_data.get("completed_activities", []),  # ← NOVO
        ...
    }
```

#### 1.3. Activity Tracking

**Novo arquivo:** `collab_sims/core/activity_tracker.py`

**Propósito:** Rastrear atividades executadas durante sessão

```python
class ActivityTracker:
    """Tracks completed activities in a session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.activities: list[CompletedActivity] = []

    def mark_activity_complete(
        self,
        activity_name: str,
        start_time: datetime,
        end_time: datetime,
        artifacts: list[str]
    ):
        """Mark an activity as completed."""
        self.activities.append(CompletedActivity(
            name=activity_name,
            start_time=start_time,
            end_time=end_time,
            artifacts=artifacts
        ))
```

#### 1.4. Dynamic Agent Selection

**Arquivo:** `collab_sims/core/agent_orchestrator.py` (NOVO)

**Propósito:** Decidir qual agente usar baseado no contexto

```python
class AgentOrchestrator:
    """Orchestrates which agent to use based on conversation context."""

    def select_agent(
        self,
        project: Project,
        current_activity: str | None,
        conversation_history: list[Message]
    ) -> Agent:
        """
        Select appropriate agent based on:
        - Current activity being executed
        - Conversation context
        - Project configuration
        """
        # Lógica para selecionar agente dinamicamente
        pass
```

---

### Fase 2: Mudanças no Frontend - Rotas

#### 2.1. Renomear Diretório

**Antes:**
```
web/sessions/
├── index.html   → Lista de sessões
└── chat.html    → Interface de chat
```

**Depois:**
```
web/projects/
├── index.html   → Lista de projetos (com sessões)
└── chat.html    → Interface de chat do projeto
```

#### 2.2. URL Structure

**Antes:**
- `http://localhost:3005/sessions/`
- `http://localhost:3005/sessions/chat.html?id={session_id}`

**Depois:**
- `http://localhost:3005/projects/`
- `http://localhost:3005/projects/chat.html?project={name}&session={id}`

---

### Fase 3: Mudanças no Frontend - Header

#### 3.1. Header Information

**Arquivo:** `web/projects/chat.html`

**Antes:**
```
Sessions | Sims Agent | 81ff2ec9 research-ux
```

**Depois:**
```
{project_name} | {current_activity or "Planning"} | "{first_30_chars_of_first_msg}"
```

**Exemplos:**
- `Research UX | Day 1: Understanding | "Let's start by understanding the..."`
- `Design Sprint | Planning | "Create a design sprint plan for..."`

#### 3.2. Session Name Generation

**Arquivo:** `web/js/handlers/eventHandlers.js`

**Lógica:**
```javascript
function handleFirstMessage(context, event) {
    if (event.role === 'user' && !context.sessionName) {
        // Gerar session_name dos primeiros 30 caracteres
        const sessionName = event.content.substring(0, 30).trim();

        // Atualizar no backend
        await api.updateSessionName(context.sessionId, sessionName);

        // Atualizar UI
        context.sessionName = sessionName;
        updateHeader();
    }
}
```

---

### Fase 4: Mudanças no Frontend - Projects List

#### 4.1. Projects View (antes Sessions List)

**Arquivo:** `web/projects/index.html`

**Layout:**
```
┌─────────────────────────────────────────────┐
│  Projects                                   │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  📊 Research UX                      │  │
│  │  3 sessions | 5 activities completed│  │
│  │  Last: "Let's analyze user..."       │  │
│  │  ────────────────────────────────    │  │
│  │  [View] [New Session]                │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  🎨 Design Sprint Q1                 │  │
│  │  1 session | 0 activities            │  │
│  │  Last: "Create a design sprint..."   │  │
│  │  ────────────────────────────────    │  │
│  │  [View] [New Session]                │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

**API Calls:**
```javascript
// GET /api/projects (com contagem de sessions e activities)
{
    "projects": [
        {
            "name": "research-ux",
            "display_name": "Research UX",
            "session_count": 3,
            "completed_activities": 5,
            "last_session": {
                "id": "...",
                "name": "Let's analyze user...",
                "created_at": "..."
            }
        }
    ]
}
```

---

### Fase 5: Mudanças no Frontend - Chat Sidebar

#### 5.1. Tab Reorganization

**Antes:**
```
Tabs:
├── Plan
├── Approvals
├── Metrics
├── Events
└── Library
    ├── Projects
    ├── Agents
    └── Activity Scripts
```

**Depois:**
```
Tabs:
├── Project      ← Era Library > Projects
├── Activities   ← Era Library > Activity Scripts
├── Agents       ← Era Library > Agents
├── Task         ← Era "Plan"
├── Approvals    ← Mantém
└── Events       ← Mantém

Bottom:
└── Metrics (compacto)
```

#### 5.2. Tab: Project

**Propósito:** Mostrar contexto do projeto e guia de processo

**Conteúdo:**
```
┌─────────────────────────────────┐
│  📊 Research UX                 │
│                                 │
│  ## Overview                    │
│  [Markdown content do projeto]  │
│                                 │
│  ## Process Guide               │
│  1. Discovery                   │
│  2. Analysis                    │
│  3. Synthesis                   │
│  4. Validation                  │
│                                 │
│  [Edit] [Save]                  │
└─────────────────────────────────┘
```

**Funcionalidade:**
- Renderizar markdown do projeto
- Permitir edição inline
- Salvar via PUT /api/library/projects/{name}

#### 5.3. Tab: Activities

**Propósito:** Ver e editar atividades (scripts e completadas)

**Conteúdo:**
```
┌─────────────────────────────────┐
│  Activities                     │
│                                 │
│  ## Completed ✓                 │
│  ▶ Day 1: Understanding  ━━━━   │
│    Completed: 2h ago            │
│                                 │
│  ## Available                   │
│  ▶ Day 2: Ideation              │
│  ▶ Day 3: Decision              │
│                                 │
│  [Click to view/edit]           │
└─────────────────────────────────┘
```

**Funcionalidade:**
- Listar atividades completadas (do tracking)
- Listar atividades disponíveis (da biblioteca)
- Ao clicar: abrir editor MD com conteúdo
- Salvar via PUT /api/library/activity-scripts/{name}

#### 5.4. Tab: Agents

**Propósito:** Ver e editar definições de agentes

**Conteúdo (atual está correto):**
```
┌─────────────────────────────────┐
│  Agents                         │
│                                 │
│  ▶ Facilitator                  │
│  ▶ Researcher                   │
│  ▶ Designer                     │
│                                 │
│  [Click to view/edit]           │
└─────────────────────────────────┘
```

**Mudança:**
- Ao clicar: abrir MD viewer/editor
- Mostrar conteúdo completo do agente
- Permitir edição inline
- Salvar via PUT /api/library/agents/{name}

#### 5.5. Tab: Task

**Propósito:** Task plan e progress (renomear de "Plan")

**Conteúdo (mantém atual):**
```
┌─────────────────────────────────┐
│  Task                           │
│                                 │
│  ✓ Understand problem           │
│  ▶ Generate ideas (in progress) │
│  ○ Validate solution            │
│                                 │
└─────────────────────────────────┘
```

**Mudança:** Apenas renomear aba de "Plan" para "Task"

#### 5.6. Metrics (Bottom, Compact)

**Layout:**
```
┌─────────────────────────────────┐
│  Metrics ▼                      │
│  ───────────────────────────    │
│  Tokens: 1.2K | Cost: $0.003   │
│  Duration: 2.5s | Turns: 3     │
└─────────────────────────────────┘
```

**Mudança:**
- Mover para parte inferior do sidebar
- Collapsible (fechado por padrão)
- Visual mais discreto

---

### Fase 6: Mudanças no Backend - API Extensions

#### 6.1. Projects Endpoint Enhancement

**Arquivo:** `collab_sims/api/routes/library.py`

**Novo endpoint:**
```python
@router.get("/api/projects/stats")
async def get_projects_with_stats():
    """Get all projects with session and activity counts."""
    projects = await library_service.list_projects()

    for project in projects:
        # Contar sessões
        project["session_count"] = await session_manager.count_sessions(
            project_name=project["name"]
        )

        # Contar atividades completadas
        project["completed_activities"] = await activity_tracker.count_completed(
            project_name=project["name"]
        )

        # Última sessão
        project["last_session"] = await session_manager.get_last_session(
            project_name=project["name"]
        )

    return {"projects": projects}
```

#### 6.2. Session Name Update

**Arquivo:** `collab_sims/api/routes/sessions.py`

**Novo endpoint:**
```python
@router.put("/api/sessions/{session_id}/name")
async def update_session_name(
    session_id: str,
    name: str = Body(..., embed=True)
):
    """Update session name (from first message)."""
    await session_manager.update_session_name(session_id, name)
    return {"session_id": session_id, "name": name}
```

---

## Checklist de Implementação

### Backend

- [ ] Remover `agent_name` obrigatório de session creation
- [ ] Adicionar `current_agent` dinâmico ao session metadata
- [ ] Implementar `ActivityTracker` para rastrear atividades completadas
- [ ] Criar `AgentOrchestrator` para seleção dinâmica de agentes
- [ ] Adicionar endpoint `GET /api/projects/stats`
- [ ] Adicionar endpoint `PUT /api/sessions/{id}/name`
- [ ] Atualizar testes para refletir mudanças

### Frontend - Estrutura

- [ ] Renomear `web/sessions/` para `web/projects/`
- [ ] Atualizar todas as referências de URL
- [ ] Atualizar `index.html` redirecionamento

### Frontend - Projects List

- [ ] Redesenhar `projects/index.html` para mostrar projetos
- [ ] Exibir contadores: "N sessions | X activities"
- [ ] Mostrar preview da última sessão
- [ ] Botões: [View] [New Session]

### Frontend - Chat Header

- [ ] Atualizar header para mostrar: `{project} | {activity} | {session_name}`
- [ ] Capturar primeira mensagem do usuário
- [ ] Gerar session_name dos primeiros 30 caracteres
- [ ] Enviar para backend via PUT /api/sessions/{id}/name

### Frontend - Sidebar Tabs

- [ ] Reorganizar tabs: Project, Activities, Agents, Task
- [ ] Remover conceito de "Library" com sub-tabs
- [ ] Mover Metrics para bottom (collapsible)

### Frontend - Tab: Project

- [ ] Implementar MD viewer/editor
- [ ] Carregar conteúdo via GET /api/library/projects/{name}
- [ ] Salvar via PUT /api/library/projects/{name}

### Frontend - Tab: Activities

- [ ] Listar atividades completadas (do tracking)
- [ ] Listar atividades disponíveis (da biblioteca)
- [ ] Implementar click → editor MD
- [ ] Salvar via PUT /api/library/activity-scripts/{name}

### Frontend - Tab: Agents

- [ ] Implementar click → MD viewer/editor
- [ ] Carregar conteúdo via GET /api/library/agents/{name}
- [ ] Salvar via PUT /api/library/agents/{name}

### Frontend - Tab: Task

- [ ] Renomear de "Plan" para "Task"
- [ ] Manter funcionalidade atual

### Frontend - Metrics

- [ ] Mover para bottom do sidebar
- [ ] Fazer collapsible (default: closed)
- [ ] Visual mais discreto

### Testing

- [ ] Atualizar smoke tests para novos endpoints
- [ ] Testar criação de sessão sem agent_name
- [ ] Testar geração de session_name
- [ ] Testar contadores de activities
- [ ] Teste exploratório da nova UI

### Documentation

- [ ] Atualizar docs/api.md com novos endpoints
- [ ] Atualizar docs/frontend.md com nova estrutura
- [ ] Atualizar docs/architecture.md com conceito de dynamic agents
- [ ] Adicionar diagramas de fluxo

---

## Riscos e Considerações

### 1. Breaking Changes

**Problema:** Mudanças incompatíveis com sessões existentes

**Solução:**
- Migration script para atualizar sessões antigas
- Suporte temporário para `agent_name` legado

### 2. Agent Selection Logic

**Problema:** Como decidir qual agente usar dinamicamente?

**Opções:**
- Baseado em palavras-chave na mensagem
- Baseado na atividade atual
- Prompt meta ao Claude para decidir
- Configuração no projeto

**Decisão:** TBD com mais contexto

### 3. UI Complexity

**Problema:** Editor MD inline pode ser complexo

**Solução:**
- Usar biblioteca existente (SimpleMDE, EasyMDE)
- Ou modal separado para edição

---

## Próximos Passos

1. **Revisar este plano** com usuário para validar abordagem
2. **Priorizar** fases (qual fazer primeiro?)
3. **Prototipar** mudanças de UI (wireframes?)
4. **Implementar** incrementalmente
5. **Testar** cada fase antes de prosseguir

---

## Referências

- Imagem anexada: Guia de processo (ideação → especificação → desenvolvimento → homologação)
- Feedback original do usuário (2025-01-24)
- Documentação atual: docs/architecture.md, docs/api.md, docs/frontend.md
