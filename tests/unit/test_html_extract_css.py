"""
Unit tests for html/extract-css skill

Tests cover:
- Text extraction from various HTML structures
- Attribute extraction (href, src, data-* attributes)
- HTML content extraction
- CSS selector support (class, ID, tag, attribute selectors)
- Empty/missing element handling
- Malformed HTML tolerance
"""

import pytest
from bs4 import BeautifulSoup


# Mock the skill execution function
# In actual implementation, this would import from the skill's Python module


def execute_html_extract_css(args):
    """
    Mock implementation of html/extract-css skill execution.
    This matches the contract from contracts/html-extract-css.md
    """
    html_content = args["html_content"]
    selector = args["selector"]
    extract_type = args.get("extract_type", "text")
    attribute_name = args.get("attribute_name")
    default_value = args.get("default_value", [])

    # Load HTML (from string - file loading not implemented in mock)
    if html_content.startswith("/"):
        raise FileNotFoundError(f"FILE_NOT_FOUND: {html_content}")

    # Parse HTML
    soup = BeautifulSoup(html_content, 'lxml')

    # Find elements
    try:
        elements = soup.select(selector)
    except Exception:
        return {"items": default_value, "count": 0, "error": "INVALID_SELECTOR"}

    # Extract data
    items = []
    for element in elements:
        if extract_type == "text":
            items.append(element.get_text(strip=True))
        elif extract_type == "attribute":
            items.append(element.get(attribute_name, ""))
        elif extract_type == "html":
            items.append(str(element))

    # Return results
    if not items:
        items = default_value

    return {
        "items": items,
        "count": len(items)
    }


# ============================================================================
# Unit Tests
# ============================================================================

def test_extract_text_from_class_selector():
    """Test basic text extraction using class selector."""
    html = """
    <html>
      <body>
        <div class="card-name">Lightning Bolt</div>
        <div class="card-name">Counterspell</div>
        <div class="card-name">Black Lotus</div>
      </body>
    </html>
    """

    result = execute_html_extract_css({
        "html_content": html,
        "selector": ".card-name",
        "extract_type": "text"
    })

    assert result["count"] == 3
    assert "Lightning Bolt" in result["items"]
    assert "Counterspell" in result["items"]
    assert "Black Lotus" in result["items"]


def test_extract_text_from_id_selector():
    """Test text extraction using ID selector."""
    html = """
    <html>
      <body>
        <div id="main-content">Welcome to our site</div>
      </body>
    </html>
    """

    result = execute_html_extract_css({
        "html_content": html,
        "selector": "#main-content",
        "extract_type": "text"
    })

    assert result["count"] == 1
    assert result["items"][0] == "Welcome to our site"


def test_extract_text_from_tag_selector():
    """Test text extraction using tag selector."""
    html = """
    <html>
      <body>
        <p>First paragraph</p>
        <p>Second paragraph</p>
        <p>Third paragraph</p>
      </body>
    </html>
    """

    result = execute_html_extract_css({
        "html_content": html,
        "selector": "p",
        "extract_type": "text"
    })

    assert result["count"] == 3
    assert "First paragraph" in result["items"]
    assert "Second paragraph" in result["items"]
    assert "Third paragraph" in result["items"]


def test_extract_attribute_href():
    """Test attribute extraction for href attributes."""
    html = """
    <html>
      <body>
        <nav>
          <a href="https://scryfall.com/card/123" class="card-link">Card 1</a>
          <a href="https://scryfall.com/card/456" class="card-link">Card 2</a>
        </nav>
      </body>
    </html>
    """

    result = execute_html_extract_css({
        "html_content": html,
        "selector": ".card-link",
        "extract_type": "attribute",
        "attribute_name": "href"
    })

    assert result["count"] == 2
    assert "https://scryfall.com/card/123" in result["items"]
    assert "https://scryfall.com/card/456" in result["items"]


def test_extract_attribute_src():
    """Test attribute extraction for src attributes."""
    html = """
    <html>
      <body>
        <img src="/images/product1.jpg" class="product-image">
        <img src="/images/product2.jpg" class="product-image">
      </body>
    </html>
    """

    result = execute_html_extract_css({
        "html_content": html,
        "selector": ".product-image",
        "extract_type": "attribute",
        "attribute_name": "src"
    })

    assert result["count"] == 2
    assert "/images/product1.jpg" in result["items"]
    assert "/images/product2.jpg" in result["items"]


def test_extract_attribute_data_attribute():
    """Test extraction of custom data-* attributes."""
    html = """
    <html>
      <body>
        <div data-id="123" class="item">Item 1</div>
        <div data-id="456" class="item">Item 2</div>
      </body>
    </html>
    """

    result = execute_html_extract_css({
        "html_content": html,
        "selector": ".item",
        "extract_type": "attribute",
        "attribute_name": "data-id"
    })

    assert result["count"] == 2
    assert "123" in result["items"]
    assert "456" in result["items"]


def test_extract_html_content():
    """Test HTML content extraction."""
    html = """
    <html>
      <body>
        <article class="post">
          <h2>Title</h2>
          <p>Content here</p>
        </article>
      </body>
    </html>
    """

    result = execute_html_extract_css({
        "html_content": html,
        "selector": "article.post",
        "extract_type": "html"
    })

    assert result["count"] == 1
    assert "<h2>Title</h2>" in result["items"][0]
    assert "<p>Content here</p>" in result["items"][0]


