"""
Magic Cards - Modular card proxy generation library.

Provides three main functions:
- fetch_resources_from_list(): Download card images from APIs
- generate_document(): Create PPTX presentations from card images
- transform_to_pdf(): Convert PPTX to PDF using LibreOffice
"""

from .data_fetcher import fetch_resources_from_list
from .document_generator import generate_document
from .format_transformer import transform_to_pdf

__all__ = [
    'fetch_resources_from_list',
    'generate_document',
    'transform_to_pdf'
]
