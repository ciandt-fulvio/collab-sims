---
name: design-criteria
description: Dinâmica colaborativa onde todos os agentes sugerem critérios de design (MUST: 1-10 itens, SHOULD: 0-5 itens, DONT: 1-5 itens) para um contexto específico de SRE
---

Dinâmica colaborativa onde todos os agentes sugerem critérios de design (MUST: 1-10 itens, SHOULD: 0-5 itens, DONT: 1-5 itens) para um contexto específico de SRE.

Coordinate with the team agents to produce the required outputs.

## Workflow

Follow this sequence:

### Pre-requisite
- Descubra qual dia é hoje e **Crie um timestamp** no formato DDMMYY_HHMMSS

### Phase 1: Parallel Agent Execution

Each agent should independently analyze the context and propose their design criteria.

**Format for each agent:**

```markdown
## [Agent Name] - Design Criteria

### MUST (1-10 items)
- Critical requirements that cannot be compromised
- ...

### SHOULD (0-5 items)
- Important but negotiable requirements
- ...

### DON'T (1-5 items)
- Anti-patterns to avoid
- ...
```

### Phase 2: Consolidation

After all agents have contributed:
1. Identify common patterns across agents
2. Resolve conflicts or disagreements
3. Synthesize final unified criteria list

### Output

Save the consolidated design criteria in markdown format with timestamp.
