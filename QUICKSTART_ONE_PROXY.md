# Quickstart: Generate ONE MTG Proxy Card

**Goal**: Generate your first MTG proxy card end-to-end in ~10 minutes!

---

## Prerequisites

### 1. Ollama + llava:7b Running
```bash
# Check if running
ollama list | grep llava:7b

# If not, start Ollama and pull model
ollama serve &
ollama pull llava:7b
```

### 2. Hellcube Spreadsheet
Place `Hellcube AJ.xlsx` in project root directory.

### 3. ONE Blanked Template
Run template preprocessing for ONE template (5-10 min):

```bash
python src/cli/preprocess_templates.py \
  --max-rollouts 10 \
  --max-concurrent 1 \
  --subset 18bfdd1da886ce2c59fd2c1e8db2bfa4c94253ef5b36e1a8f6c5c729f7f6999b
```

**Verify**: Check `.cache/templates_blanked/` has at least one `*_blank.png` file

---

## Execute Golden Path

### Run the E2E Test Script

```bash
python test_one_proxy.py
```

### Expected Output

```
======================================================================
END-TO-END TEST: Generate ONE MTG Proxy Card
======================================================================

[2025-11-23 15:30:00] Step 1: Parsing ONE card from Hellcube spreadsheet...
[2025-11-23 15:30:01] ✅ Parsed card: Lightning Bolt
  - Type: Instant
  - Mana Cost: (Rd)
  - Color: red
  - Abilities: 1 ability(ies)

[2025-11-23 15:30:02] Step 2: Loading blanked template...
[2025-11-23 15:30:02] Using template hash: 18bfdd1da886ce2c...
[2025-11-23 15:30:03] ✅ Loaded blanked template: (745, 1040)

[2025-11-23 15:30:03] Step 3: Creating placeholder artwork (MVP - skipping download)...
[2025-11-23 15:30:03] ✅ Created placeholder artwork: (400, 300)

[2025-11-23 15:30:04] Step 4: Compositing artwork onto template...
[2025-11-23 15:30:04] ✅ Artwork composited at (172, 260)

[2025-11-23 15:30:05] Step 5: Preparing card elements for MCTS text placement...
[2025-11-23 15:30:05] Created 3 card elements

[2025-11-23 15:30:06] Step 6: Applying heuristic text layout (MVP - skipping MCTS)...
[2025-11-23 15:30:06] ✅ Heuristic layout applied

[2025-11-23 15:30:07] Step 7: Rendering text onto template...
[2025-11-23 15:30:07] ✅ Text rendered

[2025-11-23 15:30:08] Step 8: Saving final proxy...
[2025-11-23 15:30:08] ✅ Proxy saved to: output/proxies/red/Lightning_Bolt.png

======================================================================
SUCCESS! Proxy card generated:
  - Card: Lightning Bolt
  - Type: Instant
  - Color: red
  - Output: output/proxies/red/Lightning_Bolt.png
  - Size: (745, 1040) @ 300 DPI
======================================================================
```

---

## View Your Proxy

```bash
# Open with image viewer
xdg-open output/proxies/red/Lightning_Bolt.png

# Or use file manager
ls -lh output/proxies/red/
```

---

## What This Script Does (MVP)

### ✅ Implemented
1. **Parse ONE card** from Hellcube spreadsheet
2. **Load blanked template** (from preprocessing cache)
3. **Create placeholder artwork** (cornflower blue rectangle with "ARTWORK" text)
4. **Composite artwork** onto template center
5. **Apply heuristic text layout** (name, type, abilities at fixed positions)
6. **Render text** onto template with word wrapping
7. **Save final proxy** to `output/proxies/{color}/{card_name}.png` @ 300 DPI

### ⏭️ Skipped (for Speed)
- ❌ Real artwork download (uses placeholder)
- ❌ MCTS text placement optimization (uses heuristic positions)
- ❌ VLM region detection (uses hardcoded coordinates)
- ❌ Mana symbol rendering (text only)

### 🚀 Full Pipeline (Future)
To get MCTS-optimized layout with real artwork:
1. Implement artwork download (T037)
2. Enable MCTS text placement in script (change flag)
3. Add mana symbol rendering (T039)

---

## Troubleshooting

### Error: "No blanked templates found in cache!"
**Solution**: Run preprocessing first:
```bash
python src/cli/preprocess_templates.py \
  --max-rollouts 10 \
  --max-concurrent 1 \
  --subset 18bfdd1da886ce2c59fd2c1e8db2bfa4c94253ef5b36e1a8f6c5c729f7f6999b
```

### Error: "Hellcube AJ.xlsx not found!"
**Solution**: Copy spreadsheet to project root:
```bash
cp /path/to/Hellcube\ AJ.xlsx .
```

### Error: Card parsing fails
**Solution**: Check Excel file format:
```bash
# Verify file exists and is readable
file "Hellcube AJ.xlsx"
```

---

## Next Steps

### After First Proxy Works

1. **Run full preprocessing** (112 templates, 2-4 hours):
   ```bash
   python src/cli/preprocess_templates.py
   ```

2. **Enable MCTS optimization** in `test_one_proxy.py`:
   ```python
   # Change Step 6 to use MCTS instead of heuristic
   from src.mcts.mcts_algorithm import MCTSLayoutAlgorithm

   mcts = MCTSLayoutAlgorithm(max_rollouts=100)
   result = mcts.execute(problem={"elements": elements, "template_regions": regions})
   ```

3. **Implement artwork download** (T037)

4. **Process full batch** (200 cards):
   ```bash
   python src/batch/batch_processor.py --input "Hellcube AJ.xlsx"
   ```

---

**Time to First Proxy**: ~10 minutes (including preprocessing) 🎉
