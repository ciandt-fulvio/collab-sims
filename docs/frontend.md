# Frontend Web

Interface web moderna construída com Alpine.js para monitorar e interagir com agentes Claude em tempo real.

## Stack Tecnológico

- **Alpine.js 3** - Framework reativo (15KB, sem build step)
  - **Plugins**: Collapse (`@alpinejs/collapse@3`)
- **Tailwind CSS** - Utility-first CSS (via CDN)
- **Vanilla JavaScript** - ES6 modules nativos
- **Server-Sent Events (SSE)** - Streaming em tempo real
- **Vitest** - Testing framework

## Características

### ✨ Features Principais

- 🔄 **Gerenciamento de Sessões** - Criar, listar e deletar sessões
- 💬 **Chat Interface** - Conversas com streaming de texto
- 🔤 **Word-by-Word Streaming** - Texto aparece incrementalmente
- ✅ **Tool Approval** - Aprovar/rejeitar ferramentas em tempo real
- 🛠️ **Tool Monitoring** - Ver todas as execuções de ferramentas
- 📋 **Task Plans** - Visualização de planos e progresso
- 📊 **Metrics** - Custos e tokens em tempo real
- 📝 **Event Log** - Histórico completo de eventos
- 🎨 **Dark Mode** - Tema claro/escuro

### 🚫 No Build Step Required

- Código ES6 modules roda direto no browser
- Sem transpilação, bundling ou webpack
- Desenvolvimento instantâneo (F5 para recarregar)
- Deploy simples (copiar arquivos)

## Arquitetura

### Estrutura de Diretórios

```
web/
├── index.html              # Redirect para /sessions/
├── sessions/
│   ├── index.html          # Lista de sessões
│   └── chat.html           # Interface de chat
├── js/
│   ├── alpine-bootstrap.js # Entry point - carrega Alpine
│   ├── components/
│   │   ├── app.js          # Componente principal (simsApp)
│   │   ├── chat/           # Painéis do chat
│   │   │   ├── metricsPanel.js
│   │   │   ├── planPanel.js
│   │   │   ├── eventsPanel.js
│   │   │   └── approvalsPanel.js
│   │   └── sessions/
│   │       └── sessionsListComponent.js
│   ├── services/
│   │   └── api.js          # SimsAPI client + SSE handler
│   ├── handlers/
│   │   └── eventHandlers.js # Roteamento de eventos
│   ├── state/
│   │   └── sessionState.js  # Gerenciamento de estado
│   └── utils/
│       ├── rendering.js     # Markdown, HTML
│       ├── toolFormatters.js # Formatadores de tools
│       └── theme.js         # Dark/light mode
├── css/
│   └── styles.css          # Custom styles
└── __tests__/              # Testes Vitest
    └── ...
```

### Component Composition

O componente principal usa composição para combinar painéis:

```javascript
// app.js
export function simsApp() {
  return {
    ...metricsPanel(),    // Estado e métodos de métricas
    ...planPanel(),       // Estado e métodos de plano
    ...eventsPanel(),     // Estado e métodos de eventos
    ...approvalsPanel(),  // Estado e métodos de aprovações
    // ... estado próprio
  };
}
```

Registrado com Alpine:

```javascript
// alpine-bootstrap.js
Alpine.data('simsApp', simsApp);
```

Usado no HTML:

```html
<div x-data="simsApp()" x-init="init()">
  <!-- Bindings Alpine aqui -->
</div>
```

## Fluxo de Dados

### 1. Inicialização

```
1. User acessa /sessions/chat.html?id=123
2. Alpine.js carrega simsApp()
3. init() verifica ID na URL
4. loadSession() busca dados: GET /api/sessions/123
5. Carrega eventos históricos: GET /api/sessions/123/events
6. Reconstrói estado processando eventos
7. Se sessão ativa, reconecta SSE
```

### 2. Enviando Mensagem

```
User digita mensagem → sendMessage()
   ↓
POST /api/sessions/{id}/query/stream
   ↓
Backend retorna SSE stream
   ↓
EventStreamHandler recebe eventos
   ↓
handleEvent() processa cada evento
   ↓
dispatchEvent() roteia para handler específico
   ↓
Handler atualiza estado do componente
   ↓
Alpine.js reage e atualiza UI
```

### 3. Processamento de Eventos

```javascript
// eventHandlers.js
export function dispatchEvent(context, event) {
  const handlers = {
    'query': handleQueryEvent,
    'message': handleMessageEvent,
    'partial_message': handlePartialMessageEvent,
    'tool_use': handleToolUseEvent,
    'tool_result': handleToolResultEvent,
    'plan': handlePlanEvent,
    'approval_request': handleApprovalRequestEvent,
    'complete': handleCompleteEvent,
  };

  const handler = handlers[event.type];
  if (handler) {
    handler(context, event);
  }
}
```

