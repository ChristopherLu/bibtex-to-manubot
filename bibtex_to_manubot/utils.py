"""
Utility functions for BibTeX to Manubot conversion.
"""

import re
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse


def clean_bibtex_field(field: str) -> str:
    """Clean BibTeX field by removing braces and LaTeX commands.
    
    Args:
        field: Raw BibTeX field value
        
    Returns:
        Cleaned field value
    """
    if not field:
        return ""
    
    # Remove outer braces
    field = field.strip()
    if field.startswith('{') and field.endswith('}'):
        field = field[1:-1]
    
    # Remove double braces
    field = re.sub(r'\{\{([^}]+)\}\}', r'\1', field)
    field = re.sub(r'\{([^}]+)\}', r'\1', field)
    
    # Convert common LaTeX commands
    latex_replacements = {
        r'\\textit\{([^}]+)\}': r'*\1*',
        r'\\textbf\{([^}]+)\}': r'**\1**',
        r'\\emph\{([^}]+)\}': r'*\1*',
        r'\\"a': 'ä', r'\\"o': 'ö', r'\\"u': 'ü',
        r'\\\'a': 'á', r'\\\'e': 'é', r'\\\'i': 'í', r'\\\'o': 'ó', r'\\\'u': 'ú',
        r'\\`a': 'à', r'\\`e': 'è', r'\\`i': 'ì', r'\\`o': 'ò', r'\\`u': 'ù',
        r'\\^a': 'â', r'\\^e': 'ê', r'\\^i': 'î', r'\\^o': 'ô', r'\\^u': 'û',
        r'\\~n': 'ñ', r'\\~a': 'ã', r'\\~o': 'õ',
        r'\\c\{c\}': 'ç',
        r'\\&': '&',
        r'\\%': '%',
        r'\\\$': '$',
        r'\\#': '#',
        r'\\_': '_',
        r'\\\\': '\n',
        r'\\': ''
    }
    
    for pattern, replacement in latex_replacements.items():
        field = re.sub(pattern, replacement, field)
    
    # Remove extra whitespace
    field = ' '.join(field.split())
    
    return field.strip()


def extract_doi(text: str) -> Optional[str]:
    """Extract and validate DOI from text.
    
    Args:
        text: Text that might contain a DOI
        
    Returns:
        Clean DOI or None
    """
    if not text:
        return None
    
    # DOI regex patterns
    doi_patterns = [
        r'(?:doi:)\s*(10\.\d+/[^\s,}]+)',
        r'(?:https?://(?:dx\.)?doi\.org/)(10\.\d+/[^\s,}]+)',
        r'^(10\.\d+/[^\s,}]+)$',  # Just the DOI itself
        r'(10\.\d+/[^\s,}]+)',    # DOI anywhere in text
    ]
    
    for pattern in doi_patterns:
        match = re.search(pattern, text.strip(), re.IGNORECASE)
        if match:
            doi = match.group(1)
            # Clean and validate
            doi = re.sub(r'[,;.\s]+$', '', doi)  # Remove trailing punctuation
            if validate_doi(doi):
                return doi
    
    return None


def validate_doi(doi: str) -> bool:
    """Validate DOI format.
    
    Args:
        doi: DOI string to validate
        
    Returns:
        True if valid DOI format
    """
    if not doi:
        return False
    
    # DOI must start with "10." and have at least one "/"
    pattern = r'^10\.\d{4,}/[^\s]+$'
    return bool(re.match(pattern, doi.strip()))


