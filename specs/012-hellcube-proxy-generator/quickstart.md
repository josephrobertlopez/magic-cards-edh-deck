# Quickstart Guide

**Feature**: 012 Hellcube Proxy Generator
**Purpose**: Get the system running quickly for development and validation

---

## Prerequisites

- **Python**: 3.9+ (existing codebase standard)
- **OS**: Linux (primary) or macOS (development)
- **Storage**: ~5GB free (4GB for llava-1.5 model + 1GB for templates/output)
- **Memory**: 8GB RAM minimum (16GB recommended for batch processing)

---

## Phase 0: Setup (VLM + Dependencies)

### 1. Install Ollama (Local VLM Backend)

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Verify installation
ollama --version
```

### 2. Download llava-1.5 Model

```bash
# Download model (~4GB, takes 5-10 minutes)
ollama pull llava:13b

# Verify model installed
ollama list
# Should show: llava:13b
```

### 3. Start Ollama Server

```bash
# Start server (runs on localhost:11434)
ollama serve

# Keep this terminal open, or run in background:
ollama serve &
```

### 4. Install Python Dependencies

```bash
# Navigate to project root
cd /home/joey/Documents/GitHub/magic-cards-edh-deck

# Install requirements
pip install -r requirements.txt

# Or install manually:
pip install pandas openpyxl pillow requests pydantic instructor
```

### 5. Verify Monorepo Link

```bash
# Ensure monorepo is accessible
ls ../monorepo/agentic/algorithms/base_algorithm.py
# Should exist

# If not, clone/symlink monorepo:
cd ..
git clone <monorepo-url> monorepo
```

---

## Phase 1: Validate VLM Integration

### Test 1: VLM Template Detection (Ground Truth)

```bash
# Run Phase 0 validation test
cd /home/joey/Documents/GitHub/magic-cards-edh-deck

# Set backend to Ollama
export BACKEND=ollama

# Run VLM detection accuracy test
pytest tests/integration/test_vlm_detection.py::test_vlm_detection_accuracy_nala_template -v

# Expected output:
# ✓ name_box: max_error=3px (within ±10px)
# ✓ mana_cost_box: max_error=5px
# ✓ type_line_box: max_error=2px
# ✓ text_box: max_error=8px
# ✓ pt_box: max_error=4px
# PASSED
```

**If test FAILS** (VLM detection > ±10px):
1. Check Ollama server is running: `curl http://localhost:11434/api/tags`
2. Review VLM prompt in `vlm_evaluators.py` (may need tuning)
3. Try different llava model version: `ollama pull llava:7b`

### Test 2: VLM Scoring Consistency

```bash
# Verify VLM scores layouts consistently
pytest tests/integration/test_vlm_scoring.py::test_vlm_scoring_consistency -v

# Expected output:
# ✓ 5 evaluations: scores=[0.88, 0.87, 0.89, 0.88, 0.87]
# ✓ std_dev=0.01 (≤0.05 threshold)
# PASSED
```

---

## Phase 2: MCTS Algorithm Validation

### Test 3: Grid World Problem (Known-Good Test)

```bash
# Test MCTS on simple grid navigation problem
pytest tests/integration/test_mcts_grid_world.py::test_mcts_finds_optimal_path -v

# Expected output:
# ✓ MCTS converged in 45 rollouts
# ✓ Found optimal path (quality ≥0.9)
# PASSED
```

**Purpose**: Validates MCTS algorithm correctness before applying to card layout problem.

### Test 4: Simple Card Layout (1 Ability)

```bash
# Test MCTS on simple MTG card
pytest tests/integration/test_mcts_simple_card.py -v

# Expected output:
# ✓ Card: Grizzly Bears (vanilla creature, 5 elements)
# ✓ Converged in 28 rollouts (20-30 expected)
# ✓ Quality score: 0.91 (≥0.8 threshold)
# ✓ Time: 5.6s (4-6s expected)
# PASSED
```

### Test 5: Complex Card Layout (3 Abilities)

```bash
# Test MCTS on complex card
pytest tests/integration/test_mcts_complex_card.py -v

# Expected output:
# ✓ Card: Jace, the Mind Sculptor (4 abilities, 8 elements)
# ✓ Converged in 72 rollouts (60-80 expected)
# ✓ Quality score: 0.84 (≥0.8 threshold)
# ✓ Time: 14.4s (12-16s expected)
# PASSED
```

---

## Phase 3: Excel Parsing Validation

### Test 6: Hellcube Spreadsheet Parsing

```bash
# Parse actual Hellcube AJ.xlsx file
python -m src.hellcube_parser "Hellcube AJ.xlsx" --validate

# Expected output:
# ✓ Parsed 203 cards from Hellcube AJ.xlsx
# ✓ All cards have required fields (name, type)
# ⚠ Warning: 12 cards missing flavor_text (optional)
# ⚠ Warning: 3 cards missing artwork_url (optional)
# ✓ Validation complete (0 errors)
```

**Sample Output**:
```
Card 1: Batman Blue
  Name: Batman Blue
  Mana Cost: (Bu,Bu)(1) → ['U', 'U', 'Generic']
  Color: U (Blue)
  Type: Creature
  Subtypes: ['Human', 'Batman']
  Abilities: ['Vigilance', 'When Batman Blue enters, draw a card']
  P/T: 2/2
  Author: AJ
  ...
```

---

## Phase 4: End-to-End Workflow

### Test 7: Single Card Proxy Generation

