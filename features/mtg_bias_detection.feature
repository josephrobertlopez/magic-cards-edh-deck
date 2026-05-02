Feature: MTG Card Design Bias Detection
  As a diversity researcher
  I want to analyze MTG card design for systematic bias across representation groups
  So that I can identify and advocate for more inclusive card design

  Background:
    Given a bias detector with random seed 42
    And mock Scryfall card data available
    And mock card tagging data available

  Scenario: Collect card data for bias analysis
    Given a card list with 10 cards
    When I collect card data for bias analysis
    Then I should have a DataFrame with 10 records
    And the DataFrame should have columns for mechanics, complexity, power, and representation groups

  Scenario: Detect division by zero in disparate impact calculation
    Given a card dataset where one group has mean value 0.0
    And the control group has mean value 0.0
    When I analyze representation bias
    Then it should handle the division by zero gracefully
    And return a result with DI ratio of 1.0 for equal values

  Scenario: Calculate complexity score from oracle text
    Given a card with oracle text "When Ajani enters, create a 2/1 white cat creature token"
    When I calculate its complexity score
    Then the score should be between 0 and 10
    And the score should reflect the presence of "when" and multiple clauses

  Scenario: Calculate power level score with efficiency factor
    Given a card with high-power indicator "exile" costing "{W}{W}" (2 mana)
    When I calculate its power score
    Then the score should reflect both the power indicator and mana efficiency
    And the score should be between 0 and 10

  Scenario: Extract mechanics from oracle text
    Given a card with oracle text containing "draw", "search", and "destroy"
    When I extract mechanics
    Then I should identify "draw", "search", and "destroy" as mechanics

  Scenario: Build custom representation profile
    Given a representation profile named "furry_gay_uwu"
    And the profile includes tags: anthropomorphic, lgbtq, achillean, sapphic
    When I create a detector with this custom profile
    Then the detector should recognize cards matching this profile
    And cards with anthropomorphic+lgbtq tags should be tagged as furry_gay_uwu

  Scenario: Analyze bias with insufficient samples
    Given a card dataset with only 2 cards in a representation group
    When I analyze representation bias
    Then the analysis should skip that group
    And output a warning message about insufficient samples

  Scenario: Export bias analysis results to JSON
    Given a completed bias analysis with results
    When I export the results to JSON
    Then the JSON should contain all group statistics
    And the JSON should include confidence intervals
    And the JSON should include mechanic analysis

  Scenario: Export bias analysis results to CSV
    Given a completed bias analysis with results
    When I export the results to CSV
    Then the CSV should have rows for each group/metric combination
    And the CSV should include disparate impact ratio
    And the CSV should include group sample counts

  Scenario: Generate deck recommendations based on bias findings
    Given a bias analysis showing LGBTQ+ cards have lower power scores
    When I generate upgrade recommendations
    Then recommendations should prioritize LGBTQ+ cards to address bias
    And recommendations should maintain color identity constraints

  Scenario: Compare two decklists for representation balance
    Given two decklists with different diversity profiles
    When I compare their representation metrics
    Then I should see the breakdown by representation group for each list
    And the comparison should highlight representation gaps

  Scenario: Analyze mechanic bias across representation groups
    Given a card dataset with mechanics tagged by representation group
    When I perform detailed mechanic analysis
    Then I should identify over-represented mechanics (ratio > 1.5x)
    And I should identify under-represented mechanics (ratio < 0.67x)
    And results should show which groups lack certain mechanics

  Scenario: Validate representation group membership
    Given a card with tags ["anthropomorphic", "bearscape"]
    When I check representation group membership
    Then the card should be marked as anthropomorphic group
    And I should be able to query cards by group membership
