"""
Configuration management for BibTeX to Manubot converter.
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """Configuration manager for the BibTeX to Manubot converter."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            config_path: Path to configuration file. If None, uses default configuration.
        """
        self.config_path = config_path
        self.config = self._load_config() if config_path else self._get_default_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config or self._get_default_config()
        except FileNotFoundError:
            # Return default configuration
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            'citation_priority': [
                'doi',
                'pmid',
                'pmcid',
                'arxiv',
                'isbn',
                'url'
            ],
            'bibtex': {
                'encoding': 'utf-8',
                'strict_parsing': False
            },
            'output': {
                'include_metadata': True,
                'format': 'yaml'
            }
        }
    
    def get(self, key_path: str, default=None):
        """Get configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to configuration value (e.g., 'output.include_metadata')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value