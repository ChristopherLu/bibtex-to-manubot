"""
BibTeX to Manubot converter.
"""

import re
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

from .models import (
    BibTeXEntry, ManubotCitation, ConversionResult, 
    BatchConversionResult, CitationType
)
from .config import Config
from .utils import (
    extract_doi, extract_pmid, extract_pmcid, 
    extract_arxiv_id, extract_isbn, validate_url,
    clean_bibtex_field, generate_publication_date
)


class BibTeXConverter:
    """Main class for converting BibTeX entries to Manubot format."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the converter.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = Config(config_path)
        self.citation_priority = self.config.get('citation_priority', [
            'doi', 'pmid', 'pmcid', 'arxiv', 'isbn', 'url'
        ])
        
        # Initialize BibTeX parser
        self.parser = BibTexParser()
        self.parser.customization = convert_to_unicode
        self.parser.ignore_nonstandard_types = False
    
    def parse_bibtex_file(self, file_path: Union[str, Path]) -> List[BibTeXEntry]:
        """Parse a BibTeX file and return entries.
        
        Args:
            file_path: Path to BibTeX file
            
        Returns:
            List of parsed BibTeX entries
        """
        file_path = Path(file_path)
        encoding = self.config.get('bibtex.encoding', 'utf-8')
        
        try:
            with open(file_path, 'r', encoding=encoding) as bibtex_file:
                content = bibtex_file.read()
                
            # Parse BibTeX content
            bib_database = bibtexparser.loads(content, parser=self.parser)
            
            # Convert to our BibTeXEntry models
            entries = []
            for entry in bib_database.entries:
                bibtex_entry = BibTeXEntry(
                    key=entry.get('ID', ''),
                    entry_type=entry.get('ENTRYTYPE', 'misc').lower(),
                    fields=entry
                )
                entries.append(bibtex_entry)
            
            return entries
            
        except Exception as e:
            raise ValueError(f"Error parsing BibTeX file {file_path}: {str(e)}")
    
    def convert_entry(self, entry: BibTeXEntry) -> ConversionResult:
        """Convert a single BibTeX entry to Manubot format.
        
        Args:
            entry: BibTeX entry to convert
            
        Returns:
            Conversion result with Manubot citation or error
        """
        result = ConversionResult(original_key=entry.key)
        
        try:
            # Try to extract identifiers in priority order
            citation_type, identifier = self._extract_best_identifier(entry)
            
            if not identifier:
                result.errors.append("No valid identifier found")
                return result
            
            # Create Manubot citation
            manubot_id = f"{citation_type.value}:{identifier}"
            
            # Generate publication date
            publication_date = generate_publication_date(
                entry.year, 
                getattr(entry, 'month', None), 
                getattr(entry, 'day', None)
            )
            
            # Use journal field, or fall back to booktitle for conference papers
            journal_or_conference = None
            if entry.journal:
                journal_or_conference = clean_bibtex_field(entry.journal)
            elif entry.booktitle:
                journal_or_conference = clean_bibtex_field(entry.booktitle)
                
            manubot_citation = ManubotCitation(
                id=manubot_id,
                citation_type=citation_type,
                identifier=identifier,
                title=clean_bibtex_field(entry.title) if entry.title else None,
                authors=entry.authors,
                journal=journal_or_conference,
                year=entry.year,
                date=publication_date,
                volume=entry.volume,
                issue=entry.number,  # BibTeX "number" maps to "issue"
                pages=entry.pages,
                publisher=clean_bibtex_field(entry.publisher) if entry.publisher else None,
                link=entry.url,
                original_key=entry.key,
                bibtex_type=entry.entry_type
            )
            
            result.success = True
            result.manubot_citation = manubot_citation
            
            # Add warnings for missing important fields
            if not entry.title:
                result.warnings.append("No title found")
            if not entry.authors:
                result.warnings.append("No authors found")
            if not entry.year:
                result.warnings.append("No publication year found")
        
        except Exception as e:
            result.errors.append(f"Conversion error: {str(e)}")
        
        return result
    
    def _is_arxiv_paper(self, entry: BibTeXEntry) -> bool:
        """Check if this is an arXiv paper that should be skipped.
        
        Args:
            entry: BibTeX entry to check
            
        Returns:
            True if this is an arXiv paper, False otherwise
        """
        # Check if journal contains "arXiv"
        if entry.journal and 'arxiv' in entry.journal.lower():
            return True
            
        # Check if eprint field contains arXiv identifier
        if hasattr(entry, 'eprint') and entry.eprint:
            return True
            
        # Check if url contains arxiv.org
        if entry.url and 'arxiv.org' in entry.url.lower():
            return True
            
        # Check if DOI is an arXiv DOI
        if entry.doi and 'arxiv' in entry.doi.lower():
            return True
            
        return False
    
    def _extract_best_identifier(self, entry: BibTeXEntry) -> tuple[Optional[CitationType], Optional[str]]:
        """Extract the best available identifier from a BibTeX entry.
        
        Args:
            entry: BibTeX entry
            
        Returns:
            Tuple of (citation_type, identifier) or (None, None)
        """
        # Check each identifier type in priority order
        for identifier_type in self.citation_priority:
            if identifier_type == 'doi' and entry.doi:
                clean_doi = extract_doi(entry.doi)
                if clean_doi:
                    return CitationType.DOI, clean_doi
            
            elif identifier_type == 'pmid' and entry.pmid:
                clean_pmid = extract_pmid(entry.pmid)
                if clean_pmid:
                    return CitationType.PMID, clean_pmid
            
            elif identifier_type == 'pmcid' and entry.pmcid:
                clean_pmcid = extract_pmcid(entry.pmcid)
                if clean_pmcid:
                    return CitationType.PMCID, clean_pmcid
            
            elif identifier_type == 'arxiv' and entry.arxiv:
                clean_arxiv = extract_arxiv_id(entry.arxiv)
                if clean_arxiv:
                    return CitationType.ARXIV, clean_arxiv
            
            elif identifier_type == 'isbn' and entry.isbn:
                clean_isbn = extract_isbn(entry.isbn)
                if clean_isbn:
                    return CitationType.ISBN, clean_isbn
            
            elif identifier_type == 'url' and entry.url:
                if validate_url(entry.url):
                    return CitationType.URL, entry.url
        
        # Fallback: use BibTeX key as raw citation
        if entry.key:
            return CitationType.RAW, entry.key
        
        return None, None
    
    def convert_file(self, input_path: Union[str, Path], 
                    output_path: Optional[Union[str, Path]] = None) -> BatchConversionResult:
        """Convert a BibTeX file to Manubot YAML format.
        
        Args:
            input_path: Path to input BibTeX file
            output_path: Path for output YAML file (optional)
            
        Returns:
            Batch conversion result
        """
        return self.batch_convert([input_path], output_path)
    
    def batch_convert(self, input_paths: List[Union[str, Path]], 
                     output_path: Optional[Union[str, Path]] = None) -> BatchConversionResult:
        """Convert multiple BibTeX files to a single Manubot YAML file.
        
        Args:
            input_paths: List of input BibTeX files
            output_path: Path for output YAML file (optional)
            
        Returns:
            Batch conversion result
        """
        start_time = time.time()
        
        # Parse all input files
        all_entries = []
        file_paths = [str(p) for p in input_paths]
        
        for file_path in input_paths:
            try:
                entries = self.parse_bibtex_file(file_path)
                all_entries.extend(entries)
            except Exception as e:
                # Create failed results for unparseable files
                failed_result = ConversionResult(
                    original_key=f"FILE:{file_path}",
                    success=False,
                    errors=[f"Failed to parse file: {str(e)}"]
                )
                all_entries.append(failed_result)
        
        # Convert entries
        conversion_results = []
        for entry in all_entries:
            if isinstance(entry, BibTeXEntry):
                result = self.convert_entry(entry)
                conversion_results.append(result)
            else:
                # Already a failed ConversionResult
                conversion_results.append(entry)
        
        # Calculate statistics
        successful = sum(1 for r in conversion_results if r.success)
        failed = len(conversion_results) - successful
        
        # Create batch result
        batch_result = BatchConversionResult(
            input_files=file_paths,
            total_entries=len(conversion_results),
            successful_conversions=successful,
            failed_conversions=failed,
            conversions=conversion_results,
            processing_time=time.time() - start_time
        )
        
        # Save to YAML file if output path provided
        if output_path:
            self.save_yaml(batch_result, output_path)
        
        return batch_result
    
    def _find_title_overlap(self, title1: str, title2: str, min_words: int = 6) -> int:
        """Find the longest consecutive word overlap between two titles.
        
        Args:
            title1: First title
            title2: Second title
            min_words: Minimum words for overlap to be considered significant
            
        Returns:
            Number of consecutive matching words
        """
        if not title1 or not title2:
            return 0
            
        # Normalize titles: lowercase, remove punctuation, split into words
        import re
        words1 = re.findall(r'\b\w+\b', title1.lower())
        words2 = re.findall(r'\b\w+\b', title2.lower())
        
        max_overlap = 0
        
        # Find longest consecutive overlap
        for i in range(len(words1)):
            for j in range(len(words2)):
                overlap = 0
                while (i + overlap < len(words1) and 
                       j + overlap < len(words2) and 
                       words1[i + overlap] == words2[j + overlap]):
                    overlap += 1
                max_overlap = max(max_overlap, overlap)
                
        return max_overlap
    
    def _remove_arxiv_duplicates(self, citations: List[Dict], min_overlap: int = 6) -> List[Dict]:
        """Remove arXiv papers that have published versions with similar titles.
        
        Args:
            citations: List of citation dictionaries
            min_overlap: Minimum consecutive word overlap to consider as duplicate
            
        Returns:
            Filtered list with arXiv duplicates removed
        """
        # Separate arXiv and non-arXiv papers based on publisher field (renamed from journal)
        # ArXiv papers have publisher = "CoRR" (Computing Research Repository)
        arxiv_papers = [c for c in citations if c.get('publisher') == 'CoRR']
        non_arxiv_papers = [c for c in citations if c.get('publisher') != 'CoRR']
        
        # Find arXiv papers to remove
        arxiv_to_remove = set()
        
        for arxiv_paper in arxiv_papers:
            arxiv_title = arxiv_paper.get('title', '')
            if not arxiv_title:
                continue
                
            for non_arxiv_paper in non_arxiv_papers:
                non_arxiv_title = non_arxiv_paper.get('title', '')
                if not non_arxiv_title:
                    continue
                    
                overlap = self._find_title_overlap(arxiv_title, non_arxiv_title)
                if overlap >= min_overlap:
                    print(f"  Removing arXiv duplicate: {arxiv_paper.get('id')}")
                    print(f"    ArXiv title (CoRR): {arxiv_title}")
                    print(f"    Published title: {non_arxiv_title}")
                    print(f"    Overlap: {overlap} words")
                    arxiv_to_remove.add(arxiv_paper.get('id'))
                    break
        
        # Return filtered list
        return [c for c in citations if c.get('id') not in arxiv_to_remove]

    def save_yaml(self, batch_result: BatchConversionResult, 
                  output_path: Union[str, Path]):
        """Save conversion results to YAML file.
        
        Args:
            batch_result: Batch conversion result
            output_path: Output file path
        """
        import yaml
        
        output_path = Path(output_path)
        include_metadata = self.config.get('output.include_metadata', True)
        
        # Get successful citations
        successful_citations = []
        for result in batch_result.conversions:
            if result.success and result.manubot_citation:
                citation_dict = result.manubot_citation.to_dict(include_metadata)
                successful_citations.append(citation_dict)
        
        # Remove arXiv duplicates
        print("Checking for arXiv duplicates...")
        original_count = len(successful_citations)
        successful_citations = self._remove_arxiv_duplicates(successful_citations)
        removed_count = original_count - len(successful_citations)
        if removed_count > 0:
            print(f"Removed {removed_count} arXiv duplicates")
        
        # Sort by year (newest first), then by title for same years
        successful_citations.sort(key=lambda x: (
            -(x.get('year', 0) or 0),  # Negative for descending order, handle None
            x.get('title', '').lower()  # Secondary sort by title
        ))
        
        # Write YAML file as a proper list with line breaks between entries
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, citation in enumerate(successful_citations):
                if i > 0:
                    f.write('\n')  # Add line break between entries
                
                # Write each citation as a list item with proper indentation
                yaml_str = yaml.dump(citation, default_flow_style=False, 
                                   allow_unicode=True, sort_keys=False, indent=2)
                # Remove the '...' document separator that yaml.dump adds
                yaml_str = yaml_str.rstrip('\n...\n').rstrip('\n')
                
                # Add the list item indicator and proper indentation
                lines = yaml_str.split('\n')
                if lines:
                    f.write(f"- {lines[0]}\n")  # First line with list indicator
                    for line in lines[1:]:
                        f.write(f"  {line}\n")  # Indent remaining lines by 2 spaces
    
    def validate_manubot_format(self, yaml_path: Union[str, Path]) -> Dict[str, Any]:
        """Validate generated YAML against Manubot format requirements.
        
        Args:
            yaml_path: Path to YAML file to validate
            
        Returns:
            Validation results dictionary
        """
        import yaml
        
        yaml_path = Path(yaml_path)
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'citation_count': 0,
            'citation_types': {}
        }
        
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Handle both old format (with citations wrapper) and new format (direct list)
            if isinstance(data, dict) and 'citations' in data:
                citations = data.get('citations', [])
            elif isinstance(data, list):
                citations = data
            else:
                citations = []
            
            validation_result['citation_count'] = len(citations)
            
            for i, citation in enumerate(citations):
                citation_id = citation.get('id', '')
                citation_type = citation.get('type', '')
                
                # Count citation types
                if citation_type:
                    validation_result['citation_types'][citation_type] = \
                        validation_result['citation_types'].get(citation_type, 0) + 1
                
                # Validate required fields
                if not citation_id:
                    validation_result['errors'].append(f"Citation {i+1}: Missing 'id' field")
                    validation_result['valid'] = False
                elif ':' not in citation_id:
                    validation_result['errors'].append(f"Citation {i+1}: Invalid ID format '{citation_id}'")
                    validation_result['valid'] = False
                
                if not citation_type:
                    validation_result['errors'].append(f"Citation {i+1}: Missing 'type' field")
                    validation_result['valid'] = False
                
                # Check for recommended fields
                if not citation.get('title'):
                    validation_result['warnings'].append(f"Citation {i+1}: Missing title")
                if not citation.get('authors'):
                    validation_result['warnings'].append(f"Citation {i+1}: Missing authors")
                if not citation.get('year'):
                    validation_result['warnings'].append(f"Citation {i+1}: Missing year")
        
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"YAML parsing error: {str(e)}")
        
        return validation_result