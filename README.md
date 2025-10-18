# Magic: The Gathering EDH Deck Cards Presentation

🎴 An automated PowerPoint presentation generator for Magic: The Gathering EDH deck cards.

## 📁 Repository Contents

- **`magic_cards_completed.pptx`** - Final PowerPoint presentation with all 158 cards placed
- **`magic_cards_template.pptx`** - Original template from Google Slides with card slots
- **`magic_cards_ppt_automation.py`** - Python automation script for placing cards
- **`images/`** - Directory containing all 158 Magic card images (numbered 001-158)

## 🎯 What This Does

This project automatically:
1. ✅ Downloads Magic card images from EDH deck URLs
2. ✅ Analyzes PowerPoint templates to find card-shaped slots
3. ✅ Resizes and places all cards into appropriate slots
4. ✅ Creates additional grid slides for overflow cards
5. ✅ Generates a complete presentation ready for sharing

## 📊 Results

- **24 template slots** filled with first 24 cards (2.5" × 3.6" each)
- **7 additional grid slides** with remaining 134 cards
- **158 total cards** from the EDH deck processed
- **Perfect aspect ratios** maintained for all Magic cards

## 🚀 Usage

```bash
# Run the automation script
python3 magic_cards_ppt_automation.py

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