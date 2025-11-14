Feature: Size-Hints Based Resource Fetching
  As a user fetching card images
  I want to specify target dimensions via size hints
  So that I get optimally-sized images for my print template

  Background:
    Given the fetch-from-api skill exists
    And the data_fetcher module supports size hints

  # ===== USER STORY 1: Fetch Resources with Optimal Dimensions =====

  Scenario: Fetch with size hints selects closest variant
    Given an API that offers multiple size variants:
      | variant_name | width_px | height_px |
      | normal       | 488      | 680       |
      | large        | 672      | 936       |
      | png          | 745      | 1040      |
    When I fetch resources with size hints:
      | width_px | height_px | dpi |
      | 750      | 1050      | 300 |
    Then the fetcher should select the "png" variant
    And the dimension_match_score should be greater than 0.9
    And the selection_rationale should explain why "png" was chosen

  Scenario: Fetch with size hints records dimension metadata
    Given an API that returns a resource at 745×1040 pixels
    When I fetch with size hints requesting 750×1050 pixels
    Then the manifest should contain:
      | field               | value           |
      | size_requested      | {"width_px": 750, "height_px": 1050} |
      | size_received       | {"width_px": 745, "height_px": 1040} |
      | dimension_match_score | >0.9          |
      | variant_selected    | png             |
    And the selection_rationale should be present

  Scenario: Size selection completes within performance budget
    Given 10 resources to fetch with size hints
    When I measure the variant selection overhead per resource
    Then the selection time should be less than 100ms per resource

  # ===== USER STORY 2: Maintain Backward Compatibility =====

  Scenario: Fetch without size hints uses default behavior
    Given a decklist with 5 cards
    When I run fetch-from-api WITHOUT the --size-hints parameter
    Then the fetch should complete successfully
    And the manifest should NOT contain size_requested fields
    And the manifest should NOT contain dimension_match_score fields
    And the behavior should be identical to the old implementation

  Scenario: Old manifest files remain valid JSON
    Given an existing manifest file from before size-hints feature
    When I run a new fetch that extends the manifest
    Then the manifest should remain valid JSON
    And the old entries should have no new fields
    And the new entries should have optional size fields

  Scenario: Malformed size hints fall back gracefully
    Given a fetch command with invalid JSON in --size-hints
    When the fetcher validates the size_hints parameter
    Then it should log a warning about malformed input
    And it should fall back to default fetch behavior (no size optimization)
    And the fetch should still complete successfully

  # ===== USER STORY 3: Handle Fixed-Size Resources =====

  Scenario: Accept fixed-size resource with low match score
    Given an API that returns only a fixed 96×96 pixel image
    When I fetch with size hints requesting 1500×2100 pixels
    Then the fetcher should accept the 96×96 image
    And the dimension_match_score should be less than 0.2
    And the variant_selected should be "fixed"
    And the selection_rationale should explain "Provider offers fixed size only"

  Scenario: Pokemon API fixed-size sprites
    Given the Pokemon API returns fixed 96×96 sprites
    When I fetch Pikachu with size hints 1500×2100
    Then the fetch should succeed
    And the manifest should show large dimension mismatch
    And the selection_rationale should explain fixed-size acceptance

  # ===== EDGE CASES =====

  Scenario: Equal distance variants prefer larger
    Given an API that offers variants:
      | variant_name | width_px | height_px |
      | smaller      | 700      | 1000      |
      | larger       | 800      | 1100      |
    When I fetch with size hints 750×1050 (equidistant from both)
    Then the fetcher should select the "larger" variant
    And the selection_rationale should mention "higher pixel count"

  Scenario: Single variant always selected
    Given an API that returns only one variant
    When I fetch with any size hints
    Then that single variant should be selected
    And the dimension_match_score should reflect actual mismatch

  Scenario: No variants available fails gracefully
    Given an API response with no image URLs
    When I attempt to fetch with size hints
    Then the fetch should fail with clear error message
    And the error should indicate "No image URLs found"

  # ===== INTEGRATION WITH WORKFLOW =====

  Scenario: End-to-end workflow with size hints
    Given a decklist file "decklists/test_deck.txt" with 3 cards
    And a template with 600 DPI requirement
    When I run the fetch-from-api skill with:
      | parameter     | value                          |
      | decklist      | decklists/test_deck.txt        |
      | output_dir    | /tmp/test-fetch                |
      | size_hints    | {"width_px": 1500, "height_px": 2100, "dpi": 600} |
    Then all 3 cards should be fetched successfully
    And the manifest should show dimension_match_score for each card
    And at least 95% of cards should have match_score >= 0.85
