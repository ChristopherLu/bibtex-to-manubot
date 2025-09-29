"""
Unit tests for BibTeX to Manubot converter.
"""

import unittest
from unittest.mock import patch, mock_open
from pathlib import Path
import tempfile
import yaml

from bibtex_to_manubot import BibTeXConverter
from bibtex_to_manubot.models import BibTeXEntry, ManubotCitation


class TestBibTeXConverter(unittest.TestCase):
    """Test BibTeX to Manubot converter functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.converter = BibTeXConverter()
    
    def test_convert_entry_with_doi(self):
        """Test converting entry with DOI."""
        entry = BibTeXEntry(
            key="test2023",
            entry_type="article",
            fields={
                "title": "Test Paper",
                "author": "John Doe and Jane Smith",
                "journal": "Nature",
                "year": "2023",
                "doi": "10.1234/example"
            }
        )
        
        result = self.converter.convert_entry(entry)
        
        self.assertTrue(result.success)
        self.assertEqual(result.manubot_citation.id, "doi:10.1234/example")
        self.assertEqual(result.manubot_citation.citation_type, "doi")
        self.assertEqual(result.manubot_citation.title, "Test Paper")
        self.assertEqual(result.manubot_citation.authors, ["John Doe", "Jane Smith"])
        self.assertEqual(result.manubot_citation.year, 2023)
    
    def test_convert_entry_with_pmid(self):
        """Test converting entry with PMID."""
        entry = BibTeXEntry(
            key="test2023",
            entry_type="article",
            fields={
                "title": "Medical Paper",
                "author": "Dr. Smith",
                "year": "2023",
                "pmid": "12345678"
            }
        )
        
        result = self.converter.convert_entry(entry)
        
        self.assertTrue(result.success)
        self.assertEqual(result.manubot_citation.id, "pmid:12345678")
        self.assertEqual(result.manubot_citation.citation_type, "pmid")
    
    def test_convert_entry_with_arxiv(self):
        """Test converting entry with arXiv ID."""
        entry = BibTeXEntry(
            key="test2023",
            entry_type="article",
            fields={
                "title": "arXiv Paper",
                "author": "Researcher A",
                "year": "2023",
                "eprint": "2301.12345",
                "archivePrefix": "arXiv"
            }
        )
        
        result = self.converter.convert_entry(entry)
        
        self.assertTrue(result.success)
        self.assertEqual(result.manubot_citation.id, "arxiv:2301.12345")
        self.assertEqual(result.manubot_citation.citation_type, "arxiv")
    
    def test_convert_entry_fallback_to_raw(self):
        """Test fallback to raw citation when no identifiers available."""
        entry = BibTeXEntry(
            key="test2023",
            entry_type="article",
            fields={
                "title": "Paper Without Identifiers",
                "author": "Unknown Author",
                "year": "2023",
                "journal": "Unknown Journal"
            }
        )
        
        result = self.converter.convert_entry(entry)
        
        self.assertTrue(result.success)
        self.assertEqual(result.manubot_citation.id, "raw:test2023")
        self.assertEqual(result.manubot_citation.citation_type, "raw")
    
    def test_validate_manubot_format(self):
        """Test YAML format validation."""
        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump([
                {
                    'id': 'doi:10.1234/example',
                    'type': 'doi',
                    'title': 'Test Paper',
                    'authors': ['John Doe'],
                    'year': 2023
                }
            ], f)
            temp_path = Path(f.name)
        
        try:
            result = self.converter.validate_manubot_format(temp_path)
            
            self.assertTrue(result['valid'])
            self.assertEqual(result['citation_count'], 1)
            self.assertIn('doi', result['citation_types'])
            self.assertEqual(result['citation_types']['doi'], 1)
        
        finally:
            temp_path.unlink()
    
    def test_basic_functionality(self):
        """Test basic converter functionality."""
        # Just test that the converter can be instantiated
        self.assertIsNotNone(self.converter)
        self.assertTrue(hasattr(self.converter, 'convert_entry'))
        self.assertTrue(hasattr(self.converter, 'parse_bibtex_file'))


class TestManubotCitation(unittest.TestCase):
    """Test Manubot citation model."""
    
    def test_citation_creation(self):
        """Test creating Manubot citation."""
        citation = ManubotCitation(
            id="doi:10.1234/example",
            citation_type="doi",
            identifier="10.1234/example",
            title="Test Paper",
            authors=["John Doe"],
            year=2023,
            publisher="Nature"
        )
        
        self.assertEqual(citation.id, "doi:10.1234/example")
        self.assertEqual(citation.citation_type, "doi")
        self.assertEqual(citation.title, "Test Paper")
        self.assertEqual(citation.authors, ["John Doe"])
        self.assertEqual(citation.year, 2023)
        self.assertEqual(citation.publisher, "Nature")


if __name__ == '__main__':
    unittest.main()