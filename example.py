"""
Example usage of the BibTeX to Manubot converter.
"""

from pathlib import Path
from bibtex_to_manubot import BibTeXConverter


def main():
    """Example usage of the BibTeX to Manubot converter."""
    
    print("BibTeX to Manubot Converter Example")
    print("=" * 50)
    
    # Initialize the converter
    converter = BibTeXConverter()
    
    # Example 1: Convert single BibTeX file
    print("\n1. Converting BibTeX File:")
    
    example_file = Path(__file__).parent / "example.bib"
    
    if example_file.exists():
        try:
            result = converter.convert_file(
                example_file,
                output_path="example_citations.yaml"
            )
            
            print(f"Input file: {example_file}")
            print(f"Total entries: {result.total_entries}")
            print(f"Successful conversions: {result.successful_conversions}")
            print(f"Failed conversions: {result.failed_conversions}")
            print(f"Success rate: {result.success_rate:.1f}%")
            print(f"Processing time: {result.processing_time:.2f}s")
            print("Output saved to: example_citations.yaml")
            
            # Show sample conversions
            print("\nSample conversions:")
            for i, conversion in enumerate(result.conversions[:3], 1):
                if conversion.success:
                    print(f"{i}. {conversion.original_key}")
                    print(f"   → {conversion.manubot_citation.id}")
                    if conversion.manubot_citation.title:
                        title = conversion.manubot_citation.title[:60] + "..." if len(conversion.manubot_citation.title) > 60 else conversion.manubot_citation.title
                        print(f"   Title: {title}")
                else:
                    print(f"{i}. {conversion.original_key} - FAILED")
                    print(f"   Errors: {'; '.join(conversion.errors)}")
        
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Example BibTeX file not found")
    
    # Example 2: Show individual entry conversion
    print("\n2. Individual Entry Conversion:")
    
    if example_file.exists():
        try:
            entries = converter.parse_bibtex_file(example_file)
            
            if entries:
                # Convert first entry
                first_entry = entries[0]
                conversion_result = converter.convert_entry(first_entry)
                
                print(f"Original BibTeX key: {first_entry.key}")
                print(f"Entry type: {first_entry.entry_type}")
                print(f"Title: {first_entry.title}")
                print(f"Authors: {', '.join(first_entry.authors) if first_entry.authors else 'None'}")
                print(f"Year: {first_entry.year}")
                print(f"DOI: {first_entry.doi}")
                
                print(f"\nConversion result:")
                if conversion_result.success:
                    print(f"✓ Success: {conversion_result.manubot_citation.id}")
                    print(f"  Citation type: {conversion_result.manubot_citation.citation_type}")
                else:
                    print(f"✗ Failed: {'; '.join(conversion_result.errors)}")
        
        except Exception as e:
            print(f"Error: {e}")
    
    # Example 3: Validate output YAML
    print("\n3. Validating Output YAML:")
    
    yaml_file = Path("example_citations.yaml")
    if yaml_file.exists():
        try:
            validation_result = converter.validate_manubot_format(yaml_file)
            
            print(f"YAML file: {yaml_file}")
            print(f"Citations found: {validation_result['citation_count']}")
            print(f"Valid format: {validation_result['valid']}")
            
            if validation_result['citation_types']:
                print("\nCitation types:")
                for ctype, count in validation_result['citation_types'].items():
                    print(f"  {ctype}: {count}")
            
            if validation_result['errors']:
                print("\nValidation errors:")
                for error in validation_result['errors']:
                    print(f"  - {error}")
            
            if validation_result['warnings']:
                print("\nValidation warnings:")
                for warning in validation_result['warnings']:
                    print(f"  - {warning}")
        
        except Exception as e:
            print(f"Validation error: {e}")
    else:
        print("Output YAML file not found")
    
    # Example 4: Command-line usage instructions
    print("\n4. Command-line Usage Examples:")
    print("Convert a single BibTeX file:")
    print("  python -m bibtex_to_manubot -i example.bib -o citations.yaml")
    print("\nConvert multiple BibTeX files:")
    print("  python -m bibtex_to_manubot -i '*.bib' -o all_citations.yaml")
    print("\nConvert with validation:")
    print("  python -m bibtex_to_manubot -i example.bib -o citations.yaml --validate")
    print("\nValidate existing YAML:")
    print("  python -m bibtex_to_manubot validate -f citations.yaml")


if __name__ == "__main__":
    main()