# Reestruturação do Filesystem - Execution

**Data:** 2025-11-25
**Objetivo:** Reestruturar organização de arquivos de execution para agrupar projeto e seus resultados

## Situação Atual

```
data/
├── execution/
│   ├── projects/
│   │   ├── design-sprint-q1.md
│   │   ├── criando-projeto.md
│   │   └── research-ux.md
│   ├── activity_results/
│   │   └── design-sprint-q1/
│   │       ├── how-might-we_v1.md
│   │       ├── how-might-we_v2.md
│   │       └── design-criteria_v1.md
│   └── agents/  ← DUPLICADO (deveria estar apenas em definition/)
│       ├── andre-dev-resistente.md
│       ├── facilitator.md
│       └── researcher.md
└── definition/
    └── agents/  ← LOCALIZAÇÃO CORRETA
        ├── andre-dev-resistente.md
        ├── facilitator.md
        └── researcher.md
```

## Estrutura Desejada

```
data/
├── execution/
│   └── projects/
│       ├── design-sprint-q1/
│       │   ├── design-sprint-q1.md
│       │   ├── how-might-we_v1.md
│       │   ├── how-might-we_v2.md
│       │   └── design-criteria_v1.md
│       ├── criando-projeto/
│       │   └── criando-projeto.md
│       └── research-ux/
│           └── research-ux.md
└── definition/
    └── agents/
        ├── andre-dev-resistente.md
        ├── facilitator.md
        └── researcher.md
```

## Mudanças Necessárias

### 1. Agents (já está correto no código)

- **AgentLoader** já usa `data/definition/agents` (✅ correto)
- **Ação:** Remover `data/execution/agents/` (diretório duplicado)

### 2. Projects e Activity Results

#### 2.1 ProjectLoader
- **Atual:** `data/execution/projects/{project_name}.md`
- **Novo:** `data/execution/projects/{project_name}/{project_name}.md`

**Mudanças:**
- `__init__`: base_path permanece `data/execution/projects`
- `list_projects()`: buscar em `**/*.md` ao invés de `*.md`
- `get_project(name)`: buscar em `{name}/{name}.md`
- `save_project(name, content)`: salvar em `{name}/{name}.md`

#### 2.2 ActivityResultLoader
- **Atual:** `data/execution/activity_results/{project_name}/{file}.md`
- **Novo:** `data/execution/projects/{project_name}/{file}.md`

**Mudanças:**
- `__init__`: mudar base_path de `data/execution/activity_results` para `data/execution/projects`
- `list_activity_results(project_name)`: buscar em `{project_name}/*.md` excluindo `{project_name}.md`
- `get_activity_result(project_name, name)`: mesma lógica, novo caminho
- `save_*()`: mesma lógica, novo caminho

### 3. Routes Afetadas

- `collab_sims/api/routes/documents.py` - usa ActivityResultLoader
- `collab_sims/api/routes/library.py` - usa ProjectLoader

### 4. Testes Afetados

#### Testes Unitários:
- `tests/unit/core/loaders/test_project_loader.py`
- `tests/unit/core/loaders/test_activity_result_loader.py`

#### Testes de Integração:
- `tests/integration/test_documents_api.py`

## Plano de Execução

### Fase 1: Remover duplicação de agents ✅
1. Verificar que AgentLoader usa `data/definition/agents`
2. Remover diretório `data/execution/agents/`

### Fase 2: Migrar arquivos físicos
1. Criar nova estrutura de diretórios
2. Mover arquivos de projetos para subdiretórios
3. Mover activity_results para dentro dos diretórios de projetos
4. Remover diretórios antigos vazios

### Fase 3: Atualizar código
1. Atualizar `ProjectLoader`
2. Atualizar `ActivityResultLoader`
3. Verificar routes da API

### Fase 4: Atualizar testes
1. Atualizar testes unitários do ProjectLoader
2. Atualizar testes unitários do ActivityResultLoader
3. Atualizar testes de integração

### Fase 5: Validação
1. Executar testes unitários
2. Executar testes de integração
3. Validar manualmente via API/Web UI
4. Commit das mudanças

## Riscos e Mitigações

**Risco 1:** Perda de dados durante migração
- **Mitigação:** Fazer backup antes, usar git para rastrear mudanças

**Risco 2:** Quebra de compatibilidade com dados existentes
- **Mitigação:** Manter estrutura de metadados nos arquivos markdown inalterada

**Risco 3:** Testes podem falhar após mudança
- **Mitigação:** Atualizar todos os testes antes de validar

## Notas

- Não há necessidade de migração de dados de produção (ainda em desenvolvimento)
- Mudanças são backwards-incompatible (estrutura de diretórios diferente)
- Frontend não precisa de mudanças (usa API abstraída pelos loaders)
