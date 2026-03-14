"""Render mana cost strings ({2}{R}{R}) into composite images with colored circles."""

import re
from PIL import Image, ImageDraw, ImageFont


# WUBRG color mapping for mana symbols
MANA_COLORS = {
    'W': (248, 231, 185),   # White - cream/gold
    'U': (14, 104, 171),    # Blue
    'B': (21, 11, 0),       # Black
    'R': (211, 32, 42),     # Red
    'G': (0, 115, 62),      # Green
    'C': (204, 194, 193),   # Colorless
    'X': (204, 194, 193),   # Variable
}

# Text color on each background (contrast)
MANA_TEXT_COLORS = {
    'W': (0, 0, 0),
    'U': (255, 255, 255),
    'B': (255, 255, 255),
    'R': (255, 255, 255),
    'G': (255, 255, 255),
    'C': (0, 0, 0),
    'X': (0, 0, 0),
}


class ManaSymbolRenderer:
    """Render mana cost strings into PIL Images with colored circles."""

    def __init__(self, symbol_size: int = 24):
        self.symbol_size = symbol_size
        self.spacing = 2

    def parse_mana_cost(self, cost_str: str) -> list:
        """Parse mana cost string like '{2}{R}{R}' or '2RR' into symbol list.

        Returns list of tuples: (symbol_text, color_key)
        """
        symbols = []

        # Handle {X} notation
        braces = re.findall(r'\{([^}]+)\}', cost_str)
        if braces:
            for s in braces:
                if s.isdigit():
                    symbols.append((s, 'C'))
                elif s.upper() in MANA_COLORS:
                    symbols.append((s.upper(), s.upper()))
                elif s.upper() == 'X':
                    symbols.append(('X', 'X'))
                else:
                    symbols.append((s, 'C'))
            return symbols

        # Handle compact notation like '2RR'
        i = 0
        while i < len(cost_str):
            ch = cost_str[i].upper()
            if ch.isdigit():
                # Collect multi-digit numbers
                num = ch
                while i + 1 < len(cost_str) and cost_str[i + 1].isdigit():
                    i += 1
                    num += cost_str[i]
                symbols.append((num, 'C'))
            elif ch in MANA_COLORS:
                symbols.append((ch, ch))
            i += 1

        return symbols

    def render_mana_cost(self, cost_str: str, size: int = None) -> Image.Image:
        """Render mana cost string to a PIL Image with colored circles.

        Args:
            cost_str: Mana cost string (e.g., '{2}{R}{R}' or '2RR')
            size: Override symbol size

        Returns:
            RGBA PIL Image with rendered mana symbols
        """
        sz = size or self.symbol_size
        symbols = self.parse_mana_cost(cost_str)

        if not symbols:
            return Image.new('RGBA', (1, 1), (0, 0, 0, 0))

        total_width = len(symbols) * sz + (len(symbols) - 1) * self.spacing
        img = Image.new('RGBA', (total_width, sz), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                                       int(sz * 0.55))
        except (IOError, OSError):
            font = ImageFont.load_default()

        for i, (text, color_key) in enumerate(symbols):
            x = i * (sz + self.spacing)
            bg_color = MANA_COLORS.get(color_key, MANA_COLORS['C'])
            text_color = MANA_TEXT_COLORS.get(color_key, (0, 0, 0))

            # Draw circle
            draw.ellipse([x, 0, x + sz - 1, sz - 1], fill=bg_color + (255,),
                         outline=(0, 0, 0, 200), width=1)

            # Draw text centered
            bbox = font.getbbox(text)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            tx = x + (sz - tw) // 2
            ty = (sz - th) // 2 - bbox[1]
            draw.text((tx, ty), text, font=font, fill=text_color + (255,))

        return img
