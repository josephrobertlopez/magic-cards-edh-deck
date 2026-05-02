Feature: Thematic EDH Deck Builder using Scryfall Tags
  As a player building thematic EDH decks
  I want to construct decks using community art/card tags as selection criteria
  So that I can build coherent, flavor-rich decks with specific representation themes

  Background:
    Given I have access to Scryfall Tagger API for card tags
    And I have EDH format validation rules
    And I can search Scryfall for card data

  Scenario: Find cards matching a single tag theme
    When I search for cards with tag "bear"
    Then I should get a list of cards with bear-related artwork
    And each card should have name, set, collector_number, and tags data
    And cards should be sorted by tag weight (most relevant first)

  Scenario: Filter cards by multiple tag criteria
    When I search for cards with ALL tags: ["achillean", "cute"]
    Then I should get cards that have BOTH tags
    And results should prioritize cards with high tag weights
    And results should be limited to cards with explicit both tags (AND logic)

  Scenario: Build a coherent themed deck
    When I build a deck with theme: "furry_gay_male"
    And I specify color identity: "Boros" (Red/White)
    And I specify minimum tag relevance score: 0.5
    Then I should get a 100-card deck
    And the deck should include a valid EDH commander
    And at least 40% of non-land cards should have thematic tags
    And the mana curve should be playable (not skewed)
    And all cards must match the color identity

  Scenario: Prioritize representation tags over generic animals
    When I build a "queer representation" themed deck
    And I assign weights: achillean=3.0, trans male=3.0, romantic couple=2.5, bear=1.0, animal=0.5
    Then cards with achillean/trans male tags should rank highest
    And generic "animal" tags should only fill gaps
    And the deck should have at least 2-3 explicitly LGBTQ+ tagged cards

  Scenario: Suggest a thematic commander
    When I request a commander for theme "furry_gay_male" with colors "Boros"
    Then I should get 1-3 commander suggestions
    And each suggestion should have high thematic tag alignment
    And suggestions should be legendary creatures or "can be commander"
    And each suggestion should include reason for match

  Scenario: Validate deck format compliance
    When I validate a 100-card themed deck
    Then I should verify: exactly 100 cards
    And verify: singleton (except basic lands)
    And verify: all cards match commander color identity
    And verify: all cards are legal in EDH format
    And return a validation report with any violations

  Scenario: Generate printable decklist with tag annotations
    When I export a themed deck to decklist format
    Then each line should show card name with tag counts
    Example:
      | card_name              | tags_shown          | count |
      | Ajani, Adversary       | [achillean:2]       | 1     |
      | Mountain               | []                  | 36    |
      | Anthem Effects         | [cute, smile]       | 8     |

  Scenario: Handle missing or unknown tag data gracefully
    When I try to build a deck with cards missing Tagger data
    Then I should log which cards lack tag data
    And I should still include them if they fit the color identity
    And I should warn the user about incomplete tag coverage
    And the deck should remain valid (not fail)

  Scenario: Reusable theme configuration system
    When I load theme configuration from "tag_themes.yaml"
    And I select preset "furry_gay_male"
    Then I should get:
      | key           | value                                      |
      | name          | furry_gay_male                             |
      | tag_weights   | achillean:3.0, trans male:3.0, bear:1.0  |
      | min_threshold | 0.5                                        |
      | description   | Queer furry celebration deck               |
    And I should be able to override any weight at runtime
