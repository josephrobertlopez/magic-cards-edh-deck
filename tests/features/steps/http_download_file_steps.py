"""
Behave step definitions for http/download-file skill integration tests.

Feature 009: Domain-Agnostic Skills
User Story 4: File Downloads from URLs (US4)
Success Criteria: FR-004

Note: Most step definitions are reused from http_fetch_json_steps.py
This file exists to maintain the pattern of one step file per user story.
"""

from behave import given


# ============================================================================
# Setup Steps
# ============================================================================

@given('the workflow input contains image URLs:')
def step_add_image_urls_input(context):
    """Add image URLs from table to workflow input."""
    image_urls = [row["image_url"] for row in context.table]
    context.workflow_input = {"image_urls": image_urls}
    # For batch mode, also set up items for iteration
    context.batch_items = image_urls


# All other required step definitions are already defined in http_fetch_json_steps.py:
# - "the workflow should complete successfully"
# - "the output X should be a list"
# - "the output X should contain Y"
# - "the batch result should have at least N successful items"
