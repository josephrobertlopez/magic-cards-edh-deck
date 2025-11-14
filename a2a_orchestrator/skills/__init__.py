"""Skill class wrappers for A2A orchestration."""

from .data_fetcher_skill import DataFetcherSkill
from .document_generator_skill import DocumentGeneratorSkill
from .format_transformer_skill import FormatTransformerSkill
from .web_fetcher_skill import WebFetcherSkill
from .html_extractor_skill import HTMLExtractorSkill

__all__ = [
    'DataFetcherSkill',
    'DocumentGeneratorSkill',
    'FormatTransformerSkill',
    'WebFetcherSkill',
    'HTMLExtractorSkill'
]