```bash
# Generate proxy for single card
python -m src.proxy_generator --card "Grizzly Bears" --output test_output/

# Expected output:
# ✓ Parsed card: Grizzly Bears
# ✓ Matched template: creature_frame.png
# ✓ VLM detected template regions (cached)
# ✓ MCTS optimization: 28 rollouts, score=0.91
# ✓ Generated proxy: test_output/Grizzly_Bears.png
# Time: 5.8s
```

### Test 8: Batch Processing (10 Cards)

```bash
# Generate proxies for first 10 cards
python -m src.proxy_generator "Hellcube AJ.xlsx" --limit 10 --output test_output/

# Expected output:
# ✓ Parsed 10 cards
# ✓ Detected 4 unique templates (6 cache hits)
# ✓ Generated 10 proxies
# ✓ Organized by color/type (dynamic voting algorithm)
# Time: 58s (5-6s per card average)
#
# Output structure:
# test_output/
# ├── blue/
# │   ├── creatures/
# │   │   ├── Batman_Blue.png
# │   │   └── Sea_Serpent.png
# │   └── instants/
# │       └── Counterspell.png
# └── green/
#     └── creatures/
#         └── Grizzly_Bears.png
```

---

## Debug Mode (Fast Iteration Without VLM)

For rapid development without waiting for VLM calls:

```bash
# Use test backend (heuristic scoring instead of VLM)
export BACKEND=test

# Run with mock VLM (instant feedback)
python -m src.proxy_generator "Hellcube AJ.xlsx" --limit 5

# Expected output:
# ⚠ Using BACKEND=test (heuristic scoring, not VLM)
# ✓ Parsed 5 cards
# ✓ Generated 5 proxies (heuristic quality)
# Time: 3s (vs 25-30s with VLM)
```

**Note**: Test mode quality will be lower than VLM mode. Use only for development/debugging.

---

## Troubleshooting

### Issue: Ollama Connection Error

**Error**: `ConnectionError: Cannot connect to Ollama at localhost:11434`

**Solution**:
```bash
# Check if Ollama is running
ps aux | grep ollama

# If not, start it:
ollama serve &

# Verify connection:
curl http://localhost:11434/api/tags
# Should return JSON with model list
```

### Issue: llava Model Not Found

**Error**: `ModelNotFoundError: Model 'llava:13b' not found`

**Solution**:
```bash
# Re-download model
ollama pull llava:13b

# Or use smaller 7B version:
ollama pull llava:7b
```

### Issue: Slow VLM Inference (>1s per call)

**Symptoms**: VLM taking 1-2s per evaluation instead of 0.2s

**Solutions**:
1. **Use GPU**: Ollama automatically uses CUDA if available
   ```bash
   # Verify GPU usage
   nvidia-smi
   # Should show ollama process using GPU
   ```

2. **Use smaller model**:
   ```bash
   ollama pull llava:7b  # Faster but slightly lower quality
   ```

3. **Reduce rollout budget**:
   ```python
   # In config
   mcts = MCTSLayoutAlgorithm(max_steps=1)  # 100 rollouts instead of 300
   ```

### Issue: Excel Parsing Fails

**Error**: `ParsingError: Invalid mana notation: (BU,BU)(1)`

**Solution**:
```bash
# Check mana symbol capitalization (should be lowercase: Bu, not BU)
# Review MANA_SYMBOL_MAP in src/mana_cost_parser.py

# If Hellcube uses different notation, update parser:
MANA_SYMBOL_MAP = {
    'Wt': 'W', 'wt': 'W', 'WT': 'W',  # Support multiple cases
    # ...
}
```

### Issue: Memory Error During Batch Processing

**Error**: `MemoryError: Cannot allocate 512MB for MCTS tree`

**Solutions**:
1. **Process in smaller batches**:
   ```bash
   # Process 50 cards at a time instead of 200
   python -m src.proxy_generator "Hellcube AJ.xlsx" --offset 0 --limit 50
   python -m src.proxy_generator "Hellcube AJ.xlsx" --offset 50 --limit 50
   # ...
   ```

2. **Enable tree pruning** (if implemented):
   ```python
   mcts = MCTSLayoutAlgorithm(
       max_steps=3,
       enable_pruning=True,  # Prune rarely-visited nodes
       pruning_threshold=5   # Prune nodes with <5 visits
   )
   ```

---

## Performance Expectations

### Phase 0 Validation (One-Time Setup)
- **VLM Detection Test**: <1 minute
- **VLM Scoring Consistency**: <2 minutes
- **Total Phase 0**: ~5 minutes

### MCTS Validation
- **Grid World**: <10 seconds
- **Simple Card**: 4-6 seconds
- **Complex Card**: 12-16 seconds

### Production Batch (200 Cards)
- **Parsing**: ~5 seconds
- **Template Detection**: ~3 seconds (15 unique templates × 0.2s)
- **MCTS Optimization**: ~3,300 seconds (200 cards × 16.5s average)
- **Total**: ~55 minutes to 1.5 hours

**Breakdown**:
- Simple cards (30%): 60 × 5s = 300s
- Medium cards (50%): 100 × 10s = 1,000s
- Complex cards (20%): 40 × 50s = 2,000s
- **Total MCTS time**: 3,300s ≈ 55 minutes

---

## Next Steps After Quickstart

1. ✅ **Phase 0 Complete**: VLM integration validated
2. ✅ **Phase 1 Complete**: MCTS algorithm validated
3. 🔄 **Phase 2**: Run full 200-card batch
4. 🔄 **Phase 3**: Review generated proxies for quality
5. 🔄 **Phase 4**: Print test proxies and validate physical output

**Ready for Implementation**: If all quickstart tests pass, proceed to `/speckit.tasks` to generate implementation task breakdown.
