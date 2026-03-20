#!/usr/bin/env python3
"""
Simple batch processing script using config file
"""

import yaml
from pathlib import Path
from batch_processor import BatchProcessor


def load_config(config_path: str = 'batch_config.yaml') -> dict:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def main():
    """Run batch processing using config file"""
    
    # Load config
    print("Loading configuration from batch_config.yaml...")
    config = load_config()
    
    # Create batch processor
    processor = BatchProcessor(
        pixel_to_mm=config['PIXEL_TO_MM'],
        enable_clinical=config.get('ENABLE_CLINICAL_ASSESSMENT', True),
        ga_weeks=config.get('GESTATIONAL_AGE_WEEKS'),
        patient_id=config.get('PATIENT_ID')
    )
    
    # Process batch
    results_df = processor.process_batch(
        input_dir=config['INPUT_DIR'],
        output_dir=config['OUTPUT_DIR']
    )
    
    print(f"\n✅ Batch processing complete!")
    print(f"📁 Results saved to: {config['OUTPUT_DIR']}/")


if __name__ == "__main__":
    main()
