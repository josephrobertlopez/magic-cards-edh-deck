# Skills vs MCP: Architectural Analysis

**Date:** 2025-11-14
**Method:** Reflexion-style debate (5 rounds)
**Status:** Converged (Round 4/5, Score: 9/10)

---

## Executive Summary

Skills and MCP protocols serve **complementary architectural layers**, not competing systems. Skills provide unique capabilities (prompt injection, workflow composition) that MCP cannot replicate, while MCP provides stateful multi-agent orchestration that Skills don't need.

**Decision:** Use both, based on capability requirements.

---

## Skills: Dual-Mode Architecture

### Mode 1: Behavioral Transformers (Prompt Injection)
**Unique capability - MCP cannot replicate!**

```bash
#!/usr/bin/env bash
# .claude/skills/reflexion-debate
# Lines 5+ inject instructions into Claude's context

You are a Reflexion-style debate orchestrator...
## Reflexion Pattern Overview
1. Self-reflection after each round
2. Trajectory evaluation
3. Memory of past failures
...
```

**Examples:**
- `reflexion-debate` - Injects debate methodology
- `retention-aware-presentation` - Modifies output formatting based on user signals
- `repo-cleanup-audit` - Transforms into repository auditor persona

**Value:** Modifies **HOW** the agent thinks/behaves, not just **WHAT** it can do.

### Mode 2: Task Executors (CLI Backends)
**Simple stateless operations**

```python
#!/usr/bin/env python3
# .claude/skills/data/fetch-web-page.py
# Executable script, JSON output

def fetch_page(url, options):
    response = requests.get(url, ...)
    return {"status": "success", "html": response.text}
```

**Examples:**
- `fetch-from-api.py` - API data fetching
- `place-images-in-pptx.py` - Document generation
- `convert-to-pdf.py` - Format transformation

**Value:** Lightweight, cacheable, composable in workflows.

---

## MCP Servers: Agent Reasoning Layer

### MCP Protocol Capabilities

**From monorepo analysis (`../monorepo/agentic/mcp-servers/`):**

```python
# MCP resources expose STATE, not behavior
@server.read_resource()
async def read_resource(uri: str) -> str:
    if uri == "debate://status":
        return json.dumps(self.get_debate_agent_status())
    # Returns: JSON state data (sessions, metrics, artifacts)
```

**Key Features:**
- Stateful sessions (Pydantic models)
- A2A protocol for multi-agent coordination
- Constitutional compliance (Judge/Evidence/Reflexion)
- Provider abstraction patterns
- JSON-RPC stdio transport
- Dynamic tool discovery via `list_tools()`

**Examples:**
- `reason-debate/mcp_debate_server.py` (457 lines) - Multi-round debates with evidence
- `orchestrator/mcp_orchestrator_server.py` (676 lines) - Multi-provider coordination
- `code-execution/mcp_code_execution_server.py` - Sandboxed execution with oversight
- `benchmarking/mcp_benchmarking_server.py` - SWE-Bench testing

---

## Architectural Comparison

| Dimension | Skills | MCP Servers |
|-----------|--------|-------------|
| **Protocol** | Workflow YAML + JSON output | JSON-RPC stdio |
| **Registration** | Static markdown specs | Dynamic `list_tools()` |
| **Execution** | Subprocess CLI | Tool call handlers |
| **State Management** | Stateless (manifest files) | Stateful (Pydantic sessions) |
| **Behavioral Modification** | ✅ Prompt injection | ❌ Not supported |
| **Multi-Agent Coordination** | ❌ Not supported | ✅ A2A protocol |
| **Complexity** | 50-200 lines | 400-600 lines |
| **Portability** | Claude Code only | Any MCP client |
| **Purpose** | Task automation + behavior | Agent reasoning |

---

## Three-Layer Architecture Model

```
┌─────────────────────────────────────┐
│ LAYER 1: Prompt Injection (Skills) │ ← Modify HOW agent thinks
│ - reflexion-debate                  │
│ - retention-aware-presentation      │
│ - repo-cleanup-audit                │
└─────────────────────────────────────┘
           ↓ Modifies behavior of
┌─────────────────────────────────────┐
│ LAYER 2: Agent Core (Claude Code)  │
└─────────────────────────────────────┘
           ↓ Uses tools from
┌─────────────────────────────────────┐
│ LAYER 3a: MCP Servers (Tools)      │ ← Provide WHAT agent can do
│ - Debate reasoning                  │   (stateful, multi-agent)
│ - Code execution                    │
│ - Benchmarking                      │
└─────────────────────────────────────┘
           ↓ Orchestrates
┌─────────────────────────────────────┐
│ LAYER 3b: Skills (Executors)       │ ← DO specific tasks
│ - fetch-from-api.py                 │   (stateless, cacheable)
│ - place-images-in-pptx.py           │
└─────────────────────────────────────┘
```

---

## Decision Matrix

