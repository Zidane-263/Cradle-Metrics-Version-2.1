#!/usr/bin/env python3
"""
Batch Process Entire Dataset with SAM Pipeline
Process all 39 streams (~15,113 frames) with pose estimation and metric extraction
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
import time
from datetime import datetime
from sam_processing.sam_pipeline import SAMPosePipeline
from training.dataset_utils import DatasetValidator


class DatasetBatchProcessor:
    """Process entire dataset with progress tracking and error handling"""
    
    def __init__(self, mapping_file: str = "dataset_mapping.json", 
                 output_base_dir: str = "results",
                 sam_model_type: str = 'vit_b',
                 sam_checkpoint: str = 'sam_vit_b_01ec64.pth'):
        """
        Initialize batch processor
        
        Args:
            mapping_file: Path to dataset mapping JSON
            output_base_dir: Base directory for all results
            sam_model_type: SAM model type
            sam_checkpoint: Path to SAM checkpoint
        """
        self.mapping_file = mapping_file
        self.output_base_dir = Path(output_base_dir)
        self.output_base_dir.mkdir(exist_ok=True)
        
        # Load dataset mapping
        print("Loading dataset mapping...")
        self.validator = DatasetValidator(mapping_file)
        
        # Initialize SAM pipeline
        print("Initializing SAM pipeline...")
        self.pipeline = SAMPosePipeline(
            sam_model_type=sam_model_type,
            sam_checkpoint=sam_checkpoint,
            device='cuda'
        )
        
        # Progress tracking
        self.progress_file = self.output_base_dir / 'processing_progress.json'
        self.progress = self.load_progress()
        
    def load_progress(self):
        """Load processing progress from file"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {
            'completed_streams': [],
            'failed_streams': [],
            'total_frames_processed': 0,
            'start_time': None,
            'last_update': None
        }
    
    def save_progress(self):
        """Save processing progress to file"""
        self.progress['last_update'] = datetime.now().isoformat()
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def process_all_streams(self, save_visualizations: bool = True, 
                           skip_completed: bool = True,
                           stream_filter: dict = None):
        """
        Process all streams in the dataset
        
        Args:
            save_visualizations: Whether to save visualization images
            skip_completed: Skip already processed streams
            stream_filter: Optional filter dict (e.g., {'type': 'hdvb'})
        """
        # Get list of streams
        if stream_filter:
            streams = self.validator.list_streams(**stream_filter)
        else:
            streams = self.validator.config['streams']
        
        total_streams = len(streams)
        
        # Filter out completed streams if requested
        if skip_completed:
            streams = [s for s in streams 
                      if s['stream_id'] not in self.progress['completed_streams']]
        
        print("\n" + "="*70)
        print(f"BATCH PROCESSING: {len(streams)} streams")
        print("="*70)
        print(f"Total streams in dataset: {total_streams}")
        print(f"Already completed: {len(self.progress['completed_streams'])}")
        print(f"To process: {len(streams)}")
        print(f"Save visualizations: {save_visualizations}")
        print("="*70 + "\n")
        
        if self.progress['start_time'] is None:
            self.progress['start_time'] = datetime.now().isoformat()
        
        # Process each stream
        for idx, stream in enumerate(streams, 1):
            stream_id = stream['stream_id']
            
            print(f"\n{'='*70}")
            print(f"[{idx}/{len(streams)}] Processing: {stream_id}")
            print(f"{'='*70}")
            
            try:
                # Create output directory for this stream
                stream_output_dir = self.output_base_dir / stream_id
                stream_output_dir.mkdir(exist_ok=True)
                
                # Check if already processed
                results_file = stream_output_dir / 'pose_analysis.json'
                if results_file.exists() and skip_completed:
                    print(f"⏭️  Skipping (already processed)")
                    continue
                
                # Process stream
                start_time = time.time()
                
                results = self.pipeline.process_stream(
                    frames_dir=stream['frames_dir'],
                    annotation_file=stream['box_annotation_file'],
                    output_dir=str(stream_output_dir),
                    save_visualizations=save_visualizations
                )
                
                elapsed_time = time.time() - start_time
                
                # Update progress
                self.progress['completed_streams'].append(stream_id)
                self.progress['total_frames_processed'] += results['total_frames']
                self.save_progress()
                
                # Print summary
                print(f"\n✅ Completed in {elapsed_time:.1f} seconds")
                print(f"   Frames processed: {len(results['frame_results'])}")
                print(f"   Results saved to: {stream_output_dir}")
                
                # Estimate remaining time
                avg_time_per_stream = elapsed_time
                remaining_streams = len(streams) - idx
                estimated_remaining = avg_time_per_stream * remaining_streams
                
                print(f"\n📊 Progress: {idx}/{len(streams)} streams")
                print(f"   Estimated time remaining: {estimated_remaining/60:.1f} minutes")
                
            except Exception as e:
                print(f"\n❌ Error processing {stream_id}: {e}")
                self.progress['failed_streams'].append({
                    'stream_id': stream_id,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                self.save_progress()
                
                # Continue with next stream
                continue
        
        # Final summary
        self.print_final_summary()
    
    def print_final_summary(self):
        """Print final processing summary"""
        print("\n" + "="*70)
        print("BATCH PROCESSING COMPLETE!")
        print("="*70)
        
        total_completed = len(self.progress['completed_streams'])
        total_failed = len(self.progress['failed_streams'])
        total_frames = self.progress['total_frames_processed']
        
        print(f"\n✅ Successfully processed: {total_completed} streams")
        print(f"❌ Failed: {total_failed} streams")
        print(f"📊 Total frames processed: {total_frames}")
        
        if self.progress['start_time']:
            start = datetime.fromisoformat(self.progress['start_time'])
            end = datetime.now()
            duration = (end - start).total_seconds()
            print(f"⏱️  Total time: {duration/3600:.2f} hours")
            print(f"   Average: {duration/total_completed:.1f} seconds per stream")
        
        print(f"\n📁 Results saved to: {self.output_base_dir}")
        
        if total_failed > 0:
            print(f"\n⚠️  Failed streams:")
            for failed in self.progress['failed_streams']:
                print(f"   - {failed['stream_id']}: {failed['error']}")
        
        print("\n" + "="*70)
    
    def generate_dataset_report(self):
        """Generate comprehensive dataset analysis report"""
        report_file = self.output_base_dir / 'dataset_report.json'
        
        report = {
            'dataset_name': 'Zidane Fetal Pose Dataset',
            'processing_date': datetime.now().isoformat(),
            'total_streams': len(self.progress['completed_streams']),
            'total_frames': self.progress['total_frames_processed'],
            'streams': []
        }
        
        # Aggregate metrics from all streams
        for stream_id in self.progress['completed_streams']:
            stream_dir = self.output_base_dir / stream_id
            results_file = stream_dir / 'pose_analysis.json'
            
            if results_file.exists():
                with open(results_file, 'r') as f:
                    stream_data = json.load(f)
                
                # Extract summary statistics
                stream_summary = {
                    'stream_id': stream_id,
                    'total_frames': stream_data.get('total_frames', 0),
                    'frames_processed': len(stream_data.get('frame_results', [])),
                    'temporal_metrics': stream_data.get('temporal_metrics', {})
                }
                
                report['streams'].append(stream_summary)
        
        # Save report
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Dataset report saved to: {report_file}")
        return report


def main():
    """Main execution function"""
    
    print("="*70)
    print("SAM-BASED POSE ESTIMATION - FULL DATASET PROCESSING")
    print("="*70)
    print("\nThis will process all 39 streams (~15,113 frames)")
    print("Estimated time: 3-5 hours on RTX 3050")
    print("\nYou can stop and resume at any time (progress is saved)")
    print("="*70)
    
    # Initialize processor
    processor = DatasetBatchProcessor(
        mapping_file='dataset_mapping.json',
        output_base_dir='results',
        sam_model_type='vit_b',
        sam_checkpoint='sam_vit_b_01ec64.pth'
    )
    
    # Process all streams
    processor.process_all_streams(
        save_visualizations=True,  # Set to False to save disk space and speed up
        skip_completed=True  # Skip already processed streams
    )
    
    # Generate final report
    processor.generate_dataset_report()
    
    print("\n✅ All done! Check the 'results' folder for outputs.")


if __name__ == "__main__":
    main()
