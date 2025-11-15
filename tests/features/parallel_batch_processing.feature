# Feature 010: Parallel Batch Processing for A2A Orchestrator
# Success Criteria: SC-001 (≤2 min), SC-002 (≥10x speedup), SC-007 (preserve caching)

Feature: Parallel Batch Processing for Commander Proxy Generation
  As a Commander player
  I want to generate proxies with parallel batch processing
  So that I can get my 100-card deck in ≤2 minutes instead of ≥15 minutes

  Background:
    Given the A2A orchestrator is initialized
    And batch processing is enabled with batch_size 10 and max_concurrent 3

  @critical @sc-002
  Scenario: SC-002 - Parallel batch processing achieves 10x speedup
    Given I have a mock Scryfall API with 200ms latency per card
    And I have a decklist with 100 cards
    When I execute the workflow with batch processing enabled
    Then the workflow should complete in less than 10 seconds
    And the sequential baseline would take at least 20 seconds
    And the speedup factor should be at least 10x

  @critical @sc-001
  Scenario: SC-001 - Commander deck proxies generated in under 2 minutes
    Given I have a real Scryfall API connection
    And I have the "Atraxa, Praetors' Voice" commander deck with 100 cards
    When I execute the commander_to_proxies workflow
    Then the workflow should complete in less than 120 seconds
    And a PPTX file should be generated with 12 slides
    And each slide should contain 9 card images

  @critical @sc-007
  Scenario: SC-007 - Message caching performance preserved (25x speedup)
    Given I have a workflow with cacheable steps
    When I execute the workflow for the first time
    And I record the execution time as "baseline"
    And I execute the same workflow a second time
    And I record the execution time as "cached"
    Then the cached execution time should be at least 23.75x faster than baseline
    And the cache hit rate should be at least 95%

  @batch-processing
  Scenario: Batch processor splits items into batches correctly
    Given I have a list of 100 items
    And batch_size is configured as 10
    When the batch processor processes the items
    Then 10 batches should be created
    And each batch should contain 10 items
    And batches should execute concurrently with max_concurrent limit

  @batch-processing
  Scenario: Batch processor respects max_concurrent limit
    Given I have a list of 50 items
    And batch_size is 10 (creating 5 batches)
    And max_concurrent is 3
    When the batch processor processes the items
    Then at most 3 batches should execute simultaneously
    And all 5 batches should complete successfully

  @error-handling @partial-success
  Scenario: Partial success handling when ≥50% items succeed
    Given I have a list of 100 items in 10 batches
    And 7 batches will have all items succeed
    And 3 batches will have all items fail
    When the batch processor processes the items
    Then the workflow should complete successfully
    And the result should show 70 successful items
    And the result should show 30 failed items
    And the execution manifest should log all failures

  @error-handling @partial-failure @wip
  Scenario: Workflow fails when <50% batches complete
    Given I have a list of 100 items in 10 batches
    And 4 batches will complete successfully
    And 6 batches will throw exceptions
    When the batch processor processes the items
    Then a BatchProcessingError should be raised
    And the error message should mention "partial success threshold"
    # NOTE: Requires batch processor architectural changes - deferred for Phase 4

  @retry-logic
  Scenario: Exponential backoff retries transient errors
    Given I have a mock API that returns 429 rate limit on first 2 attempts
    And the retry policy is exponential_backoff with max_retries 3
    When the batch processor fetches a card
    Then the first attempt should fail with HTTP_429
    And the second attempt should retry after 1 second
    And the third attempt should retry after 2 seconds
    And the fourth attempt should succeed
    And the total retry count should be 2

  @retry-logic
  Scenario: Permanent errors skip retry logic
    Given I have a mock API that returns 404 not found
    And the retry policy is exponential_backoff
    When the batch processor fetches a card named "InvalidCard"
    Then the request should fail immediately
    And no retries should be attempted
    And the error_type should be "HTTP_404"

  @manifest-logging
  Scenario: Execution manifest logs batch events to JSONL
    Given I have a workflow with batch processing enabled
    When I execute the workflow with 50 items
    Then an execution manifest should be created in .execution_manifests/
    And the manifest should contain a "workflow_start" event
    And the manifest should contain 5 "batch_start" events
    And the manifest should contain 5 "batch_complete" events
    And each batch_complete event should include success_count and failure_count

  @contract-validation
  Scenario: Workflow validation catches invalid batch_config at load time
    Given I have a workflow with invalid batch_size 0
    When I try to load the workflow
    Then a WorkflowValidationError should be raised
    And the error message should mention "batch_size must be > 0"

  @contract-validation
  Scenario: Workflow validation catches invalid max_concurrent
    Given I have a workflow with max_concurrent -1
    When I try to load the workflow
    Then a WorkflowValidationError should be raised
    And the error message should mention "max_concurrent must be > 0"

  @circular-dependency
  Scenario: Circular dependency detection at workflow load time
    Given I have workflow A that calls workflow B
    And workflow B calls workflow A
    When I try to load workflow A
    Then a WorkflowValidationError should be raised
    And the error message should show the circular path "A → B → A"
