#!/usr/bin/env python3
"""
Automatic Fetal Ultrasound Analysis Pipeline
Integrates YOLOv8 detection + SAM segmentation + Biometric extraction
"""

import sys
from pathlib import Path
import cv2
import numpy as np
from typing import Dict, List
import argparse

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ultralytics import YOLO
from sam_processing.sam_pipeline import SAMPosePipeline


class AutomaticPipeline:
    """Fully automatic fetal ultrasound analysis pipeline"""
    
    def __init__(self, yolo_model_path: str = 'runs/detect/fetal_detection/weights/best.pt',
                 sam_checkpoint: str = 'sam_vit_b_01ec64.pth',
                 pixel_to_mm: float = 2.5,
                 confidence_threshold: float = 0.5,
                 enable_clinical: bool = True,
                 ga_weeks: float = None,
                 standard_id: str = 'INTERGROWTH'):
        """
        Initialize automatic pipeline
        
        Args:
            yolo_model_path: Path to trained YOLO model
            sam_checkpoint: Path to SAM model
            pixel_to_mm: Calibration factor for mm conversion
            confidence_threshold: Minimum confidence for detections
            enable_clinical: Enable INTERGROWTH-21st clinical assessment
            ga_weeks: Known gestational age (optional)
        """
        print("="*70)
        print("Automatic Fetal Ultrasound Analysis Pipeline")
        print("="*70)
        
        # Load YOLO detector
        print(f"\n📦 Loading YOLO detector: {yolo_model_path}")
        self.yolo = YOLO(yolo_model_path)
        self.confidence_threshold = confidence_threshold
        
        # Load SAM pipeline
        print(f"📦 Loading SAM pipeline...")
        self.sam_pipeline = SAMPosePipeline(
            sam_model_type='vit_b',
            sam_checkpoint=sam_checkpoint,
            device='cuda',
            pixel_to_mm=pixel_to_mm
        )
        
        # Clinical assessment
        self.enable_clinical = enable_clinical
        self.ga_weeks = ga_weeks
        if enable_clinical:
            print(f"📦 Loading clinical assessment standard: {standard_id}...")
            from utils.clinical_assessment import ClinicalAssessment
            self.clinical_assessor = ClinicalAssessment(standard_id=standard_id)
        
        # Class names
        self.class_names = ['head', 'abdomen', 'arm', 'legs']
        
        print("\n✅ Pipeline initialized successfully!")
        print(f"   Confidence threshold: {confidence_threshold}")
        print(f"   Calibration: {pixel_to_mm} pixels = 1mm")
        if enable_clinical:
            print(f"   Clinical assessment: Enabled")
            if ga_weeks:
                print(f"   Known GA: {ga_weeks} weeks")
    
    def detect_boxes(self, image: np.ndarray) -> List[Dict]:
        """
        Detect bounding boxes using YOLO
        
        Returns:
            List of detections with boxes, labels, and confidence
        """
        results = self.yolo(image, verbose=False)[0]
        
        detections = []
        for box in results.boxes:
            conf = float(box.conf[0])
            
            if conf < self.confidence_threshold:
                continue
            
            # Get box coordinates (xyxy format)
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            class_id = int(box.cls[0])
            label = self.class_names[class_id]
            
            detections.append({
                'label': label,
                'confidence': conf,
                'box': [int(x1), int(y1), int(x2), int(y2)]
            })
        
        return detections
    
    def process_image(self, image_path: str, output_dir: str = None) -> Dict:
        """
        Process single image: detect + segment + extract biometrics
        
        Args:
            image_path: Path to input image
            output_dir: Optional output directory for results
        
        Returns:
            Complete analysis results
        """
        print(f"\n{'='*70}")
        print(f"Processing: {Path(image_path).name}")
        print(f"{'='*70}")
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Step 1: Detect with YOLO
        print("\n🔍 Step 1: Detecting body parts with YOLO...")
        detections = self.detect_boxes(image_rgb)
        
        if not detections:
            print("⚠️  No detections found!")
            return {'detections': [], 'segmentation': None, 'metrics': None}
        
        print(f"✅ Found {len(detections)} body parts:")
        for det in detections:
            print(f"   - {det['label']}: {det['confidence']:.2f}")
        
        # Step 2: Segment with SAM
        print("\n🎨 Step 2: Segmenting with SAM...")
        
        # Convert detections to SAM format
        boxes_dict = {}
        for det in detections:
            label = det['label']
            box = det['box']
            
            # SAM expects boxes as list of [x1, y1, x2, y2]
            if label not in boxes_dict:
                boxes_dict[label] = []
            boxes_dict[label].append(box)
        
        # Process with SAM
        sam_results = self.sam_pipeline.process_frame_with_boxes(
            image_rgb, boxes_dict
        )
        
        # Step 3: Visualize
        print("\n📊 Step 3: Creating visualization...")
        vis_image = self.sam_pipeline.visualize_results(image_rgb, sam_results)
        
        # Save results
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Save visualization
            vis_path = output_path / f"{Path(image_path).stem}_result.png"
            cv2.imwrite(str(vis_path), cv2.cvtColor(vis_image, cv2.COLOR_RGB2BGR))
            print(f"\n✅ Saved visualization: {vis_path}")
        
        # Display metrics
        self._display_metrics(sam_results['metrics'])
        
        return {
            'detections': detections,
            'segmentation': sam_results,
            'visualization': vis_image
        }
    
    def _display_metrics(self, metrics: Dict):
        """Display extracted biometrics with clinical assessment"""
        print(f"\n{'='*70}")
        print("📏 Biometric Measurements")
        print(f"{'='*70}")
        
        unit = metrics.get('unit', 'px')
        
        if 'pose_label' in metrics and metrics['pose_label']:
            print(f"\nPose: {metrics['pose_label']}")
        
        if 'spatial_metrics' in metrics:
            spatial = metrics['spatial_metrics']
            
            # Extract measurements for clinical assessment
            measurements = {}
            if 'head_circumference' in spatial:
                measurements['HC'] = spatial['head_circumference']
            if 'abdomen_circumference' in spatial:
                measurements['AC'] = spatial['abdomen_circumference']
            if 'biparietal_diameter' in spatial:
                measurements['BPD'] = spatial['biparietal_diameter']
            if 'femur_length' in spatial:
                measurements['FL'] = spatial['femur_length']
            
            # Clinical assessment
            clinical_results = None
            if self.enable_clinical and measurements and unit == 'mm':
                clinical_results = self.clinical_assessor.assess_all_measurements(
                    measurements, self.ga_weeks
                )
            
            print("\nClinical Measurements:")
            if 'head_circumference' in spatial:
                hc = spatial['head_circumference']
                if clinical_results and 'HC' in clinical_results['measurements']:
                    clin = clinical_results['measurements']['HC']
                    print(f"  HC (Head Circumference):      {hc:.1f}{unit} "
                          f"({clin['percentile']:.0f}th %ile, ~{clin['estimated_ga']:.0f}w) "
                          f"{clin['classification']} {clin['flag']}")
                else:
                    print(f"  HC (Head Circumference):      {hc:.1f}{unit}")
            
            if 'abdomen_circumference' in spatial:
                ac = spatial['abdomen_circumference']
                if clinical_results and 'AC' in clinical_results['measurements']:
                    clin = clinical_results['measurements']['AC']
                    print(f"  AC (Abdominal Circumference): {ac:.1f}{unit} "
                          f"({clin['percentile']:.0f}th %ile, ~{clin['estimated_ga']:.0f}w) "
                          f"{clin['classification']} {clin['flag']}")
                else:
                    print(f"  AC (Abdominal Circumference): {ac:.1f}{unit}")
            
            if 'biparietal_diameter' in spatial:
                bpd = spatial['biparietal_diameter']
                if clinical_results and 'BPD' in clinical_results['measurements']:
                    clin = clinical_results['measurements']['BPD']
                    print(f"  BPD (Biparietal Diameter):    {bpd:.1f}{unit} "
                          f"({clin['percentile']:.0f}th %ile, ~{clin['estimated_ga']:.0f}w) "
                          f"{clin['classification']} {clin['flag']}")
                else:
                    print(f"  BPD (Biparietal Diameter):    {bpd:.1f}{unit}")
            
            if 'femur_length' in spatial:
                fl = spatial['femur_length']
                if clinical_results and 'FL' in clinical_results['measurements']:
                    clin = clinical_results['measurements']['FL']
                    print(f"  FL (Femur Length):            {fl:.1f}{unit} "
                          f"({clin['percentile']:.0f}th %ile, ~{clin['estimated_ga']:.0f}w) "
                          f"{clin['classification']} {clin['flag']}")
                else:
                    print(f"  FL (Femur Length):            {fl:.1f}{unit}")
            
            # Clinical assessment summary
            if clinical_results:
                print(f"\n{'='*70}")
                print("📊 Clinical Assessment (INTERGROWTH-21st)")
                print(f"{'='*70}")
                
                # Safely display GA estimate
                consensus_ga = clinical_results.get('consensus_ga')
                ga_uncertainty = clinical_results.get('ga_uncertainty')
                
                if consensus_ga is not None and ga_uncertainty is not None:
                    print(f"\nEstimated GA: {consensus_ga:.1f} weeks "
                          f"± {ga_uncertainty:.1f} weeks")
                    print(f"Consistency: {clinical_results['ga_consistency']}")
                elif consensus_ga is not None:
                    print(f"\nEstimated GA: {consensus_ga:.1f} weeks")
                    print(f"Consistency: {clinical_results['ga_consistency']}")
                
                overall = clinical_results['overall_assessment']
                print(f"\nOverall: {overall['status']}")
                for flag in overall['flags']:
                    print(f"  {flag}")
            
            print(f"\n{'='*70}")
            print("Additional Measurements:")
            if 'head_abdomen_distance' in spatial:
                print(f"  Head-Abdomen Distance: {spatial['head_abdomen_distance']:.1f}{unit}")
            if 'body_length' in spatial:
                print(f"  Body Length:           {spatial['body_length']:.1f}{unit}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Automatic Fetal Ultrasound Analysis')
    parser.add_argument('--image', type=str, required=True, help='Path to input image')
    parser.add_argument('--output', type=str, default='automatic_results', help='Output directory')
    parser.add_argument('--yolo-model', type=str, default='runs/detect/fetal_detection/weights/best.pt',
                       help='Path to trained YOLO model')
    parser.add_argument('--confidence', type=float, default=0.5, help='Detection confidence threshold')
    parser.add_argument('--calibration', type=float, default=2.5, help='Pixel-to-mm calibration')
    
    parser.add_argument('--standard', type=str, default='INTERGROWTH', choices=['INTERGROWTH', 'WHO', 'HADLOCK'],
                        help='Fetal growth standard to use')
    
    args = parser.parse_args()
    
    # Create pipeline
    pipeline = AutomaticPipeline(
        yolo_model_path=args.yolo_model,
        pixel_to_mm=args.calibration,
        confidence_threshold=args.confidence,
        standard_id=args.standard
    )
    
    # Process image
    results = pipeline.process_image(args.image, args.output)
    
    print(f"\n{'='*70}")
    print("✅ Analysis Complete!")
    print(f"{'='*70}")
    print(f"\nResults saved to: {args.output}/")


if __name__ == "__main__":
    main()