def test_empty_result_no_matches():
    """Test graceful handling when no elements match."""
    html = """
    <html>
      <body>
        <div class="content">No matching elements</div>
      </body>
    </html>
    """

    result = execute_html_extract_css({
        "html_content": html,
        "selector": ".nonexistent-class",
        "extract_type": "text"
    })

    assert result["count"] == 0
    assert result["items"] == []


def test_empty_result_with_custom_default():
    """Test custom default value when no matches."""
    html = """
    <html>
      <body>
        <div class="content">No matching elements</div>
      </body>
    </html>
    """

    result = execute_html_extract_css({
        "html_content": html,
        "selector": ".nonexistent-class",
        "extract_type": "text",
        "default_value": ["N/A"]
    })

    assert result["count"] == 0
    assert result["items"] == ["N/A"]


def test_descendant_selector():
    """Test descendant combinator selector."""
    html = """
    <html>
      <body>
        <div class="decklist">
          <span class="card-name">Lightning Bolt</span>
        </div>
        <span class="card-name">Counterspell</span>
      </body>
    </html>
    """

    result = execute_html_extract_css({
        "html_content": html,
        "selector": ".decklist .card-name",
        "extract_type": "text"
    })

    # Should only match the card-name INSIDE decklist
    assert result["count"] == 1
    assert result["items"][0] == "Lightning Bolt"


def test_child_selector():
    """Test child combinator selector (>)."""
    html = """
    <html>
      <body>
        <ul class="list">
          <li class="item">Direct child</li>
          <div>
            <li class="item">Nested child</li>
          </div>
        </ul>
      </body>
    </html>
    """

    result = execute_html_extract_css({
        "html_content": html,
        "selector": ".list > .item",
        "extract_type": "text"
    })

    # Should only match direct children
    assert result["count"] == 1
    assert result["items"][0] == "Direct child"


def test_attribute_selector():
    """Test attribute existence selector."""
    html = """
    <html>
      <body>
        <a href="https://example.com/page1" data-type="external">Link 1</a>
        <a href="/page2">Link 2</a>
        <a href="https://example.com/page3" data-type="external">Link 3</a>
      </body>
    </html>
    """

    result = execute_html_extract_css({
        "html_content": html,
        "selector": "a[data-type]",
        "extract_type": "text"
    })

    assert result["count"] == 2
    assert "Link 1" in result["items"]
    assert "Link 3" in result["items"]


def test_multiple_selector():
    """Test comma-separated multiple selectors."""
    html = """
    <html>
      <body>
        <h1 class="title">Main Title</h1>
        <h2 class="subtitle">Subtitle</h2>
        <p class="content">Paragraph</p>
      </body>
    </html>
    """

    result = execute_html_extract_css({
        "html_content": html,
        "selector": ".title, .subtitle",
        "extract_type": "text"
    })

    assert result["count"] == 2
    assert "Main Title" in result["items"]
    assert "Subtitle" in result["items"]


def test_malformed_html_tolerance():
    """Test that malformed HTML is parsed gracefully."""
    html = """
    <html>
      <body>
        <div class="item">Item 1
        <div class="item">Item 2</div>
      </body>
    """  # Note: missing closing div for Item 1

    result = execute_html_extract_css({
        "html_content": html,
        "selector": ".item",
        "extract_type": "text"
    })

    # Should still extract both items despite malformed HTML
    assert result["count"] == 2


def test_missing_attribute_returns_empty_string():
    """Test that missing attributes return empty string."""
    html = """
    <html>
      <body>
        <a href="https://example.com">Link with href</a>
        <a>Link without href</a>
      </body>
    </html>
    """

    result = execute_html_extract_css({
        "html_content": html,
        "selector": "a",
        "extract_type": "attribute",
        "attribute_name": "href"
    })

    assert result["count"] == 2
    assert "https://example.com" in result["items"]
    assert "" in result["items"]  # Missing href returns empty string


def test_whitespace_stripping():
    """Test that extracted text has whitespace stripped."""
    html = """
    <html>
      <body>
        <div class="item">

          Text with lots of whitespace

        </div>
      </body>
    </html>
    """

    result = execute_html_extract_css({
        "html_content": html,
        "selector": ".item",
        "extract_type": "text"
    })

    assert result["items"][0] == "Text with lots of whitespace"


def test_invalid_selector_error():
    """Test error handling for invalid CSS selector."""
    html = "<html><body><div>Content</div></body></html>"

    result = execute_html_extract_css({
        "html_content": html,
        "selector": "[[invalid selector]]",
        "extract_type": "text"
    })

    assert "error" in result
    assert result["error"] == "INVALID_SELECTOR"
    assert result["count"] == 0
    assert result["items"] == []


def test_file_not_found_error():
    """Test error handling for file not found."""
    with pytest.raises(FileNotFoundError) as exc_info:
        execute_html_extract_css({
            "html_content": "/nonexistent/file.html",
            "selector": ".item",
            "extract_type": "text"
        })

    assert "FILE_NOT_FOUND" in str(exc_info.value)
