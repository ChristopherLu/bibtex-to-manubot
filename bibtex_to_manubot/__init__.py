"""
BibTeX to Manubot Converter Package

A Python package for converting BibTeX files to Manubot-formatted YAML citations.
"""

from .converter import BibTeXConverter
from .models import BibTeXEntry, ManubotCitation, ConversionResult
from .config import Config

__version__ = "0.1.0"
__all__ = ["BibTeXConverter", "BibTeXEntry", "ManubotCitation", "ConversionResult", "Config"]