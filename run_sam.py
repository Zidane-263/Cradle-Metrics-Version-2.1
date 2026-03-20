#!/usr/bin/env python3
"""
Simple SAM Runner - Get Segmentation Masks + Biometric Measurements
No training required!
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sam_processing.sam_pipeline import SAMPosePipeline

def main():
    """Run SAM on your fetal ultrasound images"""
    
    print("="*70)
    print("SAM FETAL SEGMENTATION & BIOMETRICS")
    print("="*70)
    print("\nThis will:")
    print("  1. Segment fetal body parts (head, abdomen, arms, legs)")
    print("  2. Extract biometric measurements (HC, AC, BPD, FL)")
    print("  3. Save visualizations with masks overlaid")
    print("\n" + "="*70)
    
    # CALIBRATION SETTING
    # Set pixel_to_mm to convert measurements to millimeters
    # Example: If 2.5 pixels = 1mm, set pixel_to_mm=2.5
    # Leave as None to use pixels
    PIXEL_TO_MM = 2.5  # Calibration: 2.5 pixels = 1mm
    
    # Initialize SAM pipeline
    print("\n📦 Loading SAM model...")
    pipeline = SAMPosePipeline(
        sam_model_type='vit_b',
        sam_checkpoint='sam_vit_b_01ec64.pth',
        device='cuda',
        pixel_to_mm=PIXEL_TO_MM  # Calibration for mm conversion
    )
    print("✅ SAM model loaded!\n")
    
    # Example: Process one stream
    stream_name = 'stream_hdvb_aroundabd_h'
    
    print(f"🔄 Processing: {stream_name}")
    print("-" * 70)
    
    results = pipeline.process_stream(
        frames_dir=f'four_poses/{stream_name}',
        annotation_file=f'box_annotation/{stream_name}/annotations.xml',
        output_dir=f'sam_results/{stream_name}',
        save_visualizations=True
    )
    
    print("\n" + "="*70)
    print("✅ PROCESSING COMPLETE!")
    print("="*70)
    print(f"\n📊 Results:")
    print(f"  - Total frames processed: {results['total_frames']}")
    print(f"  - Frames with segmentation: {len(results['frame_results'])}")
    print(f"\n📁 Output saved to: sam_results/{stream_name}/")
    print(f"  - Segmentation masks: sam_results/{stream_name}/visualizations/")
    print(f"  - Biometric data: sam_results/{stream_name}/pose_analysis.json")
    
    # Show sample metrics
    if results['frame_results']:
        sample = results['frame_results'][0]
        metrics = sample['metrics']
        unit = metrics.get('unit', 'px')
        
        print(f"\n📏 Sample Biometric Measurements (Frame 1):")
        
        if 'spatial_metrics' in metrics:
            spatial = metrics['spatial_metrics']\
            
            # Clinical biometrics
            if 'head_circumference' in spatial:
                print(f"  - HC (Head Circumference): {spatial['head_circumference']:.1f}{unit}")
            if 'abdomen_circumference' in spatial:
                print(f"  - AC (Abdominal Circumference): {spatial['abdomen_circumference']:.1f}{unit}")
            if 'biparietal_diameter' in spatial:
                print(f"  - BPD (Biparietal Diameter): {spatial['biparietal_diameter']:.1f}{unit}")
            if 'femur_length' in spatial:
                print(f"  - FL (Femur Length): {spatial['femur_length']:.1f}{unit}")
            
            # Other measurements
            if 'head_abdomen_distance' in spatial:
                print(f"  - Head-Abdomen Distance: {spatial['head_abdomen_distance']:.1f}{unit}")
            if 'body_length' in spatial:
                print(f"  - Body Length: {spatial['body_length']:.1f}{unit}")
        
        print(f"\n💡 Check visualizations folder to see segmented masks!")
        
        if unit == 'px':
            print(f"\n⚠️  Measurements are in PIXELS. Set PIXEL_TO_MM for mm conversion.")
            print(f"   See calibration_guide.md for instructions.")
    
    print("\n" + "="*70)
    print("🎉 Done! No training required!")
    print("="*70)

if __name__ == "__main__":
    main()
