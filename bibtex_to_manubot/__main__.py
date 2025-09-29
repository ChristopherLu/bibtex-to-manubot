"""
Command line interface for BibTeX to Manubot converter.
"""

import click
from pathlib import Path
from typing import Optional, List
import glob
import os

from .converter import BibTeXConverter
from .models import BatchConversionResult
from .dblp_scraper import DBLPScraper, validate_dblp_url


@click.command()
@click.option('--input', '-i', 'input_path', required=True,
              help='BibTeX file(s) to convert (supports wildcards like *.bib) or DBLP profile URL')
@click.option('--output', '-o', 'output_path', type=click.Path(), 
              help='Output YAML file path (default: citations.yaml)')
@click.option('--config', '-c', 'config_path', type=click.Path(exists=True),
              help='Configuration file path')
@click.option('--validate', is_flag=True, 
              help='Validate output YAML format after conversion')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--include-failed', is_flag=True, default=True,
              help='Include failed conversions in output YAML')
def main(input_path: str, output_path: Optional[str], config_path: Optional[str], 
         validate: bool, verbose: bool, include_failed: bool):
    """BibTeX to Manubot Converter - Convert BibTeX files to Manubot YAML format."""
    
    # Check if input is a DBLP URL
    is_dblp_url = input_path.startswith(('http://', 'https://')) and 'dblp.org' in input_path
    
    if is_dblp_url:
        # Handle DBLP profile URL
        is_valid, result = validate_dblp_url(input_path)
        if not is_valid:
            click.echo(f"Error: {result}", err=True)
            return
        
        dblp_url = result
        if verbose:
            click.echo(f"DBLP Profile URL: {dblp_url}")
        
        # Scrape DBLP profile to get BibTeX
        try:
            scraper = DBLPScraper(delay=1.0)
            
            # Get profile info for user feedback
            if verbose:
                info = scraper.get_profile_info(dblp_url)
                if info.get('name'):
                    click.echo(f"Author: {info['name']}")
                if info.get('publication_count'):
                    click.echo(f"Estimated publications: {info['publication_count']}")
            
            # Download BibTeX to temporary file
            temp_bibtex_path = scraper.scrape_profile_to_file(dblp_url)
            input_files = [temp_bibtex_path]
            
        except Exception as e:
            click.echo(f"Error fetching DBLP profile: {e}", err=True)
            return
    else:
        # Handle file paths with wildcards
        input_files = []
        if '*' in input_path or '?' in input_path:
            input_files = glob.glob(input_path)
            if not input_files:
                click.echo(f"Error: No files found matching pattern: {input_path}", err=True)
                return
        else:
            input_files = [input_path]
    
    # Verify input files exist
    missing_files = []
    for file_path in input_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        click.echo(f"Error: Input file(s) not found: {', '.join(missing_files)}", err=True)
        return
    
    # Set default output path
    if not output_path:
        if is_dblp_url:
            # Create meaningful filename from DBLP URL
            try:
                scraper = DBLPScraper()
                pid = scraper.extract_pid_from_url(input_path)
                if pid:
                    filename = f"dblp_{pid.replace('/', '_')}_citations.yaml"
                else:
                    filename = "dblp_citations.yaml"
                output_path = filename
            except:
                output_path = "dblp_citations.yaml"
        elif len(input_files) == 1:
            input_stem = Path(input_files[0]).stem
            output_path = f"{input_stem}_manubot.yaml"
        else:
            output_path = "citations.yaml"
    
    # Initialize converter
    try:
        converter = BibTeXConverter(config_path)
    except Exception as e:
        click.echo(f"Error initializing converter: {e}", err=True)
        return
    
    if verbose:
        click.echo(f"Input files: {', '.join(input_files)}")
        click.echo(f"Output file: {output_path}")
        click.echo("Converting BibTeX to Manubot format...")
    
    try:
        # Convert files
        result = converter.batch_convert(input_files, output_path)
        
        # Display summary
        click.echo(f"\nConversion Summary:")
        click.echo(f"Input files: {len(result.input_files)}")
        click.echo(f"Total entries: {result.total_entries}")
        click.echo(f"Successful conversions: {result.successful_conversions}")
        click.echo(f"Failed conversions: {result.failed_conversions}")
        click.echo(f"Success rate: {result.success_rate:.1f}%")
        click.echo(f"Processing time: {result.processing_time:.2f}s")
        click.echo(f"Output saved to: {output_path}")
        
        # Show detailed results if verbose
        if verbose and result.conversions:
            click.echo(f"\nDetailed Results:")
            for i, conversion in enumerate(result.conversions, 1):
                status = "✓" if conversion.success else "✗"
                click.echo(f"{i:3d}. {status} {conversion.original_key}")
                
                if conversion.success and conversion.manubot_citation:
                    click.echo(f"     → {conversion.manubot_citation.id}")
                    if conversion.warnings:
                        for warning in conversion.warnings:
                            click.echo(f"     ⚠ {warning}", color='yellow')
                elif not conversion.success:
                    for error in conversion.errors:
                        click.echo(f"     ✗ {error}")
        
        # Show warnings and errors summary
        total_warnings = sum(len(c.warnings) for c in result.conversions)
        total_errors = sum(len(c.errors) for c in result.conversions)
        
        if total_warnings > 0:
            click.echo(f"\nTotal warnings: {total_warnings}")
        if total_errors > 0:
            click.echo(f"Total errors: {total_errors}")
        
        # Validate output if requested
        if validate:
            click.echo(f"\nValidating output format...")
            try:
                validation_result = converter.validate_manubot_format(output_path)
                
                if validation_result['valid']:
                    click.echo("✓ Output YAML format is valid")
                else:
                    click.echo("✗ Output YAML format has issues:")
                    for error in validation_result['errors']:
                        click.echo(f"  - {error}")
                
                if validation_result['warnings']:
                    click.echo("Validation warnings:")
                    for warning in validation_result['warnings']:
                        click.echo(f"  - {warning}")
                
                # Show citation type distribution
                if validation_result['citation_types']:
                    click.echo(f"\nCitation Types:")
                    for ctype, count in validation_result['citation_types'].items():
                        click.echo(f"  {ctype}: {count}")
            
            except Exception as e:
                click.echo(f"Validation error: {e}", err=True)
        
        # Show sample citations if verbose
        if verbose and result.successful_conversions > 0:
            click.echo(f"\nSample Citations (first 3):")
            successful_citations = result.get_successful_citations()
            for i, citation in enumerate(successful_citations[:3], 1):
                click.echo(f"{i}. {citation.id}")
                if citation.title:
                    title = citation.title[:60] + "..." if len(citation.title) > 60 else citation.title
                    click.echo(f"   Title: {title}")
                if citation.authors:
                    authors = ", ".join(citation.authors[:3])
                    if len(citation.authors) > 3:
                        authors += " et al."
                    click.echo(f"   Authors: {authors}")
    
    except Exception as e:
        click.echo(f"Error during conversion: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
    
    finally:
        # Clean up temporary BibTeX file if we created one from DBLP
        if is_dblp_url and input_files:
            temp_file = input_files[0]
            if os.path.exists(temp_file) and temp_file.startswith(os.path.join(os.path.expanduser('~'), '.tmp')):
                try:
                    os.remove(temp_file)
                    if verbose:
                        click.echo(f"Cleaned up temporary file: {temp_file}")
                except:
                    pass  # Ignore cleanup errors


@click.command()
@click.option('--dblp-url', '-u', required=True,
              help='DBLP profile URL (e.g., https://dblp.org/pid/154/4313.html)')
@click.option('--output', '-o', 'output_path', type=click.Path(),
              help='Output YAML file path (default: dblp_citations.yaml)')
@click.option('--validate', is_flag=True,
              help='Validate output YAML format after conversion')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def dblp(dblp_url: str, output_path: Optional[str], validate: bool, verbose: bool):
    """Convert DBLP profile directly to website-ready YAML format."""
    
    # Validate DBLP URL
    is_valid, result = validate_dblp_url(dblp_url)
    if not is_valid:
        click.echo(f"Error: {result}", err=True)
        return
    
    normalized_url = result
    
    if verbose:
        click.echo(f"DBLP Profile: {normalized_url}")
    
    try:
        # Initialize scraper and converter
        scraper = DBLPScraper(delay=1.0)
        converter = BibTeXConverter()
        
        # Get profile info
        if verbose:
            click.echo("Fetching profile information...")
            info = scraper.get_profile_info(normalized_url)
            if info.get('name'):
                click.echo(f"Author: {info['name']}")
            if info.get('publication_count'):
                click.echo(f"Estimated publications: {info['publication_count']}")
        
        # Set default output path
        if not output_path:
            pid = scraper.extract_pid_from_url(normalized_url)
            if pid:
                output_path = f"dblp_{pid.replace('/', '_')}_citations.yaml"
            else:
                output_path = "dblp_citations.yaml"
        
        # Scrape BibTeX data
        click.echo("Downloading BibTeX data from DBLP...")
        temp_bibtex_path = scraper.scrape_profile_to_file(normalized_url)
        
        try:
            # Convert to website format
            result = converter.batch_convert([temp_bibtex_path], output_path)
            
            # Display results
            click.echo(f"\n🎉 Conversion Complete!")
            click.echo(f"📊 Statistics:")
            click.echo(f"  • Total entries: {result.total_entries}")
            click.echo(f"  • Successful conversions: {result.successful_conversions}")
            click.echo(f"  • Failed conversions: {result.failed_conversions}")
            click.echo(f"  • Success rate: {result.success_rate:.1f}%")
            click.echo(f"  • Processing time: {result.processing_time:.2f}s")
            click.echo(f"📄 Output saved to: {output_path}")
            
            # Validate if requested
            if validate:
                click.echo(f"\nValidating output format...")
                validation_result = converter.validate_manubot_format(output_path)
                
                if validation_result['valid']:
                    click.echo("✓ Output YAML format is valid")
                else:
                    click.echo("✗ Output YAML format has issues:")
                    for error in validation_result['errors']:
                        click.echo(f"  - {error}")
                
                # Show citation type distribution
                if validation_result['citation_types']:
                    click.echo(f"\nCitation Types:")
                    for ctype, count in validation_result['citation_types'].items():
                        click.echo(f"  {ctype}: {count}")
            
            # Show sample citations
            if result.successful_conversions > 0:
                click.echo(f"\nSample Citations (first 3):")
                successful_citations = result.get_successful_citations()
                for i, citation in enumerate(successful_citations[:3], 1):
                    click.echo(f"{i}. {citation.id}")
                    if citation.title:
                        title = citation.title[:60] + "..." if len(citation.title) > 60 else citation.title
                        click.echo(f"   Title: {title}")
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_bibtex_path):
                os.remove(temp_bibtex_path)
                if verbose:
                    click.echo(f"Cleaned up temporary file: {temp_bibtex_path}")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()