## Componentes Principais

### SimsAPI Client

Cliente HTTP para comunicação com backend:

```javascript
import { SimsAPI } from './services/api.js';

const api = new SimsAPI();

// Criar sessão
const session = await api.createSession({
  include_partial_messages: true
}, 'worker');

// Enviar query com streaming
const stream = api.createEventStream(sessionId, prompt);
stream
  .on('message', (event) => console.log(event))
  .on('error', (error) => console.error(error))
  .on('end', () => console.log('Stream ended'));
await stream.start();
```

### EventStreamHandler

Consome Server-Sent Events:

```javascript
export class EventStreamHandler {
  constructor(url, options) {
    this.url = url;
    this.options = options;
    this.handlers = {};
  }

  async start() {
    const response = await fetch(this.url, this.options);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    // Read SSE stream line by line
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      // Parse "data: {json}\n\n" format
      // Emit events to handlers
    }
  }

  on(eventType, handler) {
    this.handlers[eventType] = handler;
    return this;
  }
}
```

### Tool Grouping

Ferramentas são agrupadas por turno (round-trip):

```javascript
// Tool group structure
{
  id: "group-uuid",
  messageId: "message-uuid",
  tools: [
    {
      use: {tool_name: "Write", input: {...}},
      result: {output: "File created", is_error: false}
    }
  ],
  timestamp: "2025-01-18T10:30:00",
  expanded: false  // UI state
}
```

Benefícios:
- Agrupa ferramentas relacionadas
- UI mais limpa e organizada
- Facilita collapse/expand

### Metrics Tracking

Métricas são estimadas durante streaming e atualizadas com valores exatos:

```javascript
// Durante streaming (estimativas)
function estimateTokens(text) {
  return Math.ceil(text.length / 4);
}

// No evento 'complete' (valores exatos)
handleCompleteEvent(context, event) {
  context.metrics.inputTokens = event.usage.input_tokens;
  context.metrics.outputTokens = event.usage.output_tokens;
  context.metrics.totalCost = event.total_cost_usd;
}
```

## Features Específicas

### Dark Mode

```javascript
// utils/theme.js
export function initTheme() {
  const saved = localStorage.getItem('theme');
  if (saved) return saved;

  // Auto-detect system preference
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';
}

export function toggleTheme() {
  const current = document.documentElement.classList.contains('dark')
    ? 'dark'
    : 'light';
  const next = current === 'dark' ? 'light' : 'dark';

  document.documentElement.classList.toggle('dark', next === 'dark');
  localStorage.setItem('theme', next);
  return next;
}
```

### Markdown Rendering

```javascript
// utils/rendering.js
export function renderMarkdown(text) {
  // Uses marked.js (loaded via CDN)
  const html = marked.parse(text);

  // Sanitize (basic XSS protection)
  return html.replace(/<script/gi, '&lt;script');
}
```

### Tool Formatters

Formatadores específicos para cada ferramenta:

```javascript
// utils/toolFormatters.js
const ToolInputFormatters = {
  Bash(input) {
    const command = input.command;
    return `<div class="font-mono">
      <span class="text-blue-600">$</span> ${escapeHtml(command)}
    </div>`;
  },

  Write(input) {
    const lines = input.content.split('\n').length;
    return `<div>
      📝 ${input.file_path} <span class="text-xs">(${lines} lines)</span>
    </div>`;
  },
  // ... outros formatadores
};
```

## Event Deduplication

Previne eventos duplicados usando `event_id`:

```javascript
// app.js
handleEvent(event) {
  const eventId = event.event_id || generateFallbackId();

  if (this.seenEventIds.has(eventId)) {
    return; // Skip duplicate
  }
  this.seenEventIds.add(eventId);

  // Process event...
}
```

## Session Restoration

Ao carregar sessão existente:

```javascript
async loadSession(sessionId) {
  // 1. Buscar dados da sessão
  const session = await api.getSession(sessionId);

  // 2. Buscar eventos históricos
  const events = await api.getSessionEvents(sessionId);

  // 3. Flag para evitar animações duplicadas
  this.isLoadingHistory = true;

  // 4. Processar eventos para reconstruir estado
  events.forEach(event => dispatchEvent(this, event));

  // 5. Limpar flag
  this.isLoadingHistory = false;

  // 6. Se sessão ativa, reconectar SSE
  if (isActiveQuery(events)) {
    this.reconnectToActiveSession();
  }
}
```

## Approval UI

Quando ferramenta requer aprovação:

```javascript
handleApprovalRequestEvent(context, event) {
  context.pendingApprovals.push({
    tool_use_id: event.tool_use_id,
    tool_name: event.tool_name,
    tool_input: event.tool_input,
    risk_level: event.risk_level,
    status: 'pending'
  });

  // Auto-switch to Approvals tab
  context.activeTab = 'approvals';
}
```

