# API Contracts

**Feature**: 012 Hellcube Proxy Generator
**Type**: CLI Batch Processor (Python Module Interfaces, not REST API)

This directory contains interface specifications for Python modules. Since this is a CLI tool (not a web service), contracts define:
- Python class/function signatures
- Input/output Pydantic schemas
- Error handling contracts

---

## Module Contracts

1. **hellcube_parser.py** - Excel parsing with adjacency detection
2. **mcts_layout.py** (monorepo) - MCTS layout optimization algorithm
3. **vlm_evaluators.py** (monorepo) - VLM template detection and layout scoring
4. **proxy_compositor.py** - PIL-based image composition
5. **batch_organizer.py** - Dynamic folder organization

See individual `.md` files for detailed contract specifications.
