Feature: Domain-Agnostic Skills
  As a workflow author
  I want to use generic skills that work across any domain
  So that I can adapt workflows by changing configuration, not code

  Background:
    Given the A2A orchestrator is initialized
    And the skills directory is ".claude/skills"

  # ============================================================================
  # User Story 1: Reusable HTTP Requests (US1)
  # ============================================================================

  @US1 @http @scryfall
  Scenario: Fetch JSON from Scryfall API (MTG domain)
    Given a workflow named "fetch_scryfall_card"
    And the workflow has the following steps:
      """
      steps:
        - name: fetch_card
          skill: http/fetch-json
          args:
            url: "https://api.scryfall.com/cards/named?fuzzy=lightning bolt"
            method: "GET"
            timeout: 10
          outputs:
            card_data: "{{result.data}}"
            status: "{{result.status_code}}"
      """
    When I execute the workflow
    Then the workflow should complete successfully
    And the output "steps.fetch_card.outputs.card_data" should contain key "name"
    And the output "steps.fetch_card.outputs.card_data" should contain key "mana_cost"
    And the output "steps.fetch_card.outputs.status" should equal "200"

  @US1 @http @github
  Scenario: Fetch JSON from GitHub API (developer domain)
    Given a workflow named "fetch_github_user"
    And the workflow has the following steps:
      """
      steps:
        - name: fetch_user
          skill: http/fetch-json
          args:
            url: "https://api.github.com/users/octocat"
            method: "GET"
            headers:
              Accept: "application/vnd.github.v3+json"
            timeout: 10
          outputs:
            user_data: "{{result.data}}"
            status: "{{result.status_code}}"
      """
    When I execute the workflow
    Then the workflow should complete successfully
    And the output "steps.fetch_user.outputs.user_data" should contain key "login"
    And the output "steps.fetch_user.outputs.user_data" should contain key "id"
    And the output "steps.fetch_user.outputs.status" should equal "200"

  @US1 @http @retry @rate_limit
  Scenario: HTTP retry on rate limit (429)
    Given a workflow named "test_retry_429"
    And the workflow has the following steps:
      """
      batch_config:
        batch_size: 5
        max_concurrent: 2
        retry_policy:
          max_retries: 3
          retryable_errors:
            - "HTTP_429"
            - "NETWORK_TIMEOUT"

      steps:
        - name: fetch_with_retry
          skill: http/fetch-json
          batch_mode: true
          args:
            url: "https://api.scryfall.com/cards/named?fuzzy={{item}}"
            method: "GET"
            timeout: 10
          outputs:
            results: "{{result.items}}"
      """
    And the workflow input contains card names:
      | card_name          |
      | Lightning Bolt     |
      | Counterspell       |
      | Black Lotus        |
      | Ancestral Recall   |
      | Time Walk          |
    When I execute the workflow with batch mode
    Then the workflow should complete successfully
    And the output "steps.fetch_with_retry.outputs.results" should be a list
    And the batch result should have at least 3 successful items
    # Note: If rate limited (429), retries should be attempted automatically

  @US1 @http @batch
  Scenario: Batch mode processes multiple URLs in parallel
    Given a workflow named "batch_fetch_cards"
    And the workflow has the following steps:
      """
      batch_config:
        batch_size: 10
        max_concurrent: 3

      steps:
        - name: fetch_cards
          skill: http/fetch-json
          batch_mode: true
          args:
            url: "https://api.scryfall.com/cards/named?fuzzy={{item}}"
            method: "GET"
            timeout: 10
          outputs:
            cards_data: "{{result.items}}"
      """
    And the workflow input contains card names:
      | card_name          |
      | Sol Ring           |
      | Command Tower      |
      | Arcane Signet      |
      | Rhystic Study      |
      | Cyclonic Rift      |
      | Smothering Tithe   |
      | Heroic Intervention|
      | Beast Within       |
      | Swords to Plowshares |
      | Path to Exile      |
    When I execute the workflow with batch mode
    Then the workflow should complete successfully
    And the output "steps.fetch_cards.outputs.cards_data" should be a list
    And the batch result should have at least 8 successful items
    And the execution time should be less than 10 seconds

  @US1 @http @domain_agnostic @verification
  Scenario: Verify skill has zero domain-specific terminology
    Given the skill file ".claude/skills/http/fetch-json.md" exists
    When I scan the skill file for domain-specific terms
    Then the skill should not contain "card"
    And the skill should not contain "product"
    And the skill should not contain "recipe"
    And the skill should not contain "game"
    And the skill should not contain "magic"
    And the skill should not contain "shopify"
    And the skill should not contain "github"

  # ============================================================================
  # User Story 2: Universal HTML Extraction (US2)
  # ============================================================================

  @US2 @html @css_selector @card_names
  Scenario: Extract card names with .card-name selector
    Given a workflow named "extract_card_names"
    And the workflow has the following steps:
      """
      steps:
        - name: extract_names
          skill: html/extract-css
          args:
            html: |
              <html>
                <body>
                  <div class="decklist">
                    <span class="card-name">Lightning Bolt</span>
                    <span class="card-name">Counterspell</span>
                    <span class="card-name">Black Lotus</span>
                  </div>
                </body>
              </html>
            selector: ".card-name"
            extract_type: "text"
          outputs:
            card_names: "{{result.items}}"
      """
    When I execute the workflow
    Then the workflow should complete successfully
    And the output "steps.extract_names.outputs.card_names" should be a list
    And the output "steps.extract_names.outputs.card_names" should contain "Lightning Bolt"
    And the output "steps.extract_names.outputs.card_names" should contain "Counterspell"
    And the output "steps.extract_names.outputs.card_names" should contain "Black Lotus"

  @US2 @html @css_selector @product_titles
  Scenario: Extract product titles with .product-title selector
    Given a workflow named "extract_product_titles"
    And the workflow has the following steps:
      """
      steps:
        - name: extract_titles
          skill: html/extract-css
          args:
            html: |
              <html>
                <body>
                  <div class="product-grid">
                    <div class="product">
                      <h3 class="product-title">Wireless Mouse</h3>
                    </div>
                    <div class="product">
                      <h3 class="product-title">Mechanical Keyboard</h3>
                    </div>
                    <div class="product">
                      <h3 class="product-title">USB-C Hub</h3>
                    </div>
                  </div>
                </body>
              </html>
            selector: ".product-title"
            extract_type: "text"
          outputs:
            product_names: "{{result.items}}"
      """
    When I execute the workflow
    Then the workflow should complete successfully
    And the output "steps.extract_titles.outputs.product_names" should be a list
    And the output "steps.extract_titles.outputs.product_names" should contain "Wireless Mouse"
    And the output "steps.extract_titles.outputs.product_names" should contain "Mechanical Keyboard"
    And the output "steps.extract_titles.outputs.product_names" should contain "USB-C Hub"

  @US2 @html @css_selector @missing_elements
  Scenario: Graceful handling of missing elements
    Given a workflow named "extract_missing_elements"
    And the workflow has the following steps:
      """
      steps:
        - name: extract_missing
          skill: html/extract-css
          args:
            html: |
              <html>
                <body>
                  <div class="content">
                    <p>No matching elements here</p>
                  </div>
                </body>
              </html>
            selector: ".nonexistent-class"
            extract_type: "text"
          outputs:
            results: "{{result.items}}"
      """
    When I execute the workflow
    Then the workflow should complete successfully
    And the output "steps.extract_missing.outputs.results" should be a list
    And the output "steps.extract_missing.outputs.results" should be empty

  @US2 @html @css_selector @attribute_extraction
  Scenario: Attribute extraction (href from links)
    Given a workflow named "extract_links"
    And the workflow has the following steps:
      """
      steps:
        - name: extract_hrefs
          skill: html/extract-css
          args:
            html: |
              <html>
                <body>
                  <nav>
                    <a href="https://scryfall.com/card/leb/161" class="card-link">Lightning Bolt</a>
                    <a href="https://scryfall.com/card/leb/65" class="card-link">Counterspell</a>
                    <a href="https://scryfall.com/card/vma/4" class="card-link">Black Lotus</a>
                  </nav>
                </body>
              </html>
            selector: ".card-link"
            extract_type: "attribute"
            attribute_name: "href"
          outputs:
            urls: "{{result.items}}"
      """
    When I execute the workflow
    Then the workflow should complete successfully
    And the output "steps.extract_hrefs.outputs.urls" should be a list
    And the output "steps.extract_hrefs.outputs.urls" should contain "https://scryfall.com/card/leb/161"
    And the output "steps.extract_hrefs.outputs.urls" should contain "https://scryfall.com/card/leb/65"
    And the output "steps.extract_hrefs.outputs.urls" should contain "https://scryfall.com/card/vma/4"

  # ============================================================================
  # User Story 3: JSONPath Field Extraction (US3)
  # ============================================================================

  @US3 @jsonpath @nested_field
  Scenario: Extract nested field ($.image_uris.large)
    Given a workflow named "extract_nested_field"
    And the workflow has the following steps:
      """
      steps:
        - name: extract_image_url
          skill: data/extract-jsonpath
          args:
            json_data: |
              {
                "name": "Lightning Bolt",
                "image_uris": {
                  "small": "https://example.com/small.jpg",
                  "normal": "https://example.com/normal.jpg",
                  "large": "https://example.com/large.jpg"
                }
              }
            jsonpath: "$.image_uris.large"
            default_value: null
          outputs:
            image_url: "{{result.value}}"
      """
    When I execute the workflow
    Then the workflow should complete successfully
    And the output "steps.extract_image_url.outputs.image_url" should equal "https://example.com/large.jpg"

  @US3 @jsonpath @array_extraction
  Scenario: Extract array items ($.products[*].name)
    Given a workflow named "extract_array_items"
    And the workflow has the following steps:
      """
      steps:
        - name: extract_product_names
          skill: data/extract-jsonpath
          args:
            json_data: |
              {
                "products": [
                  {"id": 1, "name": "Widget Pro"},
                  {"id": 2, "name": "Super Tool"},
                  {"id": 3, "name": "Mega Device"}
                ]
              }
            jsonpath: "$.products[*].name"
            default_value: []
          outputs:
            product_names: "{{result.items}}"
      """
    When I execute the workflow
    Then the workflow should complete successfully
    And the output "steps.extract_product_names.outputs.product_names" should be a list
    And the output "steps.extract_product_names.outputs.product_names" should contain "Widget Pro"
    And the output "steps.extract_product_names.outputs.product_names" should contain "Super Tool"
    And the output "steps.extract_product_names.outputs.product_names" should contain "Mega Device"

  @US3 @jsonpath @default_value
  Scenario: Default value for missing fields
    Given a workflow named "extract_with_default"
    And the workflow has the following steps:
      """
      steps:
        - name: extract_missing_field
          skill: data/extract-jsonpath
          args:
            json_data: |
              {
                "name": "Product X",
                "price": 19.99
              }
            jsonpath: "$.description"
            default_value: "N/A"
          outputs:
            description: "{{result.value}}"
      """
    When I execute the workflow
    Then the workflow should complete successfully
    And the output "steps.extract_missing_field.outputs.description" should equal "N/A"

  # ============================================================================
  # User Story 4: File Downloads from URLs (US4)
  # ============================================================================

  @US4 @http @download @batch
  Scenario: Batch download multiple image URLs
    Given a workflow named "batch_download_images"
    And the workflow has the following steps:
      """
      batch_config:
        batch_size: 10
        max_concurrent: 3

      steps:
        - name: download_images
          skill: http/download-file
          batch_mode: true
          args:
            url: "{{item}}"
            output_dir: "/tmp/test_downloads"
            overwrite: true
            timeout: 60
          outputs:
            downloaded_files: "{{result.items}}"
      """
    And the workflow input contains image URLs:
      | image_url |
      | https://example.com/image1.jpg |
      | https://example.com/image2.jpg |
      | https://example.com/image3.jpg |
      | https://example.com/image4.jpg |
      | https://example.com/image5.jpg |
    When I execute the workflow with batch mode
    Then the workflow should complete successfully
    And the output "steps.download_images.outputs.downloaded_files" should be a list
    And the batch result should have at least 3 successful items

  @US4 @http @download @overwrite
  Scenario: Skip download if file exists (overwrite=false)
    Given a workflow named "download_with_skip"
    And the workflow has the following steps:
      """
      steps:
        - name: download_file
          skill: http/download-file
          args:
            url: "https://example.com/test.pdf"
            output_dir: "/tmp/test_downloads"
            filename: "test.pdf"
            overwrite: false
            timeout: 30
          outputs:
            file_path: "{{result.path}}"
            skipped: "{{result.skipped}}"
      """
    When I execute the workflow
    Then the workflow should complete successfully
    And the output "steps.download_file.outputs.file_path" should contain "test.pdf"

  @US4 @http @download @timeout
  Scenario: Timeout handling for slow downloads
    Given a workflow named "download_with_timeout"
    And the workflow has the following steps:
      """
      steps:
        - name: download_large_file
          skill: http/download-file
          args:
            url: "https://example.com/large-file.zip"
            output_dir: "/tmp/test_downloads"
            timeout: 300
          outputs:
            file_path: "{{result.path}}"
            file_size: "{{result.size_bytes}}"
      """
    When I execute the workflow
    Then the workflow should complete successfully
    And the output "steps.download_large_file.outputs.file_path" should contain "large-file.zip"

  # ============================================================================
  # User Story 5: Grid Layout Documents (US5)
  # ============================================================================

  @US5 @document @grid_layout @slide_count
  Scenario: 100 images in 3×3 grid generates 12 slides
    Given a workflow named "create_3x3_grid"
    And the workflow has the following steps:
      """
      steps:
        - name: generate_presentation
          skill: document/grid-layout
          args:
            image_paths: "{{images_100}}"
            rows: 3
            columns: 3
            output_path: "/tmp/test_presentations/grid_3x3.pptx"
            slide_width: 10
            slide_height: 7.5
          outputs:
            pptx_path: "{{result.path}}"
            slide_count: "{{result.slide_count}}"
            images_per_slide: "{{result.images_per_slide}}"
      """
    When I execute the workflow
    Then the workflow should complete successfully
    And the output "steps.generate_presentation.outputs.pptx_path" should contain "grid_3x3.pptx"
    And the output "steps.generate_presentation.outputs.slide_count" should equal "12"
    And the output "steps.generate_presentation.outputs.images_per_slide" should equal "9"

  @US5 @document @grid_layout @custom_grid
  Scenario: 50 images in 5×2 grid generates 5 slides
    Given a workflow named "create_5x2_grid"
    And the workflow has the following steps:
      """
      steps:
        - name: generate_presentation
          skill: document/grid-layout
          args:
            image_paths: "{{images_50}}"
            rows: 5
            columns: 2
            output_path: "/tmp/test_presentations/grid_5x2.pptx"
            slide_width: 10
            slide_height: 7.5
          outputs:
            pptx_path: "{{result.path}}"
            slide_count: "{{result.slide_count}}"
      """
    When I execute the workflow
    Then the workflow should complete successfully
    And the output "steps.generate_presentation.outputs.pptx_path" should contain "grid_5x2.pptx"
    And the output "steps.generate_presentation.outputs.slide_count" should equal "5"

  @US5 @document @grid_layout @missing_images
  Scenario: Missing image files show placeholder text
    Given a workflow named "create_grid_with_missing"
    And the workflow has the following steps:
      """
      steps:
        - name: generate_presentation
          skill: document/grid-layout
          args:
            image_paths:
              - "/tmp/images/exists1.jpg"
              - "/tmp/images/missing1.jpg"
              - "/tmp/images/exists2.jpg"
              - "/tmp/images/missing2.jpg"
            rows: 2
            columns: 2
            output_path: "/tmp/test_presentations/grid_with_missing.pptx"
            placeholder_text: "Image Not Found"
          outputs:
            pptx_path: "{{result.path}}"
            missing_count: "{{result.missing_images_count}}"
      """
    When I execute the workflow
    Then the workflow should complete successfully
    And the output "steps.generate_presentation.outputs.pptx_path" should contain "grid_with_missing.pptx"
    And the output "steps.generate_presentation.outputs.missing_count" should equal "2"

  # ============================================================================
  # User Story 6: Document Format Conversion (US6)
  # ============================================================================

  @US6 @document @convert_format @pptx_to_pdf
  Scenario: PPTX to PDF conversion with high quality
    Given a workflow named "convert_pptx_to_pdf"
    And the workflow has the following steps:
      """
      steps:
        - name: convert_presentation
          skill: document/convert-format
          args:
            input_file: "/tmp/test_presentations/sample.pptx"
            output_format: "pdf"
            quality: "high"
          outputs:
            pdf_path: "{{result.path}}"
            file_size: "{{result.size_bytes}}"
      """
    When I execute the workflow
    Then the workflow should complete successfully
    And the output "steps.convert_presentation.outputs.pdf_path" should contain ".pdf"

  @US6 @document @convert_format @docx_to_pdf
  Scenario: DOCX to PDF preserves formatting
    Given a workflow named "convert_docx_to_pdf"
    And the workflow has the following steps:
      """
      steps:
        - name: convert_document
          skill: document/convert-format
          args:
            input_file: "/tmp/test_documents/sample.docx"
            output_format: "pdf"
            quality: "medium"
          outputs:
            pdf_path: "{{result.path}}"
      """
    When I execute the workflow
    Then the workflow should complete successfully
    And the output "steps.convert_document.outputs.pdf_path" should contain ".pdf"

  @US6 @document @convert_format @pptx_to_png
  Scenario: PPTX to PNG creates one PNG per slide
    Given a workflow named "convert_pptx_to_png"
    And the workflow has the following steps:
      """
      steps:
        - name: convert_to_images
          skill: document/convert-format
          args:
            input_file: "/tmp/test_presentations/sample.pptx"
            output_format: "png"
            output_dir: "/tmp/test_png_output"
          outputs:
            image_paths: "{{result.items}}"
            image_count: "{{result.count}}"
      """
    When I execute the workflow
    Then the workflow should complete successfully
    And the output "steps.convert_to_images.outputs.image_count" should equal "3"
