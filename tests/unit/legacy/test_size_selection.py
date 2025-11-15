"""
Unit tests for size-hints based resource fetching algorithms.

Tests Euclidean distance calculation, variant selection, and dimension match scoring.
"""

import pytest
import math
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# Import actual implementations
from magic_cards.data_fetcher import (
    VariantMetadata,
    calculate_euclidean_distance,
    select_optimal_variant,
    calculate_match_score
)


# ===== T007: Test Euclidean distance calculation =====

class TestEuclideanDistance:
    """Tests for Euclidean distance calculation between variant and hint dimensions."""

    def test_identical_dimensions_zero_distance(self):
        """Given identical dimensions, distance should be 0."""
        distance = calculate_euclidean_distance(750, 1050, 750, 1050)
        assert distance == 0.0

    def test_distance_formula_correct(self):
        """Verify Euclidean distance formula: sqrt((w1-w2)² + (h1-h2)²)"""
        # Variant: 488×680, Hint: 750×1050
        # Expected: sqrt((488-750)² + (680-1050)²) = sqrt(68644 + 136900) = sqrt(205544) ≈ 453.37
        distance = calculate_euclidean_distance(488, 680, 750, 1050)
        expected = math.sqrt((488 - 750)**2 + (680 - 1050)**2)
        assert abs(distance - expected) < 0.01, f"Expected {expected}, got {distance}"

    def test_distance_symmetric(self):
        """Distance should be same regardless of argument order (variant vs hint)."""
        dist1 = calculate_euclidean_distance(500, 700, 750, 1050)
        dist2 = calculate_euclidean_distance(750, 1050, 500, 700)
        assert abs(dist1 - dist2) < 0.01

    def test_larger_dimensions_positive_distance(self):
        """Larger dimensions should produce positive distance."""
        distance = calculate_euclidean_distance(1000, 1400, 750, 1050)
        assert distance > 0

    def test_zero_dimensions_handling(self):
        """Edge case: Handle zero dimensions gracefully."""
        # This should not crash (will be edge case handling in T037)
        with pytest.raises((NotImplementedError, ZeroDivisionError, ValueError)):
            calculate_euclidean_distance(0, 0, 750, 1050)


# ===== T008: Test variant selection algorithm =====

class TestVariantSelection:
    """Tests for selecting optimal variant using Euclidean distance."""

    def test_selects_closest_variant(self):
        """Given multiple variants, should select one with smallest Euclidean distance."""
        variants = [
            VariantMetadata("url1", 488, 680, "normal"),   # distance ≈ 453
            VariantMetadata("url2", 672, 936, "large"),    # distance ≈ 139
            VariantMetadata("url3", 745, 1040, "png"),     # distance ≈ 10
        ]
        size_hints = {"width_px": 750, "height_px": 1050, "dpi": 300}

        selected = select_optimal_variant(variants, size_hints)
        assert selected.variant_name == "png", "Should select 'png' as closest match"

    def test_prefers_larger_on_equal_distance(self):
        """When distances are equal, prefer larger variant (FR-004)."""
        variants = [
            VariantMetadata("url1", 700, 1000, "variant_a"),  # Slightly smaller
            VariantMetadata("url2", 800, 1100, "variant_b"),  # Slightly larger
        ]
        # Construct size hints equidistant from both
        size_hints = {"width_px": 750, "height_px": 1050, "dpi": 300}

        selected = select_optimal_variant(variants, size_hints)
        # Should prefer larger (higher total pixel count)
        assert selected.variant_name == "variant_b", "Should prefer larger variant on tie"

    def test_single_variant_selected(self):
        """With only one variant, it should be selected."""
        variants = [VariantMetadata("url_only", 96, 96, "fixed")]
        size_hints = {"width_px": 1500, "height_px": 2100, "dpi": 600}

        selected = select_optimal_variant(variants, size_hints)
        assert selected.variant_name == "fixed"

    def test_empty_variants_returns_none(self):
        """With no variants, should return None."""
        variants = []
        size_hints = {"width_px": 750, "height_px": 1050, "dpi": 300}

        selected = select_optimal_variant(variants, size_hints)
        assert selected is None


# ===== T009: Test dimension match score calculation =====

class TestDimensionMatchScore:
    """Tests for calculating dimension match score: 1.0 - (distance / requested_diagonal)"""

    def test_perfect_match_score_1(self):
        """Identical dimensions should yield match score of 1.0."""
        score = calculate_match_score(750, 1050, 750, 1050)
        assert abs(score - 1.0) < 0.01

    def test_match_score_formula(self):
        """Verify formula: 1.0 - (distance / requested_diagonal)"""
        # Received: 745×1040, Requested: 750×1050
        # Distance: sqrt((745-750)² + (1040-1050)²) = sqrt(25 + 100) = sqrt(125) ≈ 11.18
        # Requested diagonal: sqrt(750² + 1050²) = sqrt(1665000) ≈ 1290.39
        # Score: 1.0 - (11.18 / 1290.39) ≈ 0.991

        score = calculate_match_score(745, 1040, 750, 1050)
        distance = math.sqrt((745 - 750)**2 + (1040 - 1050)**2)
        requested_diag = math.sqrt(750**2 + 1050**2)
        expected_score = 1.0 - (distance / requested_diag)

        assert abs(score - expected_score) < 0.01, f"Expected {expected_score}, got {score}"

    def test_large_mismatch_low_score(self):
        """Large dimension mismatch should produce low match score."""
        # Received: 96×96 (Pokemon fixed), Requested: 1500×2100
        score = calculate_match_score(96, 96, 1500, 2100)
        assert score < 0.2, "Large mismatch should have low score"

    def test_score_range_0_to_1(self):
        """Match score should be between 0.0 and 1.0."""
        score = calculate_match_score(500, 700, 750, 1050)
        assert 0.0 <= score <= 1.0

    def test_negative_score_clamped(self):
        """If distance > diagonal, score should be clamped to 0.0 (not negative)."""
        # Extreme mismatch: Received 10×10, Requested 1500×2100
        score = calculate_match_score(10, 10, 1500, 2100)
        assert score >= 0.0, "Score should not be negative"


# ===== T023: Regression test for backward compatibility =====

class TestBackwardCompatibility:
    """Tests for ensuring fetch works without size_hints (FR-007)."""

    def test_fetch_without_size_hints_uses_default(self):
        """When size_hints is None, should use first available URL (existing behavior)."""
        # This will be integration test - placeholder for now
        pytest.skip("T026: Implementation pending")

    def test_old_manifest_format_valid(self):
        """Manifests without new size fields should remain valid JSON."""
        # T029: Will test manifest backward compatibility
        pytest.skip("T029: Implementation pending")


# ===== T031: Test single-variant handling (fixed-size) =====

class TestFixedSizeResources:
    """Tests for handling providers with only one size (no variants)."""

    def test_accepts_fixed_size_with_low_score(self):
        """Single fixed-size variant should be accepted with appropriate match score."""
        variants = [VariantMetadata("fixed_url", 96, 96, "fixed")]
        size_hints = {"width_px": 1500, "height_px": 2100, "dpi": 600}

        selected = select_optimal_variant(variants, size_hints)
        assert selected is not None, "Should accept fixed-size resource"
        assert selected.variant_name == "fixed"

        # Calculate match score - should be very low due to large mismatch
        score = calculate_match_score(96, 96, 1500, 2100)
        assert score < 0.2, "Fixed-size mismatch should have low match score"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
