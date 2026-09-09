"""Extraction agent package for fast structured financial news parsing."""

from .schemas import ExtractedNews
from .extractor import ExtractionAgent, get_extraction_agent

__all__ = ["ExtractedNews", "ExtractionAgent", "get_extraction_agent"]
