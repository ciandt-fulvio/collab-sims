# CollabSims

**AI Agent Collaboration Simulator** - Web UI para monitorar e interagir com agentes Claude em tempo real.

## Visão Geral

CollabSims é uma plataforma completa para executar e monitorar agentes de IA Claude, oferecendo:

- 🎯 **Execução Single-Turn**: Execute tarefas únicas com resposta imediata
- 💬 **Sessões Multi-Turn**: Conversas persistentes com contexto mantido
- ✅ **Aprovação de Ferramentas**: Controle granular sobre execução de ferramentas
- 📊 **Monitoramento em Tempo Real**: Interface web com streaming SSE
- 💾 **Persistência**: Histórico completo em SQLite
- 🔧 **API REST**: FastAPI com documentação automática

## Stack Tecnológico

**Backend:**
- Python 3.13+
- FastAPI + Uvicorn
- Claude Agent SDK
- SQLite (aiosqlite)

**Frontend:**
- Alpine.js 3
- Tailwind CSS
- Vanilla JavaScript (ES6 modules)
- Server-Sent Events (SSE)

## Documentação

### Primeiros Passos
- 📘 [README.md](README.md) - Instalação, testes e inicialização

### Arquitetura e Componentes
- 🏗️ [Arquitetura](docs/architecture.md) - Visão de alto nível do sistema
- 🗄️ [Banco de Dados](docs/database.md) - Esquema e estruturas de tabelas
- 🌐 [API](docs/api.md) - Endpoints e exemplos de uso
- 📡 [Eventos](docs/events.md) - Sistema de eventos e streaming
- 💻 [Frontend Web](docs/frontend.md) - Interface e componentes

## Início Rápido

```bash
# 1. Instalar dependências
pip install -e .

# 2. Iniciar API (Terminal 1)
./run_api.sh

# 3. Iniciar Frontend (Terminal 2)
./run_web.sh
```

**Acesse:** http://localhost:3005

## Estrutura do Projeto

```
/Users/fulvio/Projects/collab-sims/
├── collab_sims/          # Backend Python
│   ├── api/              # FastAPI routes e services
│   ├── core/             # Lógica principal (Agent, Session)
│   ├── persistence/      # SQLite repository
│   └── trackers/         # Event tracking
├── web/                  # Frontend (Alpine.js)
│   ├── js/               # Componentes e serviços
│   └── sessions/         # Páginas HTML
└── docs/                 # Documentação detalhada
```

## Contribuindo

Este projeto usa:
- **Gerenciamento de pacotes**: `pip` ou `uv`
- **Linting**: `ruff`
- **Testes**: `pytest`
- **Formatação**: `ruff format`

Veja [README.md](README.md) para comandos completos.

---

## Regras fundamentais:

- Sempre que vc fizer um plano, guarde ele de forma que eu possa consultar depois. Ele deve ser armazenado em <project_dir>/docs/plans com um arquivo markdown com o formato YYYYMMDD_nome_curto.md 
- Sempre que uma nova funcionalidade for adicionada, crie testes automatizados para ela, prefira sempre os testes unitários, quando não for possível, crie testes de integração
- Sempre que um bug for corrigido, crie um teste que reproduza o bug e depois corrija o bug
- Quando vc terminar todos os commits de uma serie de pedidos, faça um push. Faça um teste de integração antes de um push (pytest -n auto)
- use o script ./manage_servers.sh para iniciar e parar os servidores, evite os scripts ./run_*.sh
- NUNCA altere um teste automatizado sem antes me consultar, voce pode incluir novos testes, mas nunca alterar ou excluir os existentes sem minha autorização