UI mostra:
- Nome da ferramenta
- Risk level (badge colorido)
- Input parameters
- Botões: Approve, Approve & Remember, Reject

## Testing

### Vitest Setup

```javascript
// vitest.config.js
export default {
  test: {
    environment: 'happy-dom',  // Simula DOM sem browser
    globals: true
  }
};
```

### Exemplo de Teste

```javascript
// __tests__/utils/toolFormatters.test.js
import { describe, it, expect } from 'vitest';
import { formatToolInput } from '../../utils/toolFormatters.js';

describe('formatToolInput', () => {
  it('should format Bash tool input', () => {
    const result = formatToolInput('Bash', {
      command: 'ls -la'
    });

    expect(result).toContain('$');
    expect(result).toContain('ls -la');
  });
});
```

Rodar testes:

```bash
cd web
npm test
```

## CORS Configuration

Frontend roda em porta diferente da API:

```javascript
// api.js
const API_BASE_URL = window.location.hostname === 'localhost'
  ? 'http://localhost:3007'
  : 'https://api.yourapp.com';
```

Backend deve permitir CORS:

```python
# collab_sims/api/middleware/cors.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3005"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Performance

### Otimizações

1. **ES6 Modules Nativos**: Carregamento paralelo pelo browser
2. **Event Deduplication**: Evita re-renders desnecessários
3. **Virtual Scrolling**: Para listas longas de eventos (futuro)
4. **Lazy Loading**: Componentes carregados sob demanda

### Limitações

- **Não otimizado para IE11** (ES6 modules required)
- **SSE não funciona em HTTP/2 multiplexing** (use HTTP/1.1)

## Deployment

### Desenvolvimento

```bash
cd web
python3 -m http.server 3005
```

### Produção (Opção 1: CDN Estático)

Deploy para Vercel, Netlify, ou GitHub Pages:

```bash
# Atualizar API_BASE_URL em api.js
const API_BASE_URL = 'https://api.yourapp.com';

# Deploy
vercel deploy
```

### Produção (Opção 2: Servir do FastAPI)

```python
# collab_sims/api/main.py
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="web", html=True), name="web")
```

Benefícios:
- Mesmo domínio (sem CORS)
- Single deployment
- Mais simples

## Browser Compatibility

Requer browsers modernos com ES6 modules:

- Chrome 61+
- Firefox 60+
- Safari 11+
- Edge 16+

**Não suportado:**
- Internet Explorer (qualquer versão)
- Chrome < 61
- Safari < 11

## Troubleshooting

### Página em branco / Alpine.js não carrega

**Sintoma:** Página completamente branca, sem conteúdo visível

**Causa comum:** Import incorreto de plugins Alpine.js

**Solução:** Verificar imports de plugins Alpine.js:

```javascript
// ❌ INCORRETO - causa página em branco
import collapse from 'https://cdn.jsdelivr.net/npm/@alpinejs/collapse@3/dist/cdn.min.js';

// ✅ CORRETO - use o módulo ES6
import Collapse from 'https://cdn.jsdelivr.net/npm/@alpinejs/collapse@3/dist/module.esm.js';
Alpine.plugin(Collapse);
```

**Regra geral:**
- Sempre use `/dist/module.esm.js` para plugins Alpine.js em ES6 modules
- Plugin deve ser registrado com nome capitalizado via `Alpine.plugin()`
- Imports devem vir **antes** de `Alpine.start()`

### Eventos não aparecem

1. Verificar Network tab (DevTools)
2. Procurar por conexão SSE ativa
3. Verificar se eventos estão chegando
4. Verificar console por erros JavaScript

### CORS errors

1. Confirmar API rodando em `localhost:3007`
2. Confirmar frontend em `localhost:3005`
3. Verificar middleware CORS no backend

### Library tab vazio

**Sintoma:** "No agents available" ou "No activity scripts available"

**Causas possíveis:**
1. **URL incorreta:** Usar `activity_scripts` (underscore) em vez de `activity-scripts` (hyphen)
2. **Falta de `/api` prefix:** Backend retorna 404

**Solução:**
```javascript
// ✅ CORRETO
const response = await fetch('http://localhost:3007/api/library/activity-scripts');

// ❌ INCORRETO
const response = await fetch('http://localhost:3007/library/activity_scripts');
```

### Dark mode não funciona

1. Limpar localStorage: `localStorage.clear()`
2. Recarregar página

## Próximos Passos

- 📡 [Events Reference](events.md) - Entender eventos SSE
- 🌐 [API Reference](api.md) - Endpoints disponíveis
- 🏗️ [Architecture](architecture.md) - Backend architecture
