"""
MCTS Template Extractor - Regional blanking with strategy search

Adapts Clifford MCTS for template blanking with 2 strategies:
- solid_fill: Fast color sampling + feathering
- edge_aware_fill: Canny edge detection + selective fill

POC Scope:
- 1 card proof (Krang template)
- 10 simulations or >0.6 quality score
- ~5 min per card for rapid iteration
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
import numpy as np
from PIL import Image, ImageDraw
import cv2
import math

# Reuse Clifford infrastructure
from clifford_mcts_inpainting import (
    CliffordImage,
    CliffordMultivector,
    DEVICE,
    torch
)


# ==============================================================================
# Template State & Actions
# ==============================================================================

@dataclass
class TemplateState:
    """
    MCTS state for template blanking.

    Tracks which regions have been blanked and with what strategies.
    """
    image: CliffordImage              # Current template (Clifford representation)
    regions_processed: Set[str]       # {name_box, type_box, text_box, etc.}
    region_strategies: Dict[str, str] # region_id -> strategy used
    frame_mask: np.ndarray           # Frame boundary (immutable)

    def is_terminal(self, all_regions: Set[str]) -> bool:
        """Check if all regions processed."""
        return self.regions_processed == all_regions


@dataclass
class BlankingAction:
    """
    MCTS action: blank a region with a specific color.

    Hybrid approach: MCTS searches color space, PIL applies destructively.
    """
    region_id: str                   # Which region to blank
    color: Tuple[int, int, int]      # RGB color to fill with

    def __hash__(self):
        return hash((self.region_id, self.color))


# ==============================================================================
# Color Sampling Functions (for MCTS action generation)
# ==============================================================================

def sample_edge_color(image: Image.Image, region: Dict) -> Tuple[int, int, int]:
    """Sample average color from region edges."""
    x, y, w, h = region['x'], region['y'], region['width'], region['height']
    img_np = np.array(image)

    edge_colors = []

    # Sample top & bottom edges
    for i in range(min(10, w)):
        px = x + i * (w // min(10, w))
        if 0 <= px < img_np.shape[1]:
            if 0 <= y < img_np.shape[0]:
                edge_colors.append(img_np[y, px])
            if 0 <= y+h-1 < img_np.shape[0]:
                edge_colors.append(img_np[y+h-1, px])

    # Average
    if edge_colors:
        return tuple(np.mean(edge_colors, axis=0).astype(int).tolist())
    else:
        return (128, 128, 128)


def sample_neighbor_color(image: Image.Image, region: Dict, offset: int = 5) -> Tuple[int, int, int]:
    """Sample color from pixels just outside region (frame propagation)."""
    x, y, w, h = region['x'], region['y'], region['width'], region['height']
    img_np = np.array(image)

    # Sample pixels just above region (likely frame color)
    neighbor_colors = []
    sample_y = max(0, y - offset)

    for i in range(min(10, w)):
        px = x + i * (w // min(10, w))
        if 0 <= px < img_np.shape[1] and 0 <= sample_y < img_np.shape[0]:
            neighbor_colors.append(img_np[sample_y, px])

    if neighbor_colors:
        return tuple(np.mean(neighbor_colors, axis=0).astype(int).tolist())
    else:
        return sample_edge_color(image, region)


def perturb_color(base_color: Tuple[int, int, int], delta: int = 10) -> Tuple[int, int, int]:
    """Perturb color for exploration (random nearby color)."""
    r, g, b = base_color
    r = int(np.clip(r + np.random.randint(-delta, delta), 0, 255))
    g = int(np.clip(g + np.random.randint(-delta, delta), 0, 255))
    b = int(np.clip(b + np.random.randint(-delta, delta), 0, 255))
    return (r, g, b)


# ==============================================================================
# Reward Function (Weighted: 0.35 edges + 0.35 VLM + 0.15 frame + 0.15 gradient)
# ==============================================================================

class TemplateRewardFunction:
    """Evaluates blanked template quality."""

    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or {
            'edges': 0.35,
            'vlm': 0.35,
            'frame': 0.15,
            'gradient': 0.15
        }

    def evaluate(self, state: TemplateState, original: CliffordImage) -> float:
        """
        Compute weighted reward.

        Returns score in [0, 1] where higher is better.
        """
        scores = {}

        # 1. Edge cleanliness (no leftover text artifacts)
        scores['edges'] = self._compute_edge_score(state.image)

        # 2. Frame consistency (matches reference frame pattern)
        scores['frame'] = self._compute_frame_score(state.image, original)

        # 3. Gradient smoothness (no visible boundaries)
        scores['gradient'] = self._compute_gradient_score(state.image)

        # 4. VLM evaluation (TODO: integrate Ollama for POC)
        scores['vlm'] = self._compute_vlm_score(state.image)

        # Weighted combination
        total = sum(self.weights[k] * scores[k] for k in scores)
        return total

    def _compute_edge_score(self, image: CliffordImage) -> float:
        """
        Score edge cleanliness (fewer edges = better).

        Use Canny edge detection, count edges in text regions.
        """
        img_pil = image.to_pil_image()
        img_gray = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2GRAY)

        # Canny edges
        edges = cv2.Canny(img_gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        # Lower density = cleaner (inverse score)
        return 1.0 - min(1.0, edge_density * 10)

    def _compute_frame_score(self, image: CliffordImage, original: CliffordImage) -> float:
        """
        Score frame consistency (compare with original frame areas).

        Sample frame regions (outside text boxes), compute color similarity.
        """
        # Simplified: compare overall color distribution
        img_np = np.array(image.to_pil_image())
        orig_np = np.array(original.to_pil_image())

        # Color histogram similarity (chi-square distance)
        hist1 = cv2.calcHist([img_np], [0,1,2], None, [8,8,8], [0,256,0,256,0,256])
        hist2 = cv2.calcHist([orig_np], [0,1,2], None, [8,8,8], [0,256,0,256,0,256])

        distance = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CHISQR)

        # Lower distance = more similar
        return 1.0 / (1.0 + distance / 1000)

    def _compute_gradient_score(self, image: CliffordImage) -> float:
        """
        Score gradient smoothness (no sharp transitions).

        Compute Sobel gradients, penalize high magnitudes.
        """
        img_np = np.array(image.to_pil_image())
        img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY).astype(np.float32)

        # Sobel gradients
        grad_x = cv2.Sobel(img_gray, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(img_gray, cv2.CV_32F, 0, 1, ksize=3)
        magnitude = np.sqrt(grad_x**2 + grad_y**2)

        # Lower average magnitude = smoother
        avg_magnitude = np.mean(magnitude)
        return 1.0 - min(1.0, avg_magnitude / 100)

    def _compute_vlm_score(self, image: CliffordImage) -> float:
        """
        VLM quality assessment (placeholder for POC).

        TODO: Integrate Ollama + llava for actual scoring.
        """
        # Placeholder: return fixed score for POC smoke test
        # In production, call Ollama with prompt:
        # "Is this a clean blank MTG card template with no text? Rate 0-1."
        return 0.7  # Optimistic baseline


# ==============================================================================
# MCTS Tree Node
# ==============================================================================

@dataclass
class MCTSNode:
    """MCTS tree node for template blanking search."""
    state: TemplateState
    parent: Optional['MCTSNode'] = None
    action: Optional[BlankingAction] = None
    children: List['MCTSNode'] = field(default_factory=list)
    visits: int = 0
    total_reward: float = 0.0
    untried_actions: List[BlankingAction] = field(default_factory=list)

    def is_fully_expanded(self) -> bool:
        return len(self.untried_actions) == 0

    def best_child(self, exploration_constant: float = 1.414) -> 'MCTSNode':
        """UCB1 selection."""
        best_score = -float('inf')
        best_node = None

        for child in self.children:
            if child.visits == 0:
                return child

            exploit = child.total_reward / child.visits
            explore = exploration_constant * math.sqrt(math.log(self.visits) / child.visits)
            ucb = exploit + explore

            if ucb > best_score:
                best_score = ucb
                best_node = child

        return best_node


# ==============================================================================
# MCTS Template Extractor
# ==============================================================================

class MCTSTemplateExtractor:
    """
    Hybrid MCTS: Search color space, apply with PIL rectangles.

    POC Configuration:
    - 3 color sampling methods: edge, neighbor, perturbed
    - 10 simulations or >0.6 score (~5min per card)
    - Weighted reward: 0.35 edges + 0.35 VLM + 0.15 frame + 0.15 gradient
    - Destructive blanking: PIL draw.rectangle() overwrites text
    """

    def __init__(self,
                 num_simulations: int = 10,
                 exploration_constant: float = 1.414,
                 quality_threshold: float = 0.6):
        self.num_simulations = num_simulations
        self.exploration_constant = exploration_constant
        self.quality_threshold = quality_threshold
        self.reward_function = TemplateRewardFunction()

    def extract(self, template_image: Image.Image, regions: List[Dict]) -> Image.Image:
        """
        Main entry point: blank template using MCTS.

        Args:
            template_image: Original template with text
            regions: VLM-detected regions [{x, y, width, height, id}, ...]

        Returns:
            Blanked template image
        """
        print(f"Hybrid MCTS Template Extractor starting...")
        print(f"  Regions: {len(regions)}")
        print(f"  Color sampling: edge, neighbor, perturbed")
        print(f"  Simulations: {self.num_simulations} (or >{self.quality_threshold} score)")

        # Convert to Clifford representation
        cliff_img = CliffordImage.from_pil_image(template_image)
        original_cliff = CliffordImage.from_pil_image(template_image)

        # Initialize MCTS
        all_regions = {r['id'] for r in regions}
        initial_state = TemplateState(
            image=cliff_img,
            regions_processed=set(),
            region_strategies={},
            frame_mask=np.ones((template_image.height, template_image.width), dtype=np.uint8)
        )

        root = MCTSNode(state=initial_state)
        root.untried_actions = self._generate_actions(initial_state, regions)

        # MCTS search
        for sim in range(self.num_simulations):
            node = root

            # Selection
            while not node.state.is_terminal(all_regions) and node.is_fully_expanded():
                node = node.best_child(self.exploration_constant)

            # Expansion
            if not node.state.is_terminal(all_regions) and not node.is_fully_expanded():
                action = node.untried_actions.pop()
                new_state = self._apply_action(node.state, action, regions)
                child = MCTSNode(state=new_state, parent=node, action=action)
                child.untried_actions = self._generate_actions(new_state, regions)
                node.children.append(child)
                node = child

            # Simulation (fast rollout with default strategy)
            final_state = self._rollout(node.state, regions, all_regions)

            # Evaluation
            reward = self.reward_function.evaluate(final_state, original_cliff)

            # Backpropagation
            while node:
                node.visits += 1
                node.total_reward += reward
                node = node.parent

            # Early stopping if quality threshold met
            best_reward = root.total_reward / root.visits if root.visits > 0 else 0
            if best_reward > self.quality_threshold:
                print(f"  Early stop at sim {sim+1}: score={best_reward:.3f}")
                break

            if (sim + 1) % 5 == 0:
                print(f"  Sim {sim+1}/{self.num_simulations}: best_score={best_reward:.3f}")

        # Extract best path
        best_state = self._extract_best_solution(root)
        print(f"  Final score: {self.reward_function.evaluate(best_state, original_cliff):.3f}")

        return best_state.image.to_pil_image()

    def _generate_actions(self, state: TemplateState, regions: List[Dict]) -> List[BlankingAction]:
        """
        Generate color-based actions from current state.

        For each unprocessed region, sample 3 color candidates:
        - Edge color (conservative)
        - Neighbor color (frame propagation)
        - Perturbed edge (exploration)
        """
        actions = []
        img_pil = state.image.to_pil_image()

        for region in regions:
            if region['id'] not in state.regions_processed:
                # Sample 3 colors per region
                edge_color = sample_edge_color(img_pil, region)
                neighbor_color = sample_neighbor_color(img_pil, region)
                perturbed = perturb_color(edge_color, delta=15)

                # Create 3 actions per region
                actions.append(BlankingAction(region_id=region['id'], color=edge_color))
                actions.append(BlankingAction(region_id=region['id'], color=neighbor_color))
                actions.append(BlankingAction(region_id=region['id'], color=perturbed))

        return actions

    def _apply_action(self, state: TemplateState, action: BlankingAction, regions: List[Dict]) -> TemplateState:
        """
        Apply color fill action using PIL rectangle (DESTRUCTIVE).

        This is the key difference from strategy-based approach:
        - Uses PIL draw.rectangle() to OVERWRITE text
        - No compositing, no preservation - direct pixel painting
        """
        # Find region
        region = next(r for r in regions if r['id'] == action.region_id)

        # Convert to PIL, draw rectangle, convert back
        img_pil = state.image.to_pil_image()
        draw = ImageDraw.Draw(img_pil)

        x, y, w, h = region['x'], region['y'], region['width'], region['height']

        # DESTRUCTIVE: Draw filled rectangle over text
        draw.rectangle(
            [(x, y), (x + w, y + h)],
            fill=action.color
        )

        # Convert back to Clifford
        new_image = CliffordImage.from_pil_image(img_pil)

        # Update state
        new_processed = state.regions_processed | {action.region_id}
        new_strategies = {**state.region_strategies, action.region_id: f"color_{action.color}"}

        return TemplateState(
            image=new_image,
            regions_processed=new_processed,
            region_strategies=new_strategies,
            frame_mask=state.frame_mask
        )

    def _rollout(self, state: TemplateState, regions: List[Dict], all_regions: Set[str]) -> TemplateState:
        """Fast rollout: fill remaining regions with edge-sampled colors."""
        current = state
        remaining = all_regions - state.regions_processed
        img_pil = current.image.to_pil_image()

        for region_id in remaining:
            region = next(r for r in regions if r['id'] == region_id)

            # Use edge color as default (conservative)
            default_color = sample_edge_color(img_pil, region)

            action = BlankingAction(
                region_id=region_id,
                color=default_color
            )

            current = self._apply_action(current, action, regions)
            img_pil = current.image.to_pil_image()  # Update for next iteration

        return current

    def _extract_best_solution(self, root: MCTSNode) -> TemplateState:
        """Extract best state from tree (most visited path)."""
        node = root
        while node.children:
            node = max(node.children, key=lambda n: n.visits)
        return node.state