def extract_pmid(text: str) -> Optional[str]:
    """Extract PMID from text.
    
    Args:
        text: Text that might contain a PMID
        
    Returns:
        Clean PMID or None
    """
    if not text:
        return None
    
    patterns = [
        r'(?:pmid:?)\s*(\d+)',
        r'(?:pubmed\s*id:?)\s*(\d+)',
        r'(?:pubmed:?)\s*(\d+)',
        r'^(\d{7,8})$',  # Just the PMID number (7-8 digits)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.strip(), re.IGNORECASE)
        if match:
            pmid = match.group(1)
            # Validate PMID (should be 7-8 digits)
            if pmid.isdigit() and 7 <= len(pmid) <= 8:
                return pmid
    
    return None


def extract_pmcid(text: str) -> Optional[str]:
    """Extract PMC ID from text.
    
    Args:
        text: Text that might contain a PMC ID
        
    Returns:
        Clean PMC ID or None
    """
    if not text:
        return None
    
    patterns = [
        r'(?:pmc:?)\s*(PMC\d+)',
        r'(?:pmcid:?)\s*(PMC\d+)',
        r'^(PMC\d+)$',  # Just the PMC ID
        r'(PMC\d+)',    # PMC ID anywhere
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.strip(), re.IGNORECASE)
        if match:
            pmcid = match.group(1).upper()
            # Ensure it starts with PMC
            if pmcid.startswith('PMC') and pmcid[3:].isdigit():
                return pmcid
    
    return None


def extract_arxiv_id(text: str) -> Optional[str]:
    """Extract arXiv ID from text.
    
    Args:
        text: Text that might contain an arXiv ID
        
    Returns:
        Clean arXiv ID or None
    """
    if not text:
        return None
    
    patterns = [
        r'(?:arxiv:)\s*([\d.]+v?\d*)',
        r'(?:arXiv:)\s*([\d.]+v?\d*)',
        r'(?:https?://arxiv\.org/abs/)([\d.]+v?\d*)',
        r'^([\d.]+v?\d*)$',  # Just the arXiv ID
        r'(\d{4}\.\d{4,5}(?:v\d+)?)',  # New format: YYMM.NNNNN[vN]
        r'([a-z-]+(?:\.[A-Z]{2})?/\d{7})',  # Old format: subject-class/YYMMnnn
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.strip(), re.IGNORECASE)
        if match:
            arxiv_id = match.group(1)
            # Basic validation for arXiv ID format
            if (re.match(r'^\d{4}\.\d{4,5}(?:v\d+)?$', arxiv_id) or  # New format
                re.match(r'^[a-z-]+(?:\.[A-Z]{2})?/\d{7}$', arxiv_id)):  # Old format
                return arxiv_id
    
    return None


def extract_isbn(text: str) -> Optional[str]:
    """Extract ISBN from text.
    
    Args:
        text: Text that might contain an ISBN
        
    Returns:
        Clean ISBN or None
    """
    if not text:
        return None
    
    # Remove all non-digit characters except 'X'
    clean_text = re.sub(r'[^\dX]', '', text.upper())
    
    # Check for ISBN-13 (13 digits)
    if len(clean_text) == 13 and clean_text.isdigit():
        return clean_text
    
    # Check for ISBN-10 (9 digits + check digit which can be X)
    if len(clean_text) == 10:
        if clean_text[:9].isdigit() and (clean_text[9].isdigit() or clean_text[9] == 'X'):
            return clean_text
    
    # Try to extract from longer strings
    isbn_patterns = [
        r'(?:isbn:?\s*)(978\d{10})',  # ISBN-13
        r'(?:isbn:?\s*)(\d{9}[\dX])',  # ISBN-10
        r'(978\d{10})',  # ISBN-13 anywhere
        r'(\d{9}[\dX])',  # ISBN-10 anywhere
    ]
    
    for pattern in isbn_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def validate_url(url: str) -> bool:
    """Validate URL format.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL
    """
    if not url:
        return False
    
    try:
        result = urlparse(url.strip())
        return all([result.scheme in ('http', 'https'), result.netloc])
    except:
        return False


def normalize_author_names(authors: List[str]) -> List[str]:
    """Normalize author names from BibTeX format.
    
    Args:
        authors: List of raw author names
        
    Returns:
        List of normalized author names
    """
    normalized = []
    
    for author in authors:
        author = author.strip()
        if not author:
            continue
        
        # Handle "Last, First Middle" format
        if ',' in author:
            parts = author.split(',', 1)
            if len(parts) == 2:
                last = parts[0].strip()
                first = parts[1].strip()
                if first and last:
                    author = f"{first} {last}"
        
        # Remove common suffixes and titles
        suffixes = ['Jr.', 'Sr.', 'III', 'II', 'IV', 'V', 'Ph.D.', 'Dr.', 'Prof.']
        for suffix in suffixes:
            author = re.sub(f'\\s+{re.escape(suffix)}\\s*$', '', author, flags=re.IGNORECASE)
        
        # Clean extra whitespace
        author = ' '.join(author.split())
        
        if author:
            normalized.append(author)
    
    return normalized


def format_pages(pages_str: str) -> Optional[str]:
    """Format page range string.
    
    Args:
        pages_str: Raw pages string from BibTeX
        
    Returns:
        Formatted page range or None
    """
    if not pages_str:
        return None
    
    # Clean the string
    pages = pages_str.strip()
    
    # Convert double hyphens to single hyphen
    pages = re.sub(r'--+', '-', pages)
    
    # Remove extra spaces around hyphens
    pages = re.sub(r'\s*-\s*', '-', pages)
    
    return pages if pages else None


def extract_bibtex_urls(text: str) -> List[str]:
    """Extract URLs from BibTeX field text.
    
    Args:
        text: Text that might contain URLs
        
    Returns:
        List of valid URLs
    """
    if not text:
        return []
    
    # URL pattern
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\],;]+'
    urls = re.findall(url_pattern, text, re.IGNORECASE)
    
    # Validate and clean URLs
    valid_urls = []
    for url in urls:
        # Remove trailing punctuation
        url = re.sub(r'[.,;)}\]]+$', '', url)
        if validate_url(url):
            valid_urls.append(url)
    
    return valid_urls


