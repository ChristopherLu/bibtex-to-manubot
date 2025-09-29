"""
Data models for BibTeX to Manubot conversion.
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
import re


class CitationType(str, Enum):
    """Supported citation types that Manubot can handle."""
    DOI = "doi"
    PMID = "pmid"
    PMCID = "pmcid"
    ARXIV = "arxiv"
    ISBN = "isbn"
    URL = "url"
    WIKIDATA = "wikidata"
    RAW = "raw"


class BibTeXEntryType(str, Enum):
    """Common BibTeX entry types."""
    ARTICLE = "article"
    BOOK = "book"
    BOOKLET = "booklet"
    INBOOK = "inbook"
    INCOLLECTION = "incollection"
    INPROCEEDINGS = "inproceedings"
    MANUAL = "manual"
    MASTERSTHESIS = "mastersthesis"
    MISC = "misc"
    PHDTHESIS = "phdthesis"
    PROCEEDINGS = "proceedings"
    TECHREPORT = "techreport"
    UNPUBLISHED = "unpublished"


class BibTeXEntry(BaseModel):
    """Parsed BibTeX entry."""
    key: str  # BibTeX citation key
    entry_type: str  # Entry type (article, book, etc.)
    fields: Dict[str, str]  # All BibTeX fields
    
    # Common extracted fields
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    journal: Optional[str] = None
    booktitle: Optional[str] = None
    year: Optional[int] = None
    volume: Optional[str] = None
    number: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    arxiv: Optional[str] = None
    isbn: Optional[str] = None
    url: Optional[str] = None
    month: Optional[str] = None
    day: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self._extract_common_fields()
    
    def _extract_common_fields(self):
        """Extract common fields from the fields dictionary."""
        fields = {k.lower(): v for k, v in self.fields.items()}
        
        self.title = fields.get('title')
        self.journal = fields.get('journal')
        self.booktitle = fields.get('booktitle')
        self.volume = fields.get('volume')
        self.number = fields.get('number')
        self.pages = fields.get('pages')
        self.publisher = fields.get('publisher')
        self.doi = fields.get('doi')
        self.pmid = fields.get('pmid')
        self.pmcid = fields.get('pmcid')
        self.arxiv = fields.get('arxiv') or fields.get('eprint')
        self.isbn = fields.get('isbn')
        self.url = fields.get('url')
        
        # Parse year
        if 'year' in fields:
            try:
                self.year = int(fields['year'])
            except (ValueError, TypeError):
                pass
        
        # Parse authors
        if 'author' in fields:
            self.authors = self._parse_authors(fields['author'])
        
        # Store month and day for date generation
        self.month = fields.get('month')
        self.day = fields.get('day')
    
    def _parse_authors(self, author_string: str) -> List[str]:
        """Parse BibTeX author string into list of names."""
        # Split by 'and' but handle cases like "Smith and Jones"
        authors = re.split(r'\s+and\s+', author_string)
        
        # Clean up author names
        cleaned_authors = []
        for author in authors:
            author = author.strip()
            if author:
                # Handle "Last, First" format
                if ',' in author:
                    parts = author.split(',', 1)
                    if len(parts) == 2:
                        last, first = parts
                        author = f"{first.strip()} {last.strip()}"
                cleaned_authors.append(author)
        
        return cleaned_authors


class ManubotCitation(BaseModel):
    """Manubot citation format."""
    id: str  # Manubot citation ID (e.g., "doi:10.1234/example")
    citation_type: CitationType
    identifier: str  # The actual identifier value
    
    # Additional metadata for YAML output
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    date: Optional[str] = None  # Full date in YYYY-MM-DD format
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    link: Optional[str] = None
    
    # Original BibTeX information
    original_key: Optional[str] = None
    bibtex_type: Optional[str] = None
    
    @validator('id')
    def validate_manubot_id(cls, v):
        """Validate Manubot citation ID format."""
        if ':' not in v:
            raise ValueError("Manubot ID must contain a colon separator")
        return v
    
    def to_dict(self, include_metadata: bool = True) -> Dict[str, Any]:
        """Convert to dictionary for YAML output."""
        result = {
            'id': self.id,
            'type': self.citation_type.value
        }
        
        if include_metadata:
            if self.title:
                result['title'] = self.title
            if self.authors:
                result['authors'] = self.authors
            if self.journal:
                result['publisher'] = self.journal  # Rename journal to publisher for website compatibility
            if self.year:
                result['year'] = self.year
            if self.date:
                result['date'] = self.date
            if self.link:
                result['link'] = self.link  # Use link instead of url for website compatibility
        
        return result


class ConversionResult(BaseModel):
    """Result of BibTeX to Manubot conversion."""
    original_key: str
    success: bool = False
    manubot_citation: Optional[ManubotCitation] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    @property
    def citation_id(self) -> Optional[str]:
        """Get the Manubot citation ID."""
        return self.manubot_citation.id if self.manubot_citation else None


class BatchConversionResult(BaseModel):
    """Result of batch BibTeX conversion."""
    input_files: List[str]
    total_entries: int
    successful_conversions: int
    failed_conversions: int
    conversions: List[ConversionResult]
    processing_time: float
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_entries == 0:
            return 0.0
        return (self.successful_conversions / self.total_entries) * 100
    
    def get_successful_citations(self) -> List[ManubotCitation]:
        """Get all successful Manubot citations."""
        return [
            result.manubot_citation 
            for result in self.conversions 
            if result.success and result.manubot_citation
        ]