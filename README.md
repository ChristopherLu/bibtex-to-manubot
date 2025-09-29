# BibTeX to Manubot Converter

A Python project for converting BibTeX files to Manubot-formatted YAML citations.

## Features

- Parse BibTeX files and convert entries to Manubot citation format
- Auto-detect citation keys (DOI, PMID, arXiv, ISBN, URLs)
- Generate properly formatted YAML output compatible with Manubot
- Support for various BibTeX entry types (article, book, inproceedings, etc.)
- Batch processing of multiple BibTeX files
- Validation of Manubot citation formats

## Supported Citation Types

- DOI (Digital Object Identifier): `doi:10.1234/example`
- PMID (PubMed ID): `pmid:12345678`
- PMCID (PubMed Central ID): `pmcid:PMC1234567`
- arXiv IDs: `arxiv:1234.5678v1`
- ISBN: `isbn:978-0123456789`
- URLs: `url:https://example.com/paper`
- Raw citations: `raw:bibtex-key` (fallback)

## Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd bibtex_to_manubot

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

```python
from bibtex_to_manubot import BibTeXConverter

converter = BibTeXConverter()

# Convert a single BibTeX file
result = converter.convert_file("references.bib", "output.yaml")

# Convert multiple files
converter.batch_convert(["file1.bib", "file2.bib"], "combined.yaml")
```

### Command Line Interface

```bash
# Convert a single BibTeX file
python -m bibtex_to_manubot convert -i references.bib -o citations.yaml

# Convert with validation
python -m bibtex_to_manubot convert -i references.bib -o citations.yaml --validate

# Convert from DBLP URL directly
python -m bibtex_to_manubot dblp -u https://dblp.org/pid/154/4313.html -o citations.yaml

# Validate existing YAML file
python -m bibtex_to_manubot validate -f citations.yaml
```

## Features

- **Direct DBLP URL Support**: Input DBLP profile URLs and get Manubot YAML output
- **Smart Deduplication**: Automatically removes arXiv duplicates based on CoRR journal detection  
- **Website-Compatible Format**: Uses `publisher` and `link` fields for direct website integration
- **Comprehensive Validation**: Built-in YAML format validation
- **Chronological Sorting**: Automatically sorts citations by publication date

## API Documentation

See the [API Documentation](docs/api.md) for detailed information about the available methods and classes.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.