| Capability | Best Implementation | Rationale |
|------------|-------------------|-----------|
| **Behavioral Modification** | Skill (prompt injection) | Only Skills can inject instructions |
| **Stateful Reasoning** | MCP Server | Pydantic sessions, A2A protocol |
| **Simple Task Automation** | Skill (CLI executor) | Lightweight, stateless, cacheable |
| **Complex Multi-Agent** | MCP Server | Judge/Evidence/Reflexion, real-time A2A |
| **Workflow Orchestration** | Skills (YAML workflows) | Declarative, composable, cached |

---

## Workflow Composition: The Core Value

### Why Workflows Matter

**Without Orchestrator (bash scripts):**
```bash
# Manual data flow - error-prone!
python3 fetch.py "url" > output1.json
python3 extract.py "$(jq -r .html_path output1.json)" > output2.json
python3 generate.py "$(jq -r .decklist_path output2.json)"
```

**With Orchestrator (YAML workflows):**
```yaml
# Declarative composition with automatic data flow
name: "commander_to_proxies"
steps:
  - name: fetch_page
    skill: data/fetch-web-page
    outputs:
      html_path: "{{result}}"

  - name: extract_cards
    skill: data/extract-cards-from-html
    args:
      html_file: "{{steps.fetch_page.outputs.html_path}}"  # Auto data flow!
    outputs:
      decklist_path: "{{result}}"

  - name: generate_proxies
    workflow: workflows/proxy_pipeline_composed.yaml      # Nested workflows!
    args:
      decklist_path: "{{steps.extract_cards.outputs.decklist_path}}"
```

### Composition Patterns Supported

**1. Linear Pipeline:**
```yaml
steps: [A → B → C → D]
```

**2. Parallel Execution:**
```yaml
steps:
  - A [P]  # Parallel
  - B [P]  # Parallel
  - C      # Waits for A + B
```

**3. Nested Workflows:**
```yaml
steps:
  - workflow: workflows/sub_workflow.yaml
    # Workflows compose recursively
```

**4. Caching Per Step:**
```
First run:  3.411 seconds
Second run: 0.134 seconds (25x speedup via A2A message cache!)
```

---

## Orchestrator Architecture Analysis

### Current Implementation
**Location:** `a2a_orchestrator/`
**Total Size:** 1,561 lines (18 files)

### Value Assessment

**✅ VALUABLE (Keep - 70%):**

| Component | Lines | Purpose |
|-----------|-------|---------|
| `message_cache.py` | 274 | A2A caching (25x speedup) |
| `yaml_workflow_loader.py` | 274 | YAML parsing + validation |
| Variable substitution | ~100 | `{{steps.X.outputs.Y}}` resolution |
| Data flow engine | ~150 | Connect step outputs to inputs |
| Nested workflow support | ~100 | Recursive workflow composition |
| Step coordinator | ~200 | Orchestrate execution sequence |
| **TOTAL KEEP** | **~1,100** | **Core composition engine** |

**❌ BLOAT (Delete - 30%):**

| Component | Lines | Issue |
|-----------|-------|-------|
| Skill wrapper classes | ~200 | Claude Code executes skills directly |
| Hardcoded registration | ~50 | Claude discovers automatically |
| Custom subprocess logic | ~200 | Claude handles this natively |
| **TOTAL DELETE** | **~460** | **Reinventing Claude Code** |

### Architectural Issues Identified

**1. Hardcoded Skill Registration**
```python
# PROBLEM: Manual registration
def _register_builtin_skills(self):
    self.registered_skills["data/fetch-web-page"] = WebFetcherSkill()
    self.registered_skills["data/extract-cards"] = HTMLExtractorSkill()
    # ... adding every skill manually!
```

**Impact:**
- Adding new skill requires modifying orchestrator code
- No dynamic discovery (MCP has `list_tools()`!)
- Tight coupling

**2. Skill Wrapper Classes**
```python
# PROBLEM: Wrapping what Claude Code already does
class WebFetcherSkill(Skill):
    async def process_request(self, message: A2AMessage):
        # Just calls: subprocess.run([script_path, ...])
```

**Impact:**
- 200+ lines of unnecessary abstraction
- Claude Code already executes `.claude/skills/**/*.py` as MCP tools

**3. God Object Pattern**
```python
class YAMLWorkflowOrchestrator:
    # Does EVERYTHING:
    - YAML parsing
    - Schema validation
    - Skill registration
    - A2A message passing
    - Caching
    - Subprocess execution
    - Variable substitution
```

**Impact:**
- Single Responsibility Principle violation
- 528 lines in one class

---

## Refactoring Recommendations

### Phase 1: Minimal Viable Orchestrator

**Goal:** Reduce to ~1,100 lines focused on composition + caching

**Keep:**
1. `message_cache.py` (274 lines) - Performance critical
2. `yaml_workflow_loader.py` (274 lines) - Core workflow parsing
3. Variable substitution logic (~100 lines)
4. Data flow engine (~150 lines)
5. Nested workflow support (~100 lines)
6. Step execution coordinator (~200 lines)

**Delete:**
1. All skill wrapper classes (`skills/*.py`)
2. Hardcoded `_register_builtin_skills()`
3. Custom subprocess execution (delegate to Claude Code)

**Result:** 1,561 → 1,100 lines (30% reduction)

### Phase 2: Modular Architecture

