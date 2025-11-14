# Magic: The Gathering EDH Deck Cards Presentation

🎴 An automated PowerPoint presentation generator for Magic: The Gathering EDH deck cards.

## 📁 Repository Contents

- **`magic_cards_completed_FINAL.pptx`** - ✅ **CORRECTED** PowerPoint with all 158 cards properly placed
- **`magic_cards_completed_FINAL.pdf`** - ✅ **CORRECTED** PDF version (14.4MB) following template structure  
- **`magic_cards_template.pptx`** - Original template from Google Slides with card slots
- **`magic_cards_template.pdf`** - PDF version of original template (1.4MB)
- **`magic_cards_template_final_fix.py`** - ✅ **CORRECTED** automation script that properly follows template
- **`magic_cards_completed.pptx`** - ❌ Old version (incorrect template usage)
- **`magic_cards_ppt_automation.py`** - ❌ Old script (incorrect template usage)
- **`images/`** - Directory containing all 158 Magic card images (numbered 001-158)

## 🎯 What This Does

This project automatically:
1. ✅ Downloads Magic card images from EDH deck URLs
2. ✅ Analyzes PowerPoint templates to find card-shaped slots
3. ✅ Resizes and places all cards into appropriate slots
4. ✅ Creates additional grid slides for overflow cards
5. ✅ Generates a complete presentation ready for sharing

## 📊 Results ✅ CORRECTED

- **24 template slots** properly filled with first 24 cards (2.5" × 3.6" each)
  - Slide 1: 8 cards in original template layout  
  - Slide 2: 16 cards in original template layout
- **7 additional grid slides** with remaining 134 cards (4×5 grid, 20 per slide)
- **158 total cards** from the EDH deck processed correctly
- **Perfect template structure** preservation - no new slides created unnecessarily
- **Perfect aspect ratios** maintained for all Magic cards

## 🚀 Usage

```bash
# Run the CORRECTED automation script  
python3 magic_cards_template_final_fix.py

# Requirements
pip install python-pptx pillow requests
```

## 🎴 Card Source

Cards were sourced from: `https://edhrec.com/deckpreview/ho6_4ArGi1AR00gbgsaCsA`

All card images are sourced from Scryfall and are used for personal deck organization purposes.

## 📝 Features

- **Template Analysis**: Automatically detects card slots in PowerPoint templates
- **Smart Resizing**: Maintains Magic card aspect ratios while fitting slots
- **Grid Generation**: Creates organized overflow slides for extra cards
- **Batch Processing**: Handles large deck lists efficiently
- **Error Handling**: Graceful handling of missing images or slots

---
*Generated automatically with PowerPoint automation tools* ✨