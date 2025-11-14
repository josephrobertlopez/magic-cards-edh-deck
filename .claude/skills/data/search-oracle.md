# Search Oracle Skill

**RAG-based factual information retrieval with confidence scoring**

## Purpose

Query web/knowledge base for factual dimensional information to inform template-aware workflows. Returns structured facts with confidence scores for use as ground truth in print optimization.

## Usage

```bash
.claude/skills/data/search-oracle.py \
  --query "standard MTG card size in inches" \
  --num-results 5 \
  --output oracle_response.json
```

## Parameters

- `--query` (required): Factual query string
  - Examples: "business card dimensions", "recommended print DPI for posters", "A4 paper size"
- `--num-results` (optional): Number of search results to analyze (default: 5)
- `--output` (optional): Save response to JSON file

## Output Format

```json
{
  "status": "success",
  "query": "standard MTG card size in inches",
  "found": true,
  "facts": {
    "width_inches": 2.5,
    "height_inches": 3.5,
    "width_px": 750,
    "height_px": 1050,
    "dpi": 300,
    "confidence": 1.0,
    "sources": ["https://...", "..."],
    "num_sources": 2
  },
  "confidence": 1.0,
  "primary_source": "https://printninjas.com/mtg-card-specs"
}
```

## Confidence Scoring

- **1.0**: Complete dimensions + multiple sources agree
- **0.75-0.99**: Complete dimensions from single source
- **0.50-0.74**: Partial dimensions (width OR height)
- **0.25-0.49**: Single fact extracted (DPI only, etc.)
- **0.0**: No facts extracted

## Supported Fact Types

The oracle extracts:
- **Dimensions**: Width/height in inches, pixels, millimeters
- **DPI**: Print resolution (single value or range)
- **Aspect ratios**: Implied from width:height
- **Orientation**: Landscape vs portrait

## Search Strategy

1. **Real Web Search** (if available):
   - DuckDuckGo instant answer API
   - No API key required
   - Privacy-focused

2. **Fallback Knowledge Base**:
   - Generic keyword matching
   - Covers common print dimensions:
     - Playing/MTG cards
     - Business cards
     - Paper sizes (Letter, A4)
     - Posters
     - Print DPI standards

## Use Cases

### Template-Aware Fetching

```bash
# Query optimal size for card template
oracle_response=$(.claude/skills/data/search-oracle.py --query "MTG card size for 300 DPI print")

# Extract dimensions
width_px=$(echo "$oracle_response" | jq -r '.facts.width_px')
height_px=$(echo "$oracle_response" | jq -r '.facts.height_px')

# Pass to fetcher
.claude/skills/data/fetch-from-api.py \
  --decklist deck.txt \
  --size-hint "${width_px}x${height_px}"
```

### Print Workflow Validation

```bash
# Verify template DPI matches print standards
.claude/skills/data/search-oracle.py \
  --query "recommended DPI for poster printing" \
  | jq '.facts.dpi_recommended'  # Returns 300
```

### Dynamic Template Sizing

```bash
# Query paper dimensions
.claude/skills/data/search-oracle.py \
  --query "US letter paper landscape dimensions" \
  --output paper_size.json

# Use in template generation
python3 generate_template.py --size-spec paper_size.json
```

## Extending Knowledge Base

Add new dimensional facts by editing `search-oracle.py`:

```python
knowledge_base = [
    {
        "keywords": ["custom", "size", "query"],
        "fact": "Custom dimensions: X inches by Y inches at Z DPI",
        "title": "Custom Size Reference"
    },
    # ... more entries
]
```

## Integration with A2A Workflows

```yaml
# workflows/template-aware-fetch.yaml
steps:
  - name: query-template-dimensions
    skill: data/search-oracle
    input:
      query: "standard ${input.card_type} dimensions for print"
    output_var: size_facts

  - name: fetch-with-size-hints
    skill: data/fetch-from-api
    input:
      decklist_path: ${input.decklist_path}
      size_hints: ${size_facts.facts}
```

## Future Enhancements

- [ ] Integrate real web search APIs (SerpAPI, Google Custom Search)
- [ ] ML-based fact extraction (NER for dimensions)
- [ ] Caching for repeated queries
- [ ] Multi-source fact verification
- [ ] Confidence boosting from source authority
