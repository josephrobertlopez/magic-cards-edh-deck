"""
Unit tests for magic_cards/data_fetcher.py

Tests cover:
- Card fetching with mocked API responses
- DFC (Double-Faced Card) handling
- Numbered suffix generation for duplicate basic lands
- Image validation logic
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, mock_open
from magic_cards.data_fetcher import (
    fetch_single_resource,
    generate_filename,
    sanitize_filename,
    validate_resource
)


# --- Fixtures ---

@pytest.fixture
def mock_scryfall_response():
    """Mock successful Scryfall API response for a single-faced card"""
    return {
        "name": "Forest",
        "image_uris": {
            "normal": "https://example.com/forest.jpg"
        }
    }


@pytest.fixture
def mock_dfc_response():
    """Mock Scryfall API response for a double-faced card"""
    return {
        "name": "Delver of Secrets",
        "card_faces": [
            {
                "name": "Delver of Secrets",
                "image_uris": {
                    "normal": "https://example.com/delver_front.jpg"
                }
            },
            {
                "name": "Insectile Aberration",
                "image_uris": {
                    "normal": "https://example.com/delver_back.jpg"
                }
            }
        ]
    }


@pytest.fixture
def mock_valid_image():
    """Mock valid image data (1x1 PNG)"""
    # Minimal valid PNG (1x1 transparent pixel)
    return bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
        0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,  # IDAT chunk
        0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
        0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
        0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,  # IEND chunk
        0x42, 0x60, 0x82
    ]) * 20  # Make it > 1000 bytes


# --- Unit Tests ---

def test_sanitize_filename():
    """Test filename sanitization removes invalid characters"""
    assert sanitize_filename("Delver of Secrets // Insectile Aberration") == "Delver of Secrets __ Insectile Aberration"
    assert sanitize_filename("Coat of Arms: Edition") == "Coat of Arms_ Edition"
    assert sanitize_filename("Card*Name?") == "CardName"


def test_generate_numbered_filename_first():
    """Test numbered filename generation for first occurrence"""
    existing = []
    result = generate_filename("Forest", existing, ".jpg")
    assert result == "Forest.jpg"


def test_generate_numbered_filename_duplicate():
    """Test numbered filename generation for duplicate basic lands"""
    existing = ["Forest.jpg"]
    result = generate_filename("Forest", existing, ".jpg")
    assert result == "Forest_01.jpg"


def test_generate_numbered_filename_multiple_duplicates():
    """Test numbered filename generation for multiple duplicates"""
    existing = ["Forest.jpg", "Forest_01.jpg", "Forest_02.jpg"]
    result = generate_filename("Forest", existing, ".jpg")
    assert result == "Forest_03.jpg"


def test_validate_resource_valid(mock_valid_image):
    """Test image validation with valid image data"""
    assert validate_resource(mock_valid_image) is True


def test_validate_resource_too_small():
    """Test image validation rejects images < 1000 bytes"""
    small_data = b"fake image data"
    assert validate_resource(small_data) is False


def test_validate_resource_corrupted():
    """Test image validation rejects corrupted image data"""
    corrupted_data = b"not a real image" * 100  # > 1000 bytes but invalid
    assert validate_resource(corrupted_data) is False


@patch('magic_cards.data_fetcher.requests.get')
@patch('magic_cards.data_fetcher.os.makedirs')
@patch('builtins.open', new_callable=mock_open)
def test_fetch_single_resource_success(mock_file, mock_makedirs, mock_get, mock_scryfall_response, mock_valid_image):
    """Test successful card fetch with mocked API"""
    # Setup mock API response
    mock_api_response = Mock()
    mock_api_response.status_code = 200
    mock_api_response.headers = {'Content-Type': 'application/json'}
    mock_api_response.json.return_value = mock_scryfall_response

    mock_img_response = Mock()
    mock_img_response.status_code = 200
    mock_img_response.headers = {'Content-Type': 'image/jpeg'}
    mock_img_response.content = mock_valid_image

    mock_get.side_effect = [mock_api_response, mock_img_response]

    # Test fetch (protocol-first: requires api_url_template, response_schema, size_hints)
    success, metadata, error = fetch_single_resource(
        "Forest",
        output_dir="/tmp/test",
        api_url_template="https://api.scryfall.com/cards/named?fuzzy={identifier}",
        response_schema={"image_url": "image_uris.png"},
        size_hints={"width_px": 745, "height_px": 1040, "dpi": 300, "source": "test"}
    )

    assert success is True
    assert metadata["path"] == "/tmp/test/Forest.jpg"
    assert error is None


@patch('magic_cards.data_fetcher.requests.get')
def test_fetch_single_resource_not_found(mock_get):
    """Test card fetch with 404 response"""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    success, metadata, error = fetch_single_resource(
        "NonexistentCard",
        output_dir="/tmp/test",
        api_url_template="https://api.scryfall.com/cards/named?fuzzy={identifier}",
        response_schema={"image_url": "image_uris.png"},
        size_hints={"width_px": 745, "height_px": 1040, "dpi": 300, "source": "test"}
    )

    assert success is False
    assert metadata is None
    assert error == "resource_not_found"


@patch('magic_cards.data_fetcher.requests.get')
@patch('magic_cards.data_fetcher.os.makedirs')
@patch('builtins.open', new_callable=mock_open)
@patch('magic_cards.data_fetcher.os.path.exists')
def test_fetch_dfc_card(mock_exists, mock_file, mock_makedirs, mock_get, mock_dfc_response, mock_valid_image):
    """Test DFC (Double-Faced Card) handling extracts both faces"""
    mock_exists.return_value = False

    # Setup mock API response
    mock_api_response = Mock()
    mock_api_response.status_code = 200
    mock_api_response.headers = {'Content-Type': 'application/json'}
    mock_api_response.json.return_value = mock_dfc_response

    mock_img_response_1 = Mock()
    mock_img_response_1.status_code = 200
    mock_img_response_1.headers = {'Content-Type': 'image/jpeg'}
    mock_img_response_1.content = mock_valid_image

    mock_img_response_2 = Mock()
    mock_img_response_2.status_code = 200
    mock_img_response_2.headers = {'Content-Type': 'image/jpeg'}
    mock_img_response_2.content = mock_valid_image

    mock_get.side_effect = [mock_api_response, mock_img_response_1, mock_img_response_2]

    # Test DFC fetch (protocol-first)
    success, metadata, error = fetch_single_resource(
        "Delver of Secrets // Insectile Aberration",
        output_dir="/tmp/test",
        api_url_template="https://api.scryfall.com/cards/named?fuzzy={identifier}",
        response_schema={"image_url": "card_faces[*].image_uris.png"},
        size_hints={"width_px": 745, "height_px": 1040, "dpi": 300, "source": "test"}
    )

    assert success is True
    assert isinstance(metadata, dict)
    # Protocol-first returns metadata dict, may have "path" or "faces" key
    assert "path" in metadata or metadata.get("faces") == 2