```
workflow_engine/
├── cache/
│   ├── message_cache.py        # A2A caching
│   └── cache_cli.py            # Management tool
├── parser/
│   ├── yaml_loader.py          # YAML parsing
│   └── schema_validator.py     # Schema validation
├── executor/
│   ├── step_coordinator.py     # Orchestration
│   ├── data_flow.py            # Output → Input mapping
│   └── variable_resolver.py    # {{...}} substitution
└── orchestrator.py             # Thin coordinator (~200 lines)
```

### Phase 3: Future Enhancements

**Potential MCP Workflow Server:**
```python
# Expose workflows as MCP tools for portability
class MCPWorkflowServer:
    @server.list_tools()
    async def list_tools():
        # Discover all workflows/*.yaml
        return [Tool(name=workflow_name, ...) for ...]

    @server.call_tool()
    async def call_tool(name: str, args: dict):
        # Execute workflow with A2A caching
        return await execute_workflow(f"workflows/{name}.yaml", args)
```

**Benefits:**
- Claude Desktop can use workflows
- Cline can use workflows
- Any MCP client gains workflow composition

---

## Use Case Guidelines

### Use Skill When:

1. ✅ **Behavioral modification needed** (prompt injection)
   - Examples: reflexion-debate, retention-aware-presentation

2. ✅ **Simple stateless operation**
   - Examples: fetch-from-api, convert-to-pdf

3. ✅ **Workflow composition** (orchestrating multiple skills)
   - Examples: commander_to_proxies.yaml

4. ✅ **Claude Code only** (no portability requirement)

### Use MCP Server When:

1. ✅ **Stateful sessions required**
   - Examples: Multi-round debates, code execution contexts

2. ✅ **Multi-agent coordination**
   - Examples: Judge/Evidence/Reflexion patterns

3. ✅ **Constitutional compliance**
   - Examples: Code execution with oversight

4. ✅ **Portability across MCP clients**
   - Works in Claude Desktop, Cline, custom tools

5. ✅ **Complex reasoning patterns**
   - Examples: Provider orchestration, benchmarking

---

## Key Findings

### Skills Are NOT "Just CLI Wrappers"

**Two distinct modes:**
1. **Prompt injection** - Behavioral transformation (unique capability!)
2. **Task execution** - Lightweight automation (complementary to MCP)

### MCP Resources ≠ Prompt Injection

**MCP resources expose:**
```python
# JSON state data (observability)
Resource(uri="debate://status", mimeType="application/json")
```

**Skills inject:**
```bash
# Behavioral instructions (capability modification)
You are a Reflexion-style debate orchestrator...
```

**Conclusion:** Architecturally distinct capabilities.

### Workflow Composition is Core Value

**The orchestrator IS a composition engine:**
- Data flow between steps (automatic)
- Variable substitution (`{{steps.X.outputs.Y}}`)
- Nested workflows (recursive composition)
- Per-step caching (25x speedup)
- Declarative YAML (readable, testable, versionable)

**Without it:** Manual bash scripts with error-prone data flow.

### 30% of Orchestrator is Bloat

**Problems:**
- Hardcoded skill registration (should be dynamic)
- Skill wrapper classes (Claude Code handles this)
- Reimplementing subprocess execution (redundant)

**Solution:** Refactor to 1,100-line focused composition engine.

---

## Recommendations

### Immediate Actions

1. ✅ **Keep both Skills and MCP** - They're complementary, not competing
2. ✅ **Value prompt injection skills** - Unique capability
3. ✅ **Preserve workflow composition** - Core value proposition
4. ⚠️ **Refactor orchestrator** - Remove 30% bloat (skill wrappers, hardcoding)

### Decision Framework

```
Does it modify Claude's behavior?
├─ YES → Skill (prompt injection)
└─ NO → Continue...

Need stateful sessions?
├─ YES → MCP server
└─ NO → Continue...

Simple + stateless?
├─ YES → Skill (executor)
└─ NO → MCP server (complex orchestration)
```

### Architecture Principle

**Skills = Lightweight behavioral + execution layer**
**MCP = Heavy-duty agent reasoning + orchestration layer**

Use both based on capability requirements, not arbitrary preference.

---

## Appendix: Evidence Summary

### Skills Found (This Project)
- 12 markdown specifications
- 9 Python backends (CLI executors)
- 4 prompt injection skills (bash scripts)

### MCP Servers Found (Monorepo)
- 5 major servers (1,870 total lines)
- Debate (457), Orchestrator (676), Code Execution (150), Benchmarking (200), Wrapper (663)

### Performance Metrics
- A2A caching: 25x speedup (3.4s → 0.13s)
- Workflow efficiency: Declarative > imperative for composition

### Code Complexity
- Our orchestrator: 1,561 lines (30% bloat)
- Monorepo MCP orchestrator: 676 lines (more focused)
- Refactoring target: 1,100 lines (composition + caching only)

---

**Conclusion:** Skills and MCP are complementary. Skills provide unique prompt injection + lightweight workflow composition. MCP provides stateful multi-agent reasoning. Both are valuable. Orchestrator needs 30% refactoring to remove redundant wrapper code.
