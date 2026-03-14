#!/usr/bin/env python3
"""Smoke test: MCTS layout engine with a synthetic card.

Validates the full backwards-built pipeline:
  Card → CardElements → strategic actions → MCTS search → LayoutState
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.models.card import Card
from src.models.bounding_box import BoundingBox
from src.models.card_element import CardElement
from src.models.layout_action import LayoutAction
from src.layout.mcts_layout_engine import MCTSLayoutEngine, LayoutRewardFunction, LayoutState
from src.mcts.actions import generate_strategic_actions


def test_bounding_box():
    """Test BoundingBox overlap detection."""
    a = BoundingBox(x=0, y=0, width=100, height=100)
    b = BoundingBox(x=50, y=50, width=100, height=100)
    c = BoundingBox(x=200, y=200, width=50, height=50)

    assert a.overlaps(b), "a and b should overlap"
    assert not a.overlaps(c), "a and c should not overlap"
    assert a.overlap_area(b) == 2500, f"overlap area should be 2500, got {a.overlap_area(b)}"
    assert a.center == (50, 50)
    print("  BoundingBox: OK")


def test_card_element():
    """Test CardElement priority ordering."""
    name = CardElement("name", "Lightning Bolt")
    pt = CardElement("p_t", "3/3")
    ability = CardElement("ability_1", "Haste")

    assert name.priority < ability.priority < pt.priority, "Priority order: name < ability < p_t"
    print("  CardElement: OK")


def test_strategic_actions():
    """Test strategic action generation."""
    element = CardElement("name", "Krenko, Mob Boss", required=True)

    # Build regions dict with BoundingBox objects (matching what actions.py expects)
    regions = {
        "name_box": BoundingBox(x=50, y=35, width=500, height=40),
        "mana_cost_box": BoundingBox(x=580, y=35, width=130, height=40),
        "type_box": BoundingBox(x=50, y=520, width=560, height=35),
        "text_box": BoundingBox(x=65, y=565, width=610, height=375),
        "pt_box": BoundingBox(x=595, y=935, width=90, height=47),
        "artwork_box": BoundingBox(x=41, y=88, width=662, height=483),
    }

    actions = generate_strategic_actions(element, regions)
    print(f"  Strategic actions for 'name': {len(actions)} candidates")
    assert len(actions) > 0, "Should generate at least 1 action"

    # Name elements should only have center alignment
    alignments = {a.alignment for a in actions}
    assert alignments == {"center"}, f"Name should only have center alignment, got {alignments}"
    print("  Strategic actions: OK")


def test_mcts_layout():
    """Test full MCTS layout optimization."""
    card = Card(
        name="Krenko, Mob Boss",
        type="Creature",
        mana_cost="{2}{R}{R}",
        color="red",
        legendary=True,
        subtypes=["Goblin", "Warrior"],
        abilities=["T: Create X 1/1 red Goblin creature tokens, where X is the number of Goblins you control."],
        power_toughness="3/3",
    )

    regions = {
        "name_box": BoundingBox(x=50, y=35, width=500, height=40),
        "mana_cost_box": BoundingBox(x=580, y=35, width=130, height=40),
        "type_box": BoundingBox(x=50, y=520, width=560, height=35),
        "text_box": BoundingBox(x=65, y=565, width=610, height=375),
        "pt_box": BoundingBox(x=595, y=935, width=90, height=47),
        "artwork_box": BoundingBox(x=41, y=88, width=662, height=483),
    }

    engine = MCTSLayoutEngine(max_rollouts=20, quality_threshold=0.5)
    layout = engine.optimize_layout(card, regions, rollouts=20)

    print(f"  Placed elements: {len(layout.placed_elements)}")
    for elem_type, placed in layout.placed_elements.items():
        print(f"    {elem_type}: ({placed.bbox.x}, {placed.bbox.y}) font={placed.font_size} align={placed.alignment}")

    assert len(layout.placed_elements) > 0, "Should place at least 1 element"
    print("  MCTS layout: OK")


def test_reward_function():
    """Test layout reward scoring."""
    regions = {
        "name_box": BoundingBox(x=50, y=35, width=500, height=40),
        "text_box": BoundingBox(x=65, y=565, width=610, height=375),
    }

    reward_fn = LayoutRewardFunction(regions)

    # Empty state
    empty = LayoutState()
    assert reward_fn.evaluate(empty) == 0.0

    # Perfect placement (element within its region)
    from src.layout.mcts_layout_engine import PlacedElement
    good_state = LayoutState(placed_elements={
        "name": PlacedElement(
            element=CardElement("name", "Test Card"),
            bbox=BoundingBox(x=60, y=40, width=200, height=30),
            font_size=16,
            alignment="center",
        )
    })
    score = reward_fn.evaluate(good_state)
    print(f"  Good placement score: {score:.3f}")
    assert score > 0.5, f"Good placement should score > 0.5, got {score}"
    print("  Reward function: OK")


def test_mana_renderer():
    """Test mana symbol rendering."""
    from src.rendering.mana_symbol_renderer import ManaSymbolRenderer

    renderer = ManaSymbolRenderer()

    # Parse
    symbols = renderer.parse_mana_cost("{2}{R}{R}")
    assert len(symbols) == 3, f"Expected 3 symbols, got {len(symbols)}"
    assert symbols[0] == ("2", "C")
    assert symbols[1] == ("R", "R")

    # Render
    img = renderer.render_mana_cost("{2}{R}{R}", size=24)
    assert img.width > 0 and img.height == 24
    print(f"  Mana render: {img.size} — OK")


if __name__ == "__main__":
    print("MCTS Pipeline Smoke Tests")
    print("=" * 40)

    test_bounding_box()
    test_card_element()
    test_strategic_actions()
    test_reward_function()
    test_mana_renderer()
    test_mcts_layout()

    print("\n" + "=" * 40)
    print("ALL TESTS PASSED")