@click.command()
@click.option('--yaml-file', '-y', required=True, type=click.Path(exists=True),
              help='YAML file to validate')
def validate_yaml(yaml_file: str):
    """Validate a Manubot YAML file format."""
    try:
        converter = BibTeXConverter()
        result = converter.validate_manubot_format(yaml_file)
        
        click.echo(f"Validating: {yaml_file}")
        click.echo(f"Citations found: {result['citation_count']}")
        
        if result['valid']:
            click.echo("✓ YAML format is valid for Manubot")
        else:
            click.echo("✗ YAML format has issues:")
            for error in result['errors']:
                click.echo(f"  - {error}")
        
        if result['warnings']:
            click.echo("Warnings:")
            for warning in result['warnings']:
                click.echo(f"  - {warning}")
        
        if result['citation_types']:
            click.echo(f"\nCitation Types:")
            for ctype, count in result['citation_types'].items():
                click.echo(f"  {ctype}: {count}")
    
    except Exception as e:
        click.echo(f"Validation error: {e}", err=True)


@click.command()
@click.option('--input', '-i', 'input_file', required=True, type=click.Path(exists=True),
              help='YAML file containing DBLP URLs and output configurations')
@click.option('--validate', is_flag=True, 
              help='Validate output YAML format after conversion')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def batch_dblp(input_file: str, validate: bool, verbose: bool):
    """Batch process multiple DBLP URLs from a configuration YAML file.
    
    Input YAML format:
    profiles:
      - name: "Researcher Name"
        url: "https://dblp.org/pid/xxx/xxxx.html"
        output: "researcher_citations.yaml"
      - name: "Another Researcher"
        url: "https://dblp.org/pid/yyy/yyyy.html"
        output: "another_citations.yaml"
    """
    import yaml
    from datetime import datetime
    import tempfile
    
    try:
        # Load the batch configuration
        with open(input_file, 'r') as f:
            config = yaml.safe_load(f)
        
        if 'profiles' not in config:
            click.echo("Error: Input YAML must contain 'profiles' key", err=True)
            return
        
        profiles = config['profiles']
        if not isinstance(profiles, list) or len(profiles) == 0:
            click.echo("Error: 'profiles' must be a non-empty list", err=True)
            return
        
        click.echo(f"🔄 Processing {len(profiles)} DBLP profiles...")
        
        scraper = DBLPScraper(delay=1.5)  # Slightly longer delay for batch processing
        converter = BibTeXConverter()
        
        total_success = 0
        total_failed = 0
        results = []
        
        for i, profile in enumerate(profiles, 1):
            if not isinstance(profile, dict):
                click.echo(f"❌ Profile {i}: Invalid format (must be dictionary)", err=True)
                total_failed += 1
                continue
            
            name = profile.get('name', f'Profile {i}')
            url = profile.get('url')
            output_path = profile.get('output')
            
            if not url or not output_path:
                click.echo(f"❌ {name}: Missing 'url' or 'output' field", err=True)
                total_failed += 1
                continue
            
            # Validate DBLP URL
            is_valid, validation_result = validate_dblp_url(url)
            if not is_valid:
                click.echo(f"❌ {name}: Invalid DBLP URL - {validation_result}", err=True)
                total_failed += 1
                continue
            
            click.echo(f"\n📖 Processing {i}/{len(profiles)}: {name}")
            click.echo(f"   URL: {url}")
            click.echo(f"   Output: {output_path}")
            
            try:
                # Scrape DBLP profile
                if verbose:
                    click.echo("   Downloading BibTeX data from DBLP...")
                
                profile_info = scraper.get_profile_info(url)
                if verbose and profile_info:
                    click.echo(f"   Profile: {profile_info.get('name', 'Unknown')}")
                
                # Get BibTeX content as string
                bibtex_content = scraper.scrape_profile_to_bibtex(url)
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False) as temp_file:
                    temp_file.write(bibtex_content)
                    bibtex_path = temp_file.name
                
                # Convert to Manubot format
                result = converter.convert_file(bibtex_path, output_path)
                
                # Clean up temporary file
                os.unlink(bibtex_path)
                
                if result.successful_conversions > 0:
                    click.echo(f"   ✅ Success: {result.successful_conversions} citations → {output_path}")
                    total_success += 1
                    
                    if verbose:
                        click.echo(f"      Total entries: {result.total_entries}")
                        click.echo(f"      Processing time: {result.processing_time:.2f}s")
                    
                    # Validate if requested
                    if validate:
                        try:
                            validation_result = converter.validate_manubot_format(Path(output_path))
                            if validation_result['valid']:
                                click.echo(f"      ✓ YAML format validated")
                            else:
                                click.echo(f"      ⚠️  YAML validation warnings: {len(validation_result['errors'])} errors")
                        except Exception as e:
                            click.echo(f"      ⚠️  Validation error: {e}")
                else:
                    click.echo(f"   ❌ Failed: No successful conversions")
                    total_failed += 1
                
                results.append({
                    'name': name,
                    'url': url,
                    'output': output_path,
                    'success': result.successful_conversions > 0,
                    'citations': result.successful_conversions,
                    'processing_time': result.processing_time
                })
                
            except Exception as e:
                click.echo(f"   ❌ Error: {str(e)}", err=True)
                total_failed += 1
        
        # Summary
        click.echo(f"\n🎉 Batch Processing Complete!")
        click.echo(f"📊 Summary:")
        click.echo(f"   • Total profiles: {len(profiles)}")
        click.echo(f"   • Successful: {total_success}")
        click.echo(f"   • Failed: {total_failed}")
        click.echo(f"   • Success rate: {total_success/len(profiles)*100:.1f}%")
        
        if verbose and results:
            click.echo(f"\n📄 Detailed Results:")
            for result in results:
                status = "✅" if result['success'] else "❌"
                click.echo(f"   {status} {result['name']}: {result['citations']} citations")
    
    except FileNotFoundError:
        click.echo(f"Error: Input file '{input_file}' not found", err=True)
    except yaml.YAMLError as e:
        click.echo(f"Error: Invalid YAML format in '{input_file}': {e}", err=True)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@click.group()
def cli():
    """BibTeX to Manubot Converter - Convert academic bibliographies to website-ready format."""
    pass


# Add commands to the group
cli.add_command(main, name='convert')
cli.add_command(dblp, name='dblp')
cli.add_command(batch_dblp, name='batch-dblp')
cli.add_command(validate_yaml, name='validate')


if __name__ == '__main__':
    cli()