#!/usr/bin/env python3
"""
Batch Processor for Fetal Ultrasound Analysis
Process multiple images and generate comprehensive reports
"""

import sys
from pathlib import Path
import cv2
import pandas as pd
from typing import List, Dict
from tqdm import tqdm
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from automatic_pipeline import AutomaticPipeline
from clinical_history import ClinicalHistoryManager


class BatchProcessor:
    """Process multiple ultrasound images in batch"""
    
    def __init__(self, yolo_model_path: str = 'runs/detect/fetal_detection/weights/best.pt',
                 sam_checkpoint: str = 'sam_vit_b_01ec64.pth',
                 pixel_to_mm: float = 2.5,
                 enable_clinical: bool = True,
                 ga_weeks: float = None,
                 patient_id: str = None):
        """Initialize batch processor"""
        
        self.patient_id = patient_id
        self.history_manager = ClinicalHistoryManager()
        
        print("="*70)
        print("Batch Processor - Fetal Ultrasound Analysis")
        print("="*70)
        
        # Initialize automatic pipeline
        self.pipeline = AutomaticPipeline(
            yolo_model_path=yolo_model_path,
            sam_checkpoint=sam_checkpoint,
            pixel_to_mm=pixel_to_mm,
            confidence_threshold=0.5,
            enable_clinical=enable_clinical,
            ga_weeks=ga_weeks
        )
        
        self.results = []
    
    def find_images(self, input_dir: str, extensions: List[str] = None) -> List[Path]:
        """Find all image files in directory"""
        if extensions is None:
            extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff']
        
        input_path = Path(input_dir)
        images = []
        
        for ext in extensions:
            images.extend(input_path.glob(f'*{ext}'))
            images.extend(input_path.glob(f'*{ext.upper()}'))
        
        return sorted(images)
    
    def process_batch(self, input_dir: str, output_dir: str = 'batch_results') -> pd.DataFrame:
        """
        Process all images in a directory
        
        Args:
            input_dir: Directory containing images
            output_dir: Output directory for results
        
        Returns:
            DataFrame with all results
        """
        # Find images
        images = self.find_images(input_dir)
        
        if not images:
            print(f"⚠️  No images found in {input_dir}")
            return pd.DataFrame()
        
        print(f"\n📁 Found {len(images)} images to process")
        print(f"📂 Output directory: {output_dir}\n")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Process each image
        for img_path in tqdm(images, desc="Processing images"):
            try:
                result = self._process_single_image(img_path, output_path)
                self.results.append(result)
            except Exception as e:
                print(f"\n❌ Error processing {img_path.name}: {e}")
                # Add error entry
                self.results.append({
                    'image': img_path.name,
                    'status': 'error',
                    'error': str(e)
                })
        
        # Create DataFrame
        df = pd.DataFrame(self.results)
        
        # Save results
        self._save_results(df, output_path)
        
        # Save to clinical history if patient_id is provided
        if self.patient_id and not df.empty:
            print(f"\n📂 Importing {len(df)} records into Patient History: {self.patient_id}")
            for _, row in df.iterrows():
                if row['status'] == 'success':
                    # Prepare record for ClinicalHistoryManager
                    scan_data = {
                        'file_id': f"batch_{row['image'].split('.')[0]}",
                        'measurements': {
                            'HC': row.get('HC'),
                            'AC': row.get('AC'),
                            'BPD': row.get('BPD'),
                            'FL': row.get('FL')
                        },
                        'clinical': {
                            'estimated_ga': row.get('estimated_GA'),
                            'consistency': row.get('GA_consistency')
                        },
                        'risk_assessment': {
                            'growth': row.get('growth_status'),
                            'status': 'Complete'
                        }
                    }
                    self.history_manager.save_record(self.patient_id, scan_data)
        
        # Generate summary
        self._print_summary(df)
        
        return df
    
    def _process_single_image(self, img_path: Path, output_dir: Path) -> Dict:
        """Process a single image"""
        
        # Process with automatic pipeline
        results = self.pipeline.process_image(
            str(img_path),
            output_dir=str(output_dir / 'visualizations')
        )
        
        # Extract measurements
        metrics = results['segmentation']['metrics']
        spatial = metrics.get('spatial_metrics', {})
        
        # Build result dictionary
        result = {
            'image': img_path.name,
            'status': 'success',
            'pose': metrics.get('pose_label', 'unknown'),
            'detections': len(results['detections']),
        }
        
        # Add biometric measurements
        if 'head_circumference' in spatial:
            result['HC'] = round(spatial['head_circumference'], 1)
        if 'abdomen_circumference' in spatial:
            result['AC'] = round(spatial['abdomen_circumference'], 1)
        if 'biparietal_diameter' in spatial:
            result['BPD'] = round(spatial['biparietal_diameter'], 1)
        if 'femur_length' in spatial:
            result['FL'] = round(spatial['femur_length'], 1)
        
        # Add clinical assessment if available
        if self.pipeline.enable_clinical and spatial:
            measurements = {}
            if 'head_circumference' in spatial:
                measurements['HC'] = spatial['head_circumference']
            if 'abdomen_circumference' in spatial:
                measurements['AC'] = spatial['abdomen_circumference']
            if 'biparietal_diameter' in spatial:
                measurements['BPD'] = spatial['biparietal_diameter']
            if 'femur_length' in spatial:
                measurements['FL'] = spatial['femur_length']
            
            if measurements:
                clinical = self.pipeline.clinical_assessor.assess_all_measurements(
                    measurements, self.pipeline.ga_weeks
                )
                
                # Add percentiles
                for metric, data in clinical['measurements'].items():
                    result[f'{metric}_percentile'] = round(data['percentile'], 1)
                    result[f'{metric}_classification'] = data['classification']
                
                # Add GA estimate
                if clinical['consensus_ga']:
                    result['estimated_GA'] = round(clinical['consensus_ga'], 1)
                    result['GA_consistency'] = clinical['ga_consistency']
                
                # Add overall assessment
                result['growth_status'] = clinical['overall_assessment']['status']
        
        result['unit'] = metrics.get('unit', 'px')
        
        return result
    
    def _save_results(self, df: pd.DataFrame, output_dir: Path):
        """Save results to CSV and JSON"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save CSV
        csv_path = output_dir / f'batch_results_{timestamp}.csv'
        df.to_csv(csv_path, index=False)
        print(f"\n✅ Results saved to: {csv_path}")
        
        # Save JSON (more detailed)
        json_path = output_dir / f'batch_results_{timestamp}.json'
        df.to_json(json_path, orient='records', indent=2)
        print(f"✅ Detailed results saved to: {json_path}")
    
    def _print_summary(self, df: pd.DataFrame):
        """Print summary statistics"""
        
        print("\n" + "="*70)
        print("📊 Batch Processing Summary")
        print("="*70)
        
        # Success rate
        total = len(df)
        success = len(df[df['status'] == 'success'])
        print(f"\nProcessed: {total} images")
        print(f"Success: {success} ({success/total*100:.1f}%)")
        if total > success:
            print(f"Errors: {total - success}")
        
        # Measurements summary
        if 'HC' in df.columns:
            print(f"\nHead Circumference (HC):")
            print(f"  Mean: {df['HC'].mean():.1f} {df['unit'].iloc[0]}")
            print(f"  Range: {df['HC'].min():.1f} - {df['HC'].max():.1f} {df['unit'].iloc[0]}")
        
        if 'AC' in df.columns:
            print(f"\nAbdominal Circumference (AC):")
            print(f"  Mean: {df['AC'].mean():.1f} {df['unit'].iloc[0]}")
            print(f"  Range: {df['AC'].min():.1f} - {df['AC'].max():.1f} {df['unit'].iloc[0]}")
        
        if 'estimated_GA' in df.columns:
            print(f"\nEstimated Gestational Age:")
            print(f"  Mean: {df['estimated_GA'].mean():.1f} weeks")
            print(f"  Range: {df['estimated_GA'].min():.1f} - {df['estimated_GA'].max():.1f} weeks")
        
        # Growth classification summary
        if 'growth_status' in df.columns:
            print(f"\nGrowth Classification:")
            for status, count in df['growth_status'].value_counts().items():
                print(f"  {status}: {count} ({count/total*100:.1f}%)")
        
        print("\n" + "="*70)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch Process Fetal Ultrasound Images')
    parser.add_argument('--input', type=str, required=True, help='Input directory with images')
    parser.add_argument('--output', type=str, default='batch_results', help='Output directory')
    parser.add_argument('--calibration', type=float, default=2.5, help='Pixel-to-mm calibration')
    parser.add_argument('--ga', type=float, default=None, help='Known gestational age (weeks)')
    parser.add_argument('--no-clinical', action='store_true', help='Disable clinical assessment')
    
    args = parser.parse_args()
    
    # Create batch processor
    processor = BatchProcessor(
        pixel_to_mm=args.calibration,
        enable_clinical=not args.no_clinical,
        ga_weeks=args.ga
    )
    
    # Process batch
    results_df = processor.process_batch(args.input, args.output)
    
    print(f"\n✅ Batch processing complete!")
    print(f"📁 Results saved to: {args.output}/")


if __name__ == "__main__":
    main()
