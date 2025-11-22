# CollabSims

AI Agent Collaboration Simulator - Plataforma web para executar e monitorar agentes Claude.

## Instalação

### Requisitos

- Python 3.13+
- pip ou uv (recomendado)

### Instalar Dependências

**Opção 1: Usando pip**
```bash
pip install -e .
```

**Opção 2: Usando uv (recomendado)**
```bash
# Instalar uv (se ainda não tiver)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Instalar dependências
uv pip install -e .
```

### Dependências de Desenvolvimento

```bash
pip install -e ".[dev]"
```

## Iniciando o Projeto

### Método 1: Scripts de Inicialização

**Iniciar API (Terminal 1):**
```bash
./run_api.sh
```
- API disponível em: `http://localhost:3007`
- Documentação em: `http://localhost:3007/docs`

**Iniciar Frontend (Terminal 2):**
```bash
./run_web.sh
```
- Interface web em: `http://localhost:3005`

## Testando

### ⚡ Testes Rápidos (Recomendado)

```bash
# Testes unitários super rápidos (< 1s)
pytest -m unit -n auto

# Todos os testes em paralelo (~4x mais rápido)
pytest -n auto

# Ver detalhes em: tests/README.md
```

### Executar Todos os Testes

```bash
# Serial (lento)
pytest

# Paralelo (RECOMENDADO - 4x mais rápido)
pytest -n auto
```

### Executar com Cobertura

```bash
# Terminal (rápido)
pytest --cov=collab_sims --cov-report=term-missing -n auto

# HTML (navegável)
pytest --cov=collab_sims --cov-report=html -n auto
open htmlcov/index.html
```

### Reports de Testes que Falharam

```bash
# Re-executar apenas testes que falharam
pytest --lf -n auto

# Traceback detalhado + variáveis locais
pytest --lf -vv --tb=long --showlocals

# HTML report
pytest --html=report.html --self-contained-html
open report.html
```

### Executar Teste Específico

```bash
pytest tests/unit/core/test_events.py::TestEventTypeEnum::test_event_type_values
```

### Testes do Frontend (Vitest)

```bash
cd web
npm install  # Primeira vez apenas
npm test
```

## Linting e Formatação

### Verificar Código

```bash
ruff check .
```

### Formatar Código

```bash
ruff format .
```

### Fix Automático

```bash
ruff check --fix .
```

## Verificação de Saúde

Após iniciar a API, verifique se está funcionando:

```bash
curl http://localhost:3007/health
```

Resposta esperada:
```json
{"status": "healthy", "service": "collab-sims-api"}
```

## Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto (opcional):

```env
# Porta da API (padrão: 3007)
PORT=3007

# Caminho do banco de dados (padrão: ./data/sessions.db)
DATABASE_PATH=./data/sessions.db

# Nível de log (padrão: INFO)
LOG_LEVEL=DEBUG
```

## Estrutura de Diretórios

```
collab-sims/
├── collab_sims/          # Código Python
│   ├── api/              # FastAPI application
│   ├── core/             # Lógica de negócio
│   ├── persistence/      # Camada de persistência
│   └── trackers/         # Event tracking
├── web/                  # Frontend web
│   ├── js/               # JavaScript modules
│   ├── css/              # Estilos
│   └── sessions/         # Páginas HTML
├── docs/                 # Documentação
├── tests/                # Testes Python
└── data/                 # Banco de dados SQLite (gerado)
```

## Uso Rápido

1. **Criar uma sessão:**
   - Acesse `http://localhost:3005`
   - Clique em "New Session"
   - Escolha "Worker" ou "Scout"

2. **Enviar mensagem:**
   - Digite sua pergunta/tarefa
   - Pressione Enter ou clique em "Send"

3. **Monitorar execução:**
   - Veja eventos em tempo real
   - Aprove/rejeite ferramentas (se necessário)
   - Acompanhe métricas e custos

## Solução de Problemas

### API não inicia

```bash
# Verificar se aiosqlite está instalado
pip install aiosqlite

# Verificar portas em uso
lsof -i :3007
```

### Frontend não carrega

```bash
# Verificar se está no diretório correto
cd web
pwd  # Deve mostrar: .../collab-sims/web

# Tentar porta diferente
python3 -m http.server 8080
```

### CORS errors

Certifique-se de que:
- API está rodando em `localhost:3007`
- Frontend está rodando em `localhost:3005`
- Ambos estão acessíveis via `http://` (não `https://`)

## Próximos Passos

- 📖 Leia a [Documentação da API](docs/api.md)
- 🏗️ Entenda a [Arquitetura](docs/architecture.md)
- 📡 Explore os [Eventos](docs/events.md)
- 💻 Customize o [Frontend](docs/frontend.md)

## Suporte

- **Issues**: [GitHub Issues](https://github.com/seu-usuario/collab-sims/issues)
- **Documentação**: [docs/](docs/)
- **API Docs**: http://localhost:3007/docs (quando rodando)