def create_manubot_id(citation_type: str, identifier: str) -> str:
    """Create a properly formatted Manubot citation ID.
    
    Args:
        citation_type: Type of citation (doi, pmid, etc.)
        identifier: The identifier value
        
    Returns:
        Formatted Manubot citation ID
    """
    return f"{citation_type.lower()}:{identifier}"


def validate_manubot_id(manubot_id: str) -> bool:
    """Validate Manubot citation ID format.
    
    Args:
        manubot_id: Manubot citation ID to validate
        
    Returns:
        True if valid format
    """
    if not manubot_id or ':' not in manubot_id:
        return False
    
    parts = manubot_id.split(':', 1)
    if len(parts) != 2:
        return False
    
    citation_type, identifier = parts
    
    # Validate based on citation type
    if citation_type == 'doi':
        return validate_doi(identifier)
    elif citation_type == 'pmid':
        return identifier.isdigit() and 7 <= len(identifier) <= 8
    elif citation_type == 'pmcid':
        return identifier.startswith('PMC') and identifier[3:].isdigit()
    elif citation_type == 'arxiv':
        return bool(re.match(r'^\d{4}\.\d{4,5}(?:v\d+)?$|^[a-z-]+(?:\.[A-Z]{2})?/\d{7}$', identifier))
    elif citation_type == 'isbn':
        clean_id = re.sub(r'[^\dX]', '', identifier.upper())
        return len(clean_id) in (10, 13)
    elif citation_type == 'url':
        return validate_url(identifier)
    elif citation_type == 'raw':
        return bool(identifier.strip())
    
    return False


def generate_publication_date(year: Optional[int], month: Optional[str] = None, day: Optional[str] = None) -> Optional[str]:
    """Generate a publication date in YYYY-MM-DD format.
    
    Args:
        year: Publication year
        month: Publication month (optional)
        day: Publication day (optional)
        
    Returns:
        Date string in YYYY-MM-DD format or None
    """
    if not year:
        return None
    
    # Default to mid-year if no specific date
    default_month = "06"
    default_day = "15"
    
    # Parse month if provided
    if month:
        month = month.strip().lower()
        month_mapping = {
            'january': '01', 'jan': '01',
            'february': '02', 'feb': '02',
            'march': '03', 'mar': '03',
            'april': '04', 'apr': '04',
            'may': '05',
            'june': '06', 'jun': '06',
            'july': '07', 'jul': '07',
            'august': '08', 'aug': '08',
            'september': '09', 'sep': '09', 'sept': '09',
            'october': '10', 'oct': '10',
            'november': '11', 'nov': '11',
            'december': '12', 'dec': '12'
        }
        
        if month in month_mapping:
            month_num = month_mapping[month]
        elif month.isdigit() and 1 <= int(month) <= 12:
            month_num = f"{int(month):02d}"
        else:
            month_num = default_month
    else:
        month_num = default_month
    
    # Parse day if provided
    if day:
        day = day.strip()
        if day.isdigit() and 1 <= int(day) <= 31:
            day_num = f"{int(day):02d}"
        else:
            day_num = default_day
    else:
        day_num = default_day
    
    # Validate the date doesn't exceed month limits
    try:
        from datetime import datetime
        datetime(year, int(month_num), int(day_num))
        return f"{year}-{month_num}-{day_num}"
    except ValueError:
        # If invalid date (e.g., Feb 31), use last day of month
        if month_num in ['02']:
            day_num = '28'  # Safe for February
        elif month_num in ['04', '06', '09', '11']:
            day_num = '30'  # 30-day months
        else:
            day_num = '31'  # 31-day months
        
        return f"{year}-{month_num}-{day_num}"


def parse_bibtex_date_fields(fields: Dict[str, str]) -> Dict[str, Optional[str]]:
    """Parse date-related fields from BibTeX entry.
    
    Args:
        fields: BibTeX fields dictionary
        
    Returns:
        Dictionary with parsed year, month, day
    """
    result = {'year': None, 'month': None, 'day': None}
    
    # Parse year
    if 'year' in fields:
        year_str = fields['year'].strip()
        if year_str.isdigit():
            result['year'] = int(year_str)
    
    # Parse month
    if 'month' in fields:
        result['month'] = fields['month'].strip()
    
    # Parse day
    if 'day' in fields:
        result['day'] = fields['day'].strip()
    
    return result