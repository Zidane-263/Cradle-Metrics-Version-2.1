#!/usr/bin/env python3
"""
Complete SAM-Based Pose Estimation Pipeline
Integrates SAM segmentation, skeleton extraction, keypoint detection, and metric computation
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import cv2
import numpy as np
import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple
from tqdm import tqdm

from sam_processing.sam_pose_estimator import SAMSegmentor, SkeletonExtractor, KeypointDetector
from utils.pose_metrics import PoseMetrics


class SAMPosePipeline:
    """Complete pipeline for SAM-based pose estimation and metric extraction"""
    
    def __init__(self, sam_model_type: str = 'vit_h', sam_checkpoint: str = None, 
                 device: str = 'cuda', pixel_to_mm: float = None):
        """
        Initialize the complete pipeline
        
        Args:
            sam_model_type: SAM model type
            sam_checkpoint: Path to SAM checkpoint
            device: 'cuda' or 'cpu'
            pixel_to_mm: Calibration factor (pixels per mm). 
                        Example: 2.5 means 2.5 pixels = 1mm
                        If None, measurements will be in pixels
        """
        print("Initializing SAM Pose Estimation Pipeline...")
        
        self.sam_segmentor = SAMSegmentor(sam_model_type, sam_checkpoint, device)
        self.skeleton_extractor = SkeletonExtractor()
        self.keypoint_detector = KeypointDetector()
        self.metric_computer = PoseMetrics(pixel_to_mm=pixel_to_mm)
        
        print("Pipeline initialized successfully!")
        if pixel_to_mm:
            print(f"Calibration: {pixel_to_mm} pixels = 1mm (measurements in mm)")
        else:
            print("No calibration set (measurements in pixels)")
    
    def parse_annotation_xml(self, xml_path: str) -> List[Dict]:
        """
        Parse CVAT XML annotation file
        
        Args:
            xml_path: Path to annotations.xml
        
        Returns:
            List of frame annotations
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        annotations = []
        for image in root.findall('image'):
            frame_data = {
                'id': int(image.get('id')),
                'name': image.get('name'),
                'width': int(image.get('width')),
                'height': int(image.get('height')),
                'boxes': [],
                'pose': None,
                'view': None
            }
            
            # Extract bounding boxes
            for box in image.findall('box'):
                frame_data['boxes'].append({
                    'label': box.get('label'),
                    'xtl': float(box.get('xtl')),
                    'ytl': float(box.get('ytl')),
                    'xbr': float(box.get('xbr')),
                    'ybr': float(box.get('ybr'))
                })
            
            # Extract pose label
            for tag in image.findall('tag'):
                if tag.get('label') == 'Orientation':
                    attr = tag.find('attribute[@name="Pose"]')
                    if attr is not None:
                        frame_data['pose'] = attr.text
                elif tag.get('label') == 'location':
                    attr = tag.find('attribute[@name="View_fetus"]')
                    if attr is not None:
                        frame_data['view'] = attr.text
            
            annotations.append(frame_data)
        
        return annotations
    
    def process_frame(self, image: np.ndarray, boxes: List[Dict], 
                     pose_label: str = None) -> Dict:
        """
        Process a single frame through the complete pipeline
        
        Args:
            image: RGB image
            boxes: List of bounding boxes
            pose_label: Pose orientation label
        
        Returns:
            Complete results including keypoints and metrics
        """
        # Set image for SAM
        self.sam_segmentor.set_image(image)
        
        # Generate segmentation masks
        seg_results = self.sam_segmentor.segment_multiple_boxes(boxes)
        
        # Extract keypoints from each body part
        all_keypoints = []
        for mask, score, label in seg_results:
            # Extract skeleton
            skeleton = self.skeleton_extractor.extract_skeleton(mask)
            
            # Detect keypoints
            keypoints = self.keypoint_detector.extract_body_part_keypoints(
                mask, skeleton, label
            )
            keypoints['sam_score'] = float(score)
            all_keypoints.append(keypoints)
        
        # Compute metrics
        metrics = self.metric_computer.extract_frame_metrics(all_keypoints, pose_label)
        
        return {
            'keypoints': all_keypoints,
            'metrics': metrics,
            'segmentation_results': [(mask, score, label) for mask, score, label in seg_results]
        }
    
    def process_frame_with_boxes(self, image: np.ndarray, boxes_dict: Dict[str, List]) -> Dict:
        """
        Process frame with pre-detected bounding boxes from YOLO
        
        Args:
            image: RGB image
            boxes_dict: Dictionary mapping labels to list of boxes [x1, y1, x2, y2]
        
        Returns:
            Processing results with segmentation and metrics
        """
        # Set image for SAM
        self.sam_segmentor.set_image(image)

        # Convert boxes to SAM format and segment
        segmentation_results = []
        
        for label, boxes in boxes_dict.items():
            for box in boxes:
                # Convert YOLO box format [x1, y1, x2, y2] to SAM dict format
                if isinstance(box, list):
                    box_dict = {
                        'xtl': box[0],
                        'ytl': box[1],
                        'xbr': box[2],
                        'ybr': box[3]
                    }
                else:
                    box_dict = box
                
                # Segment with SAM
                mask, score = self.sam_segmentor.segment_from_box(box_dict)
                
                # Add to results
                segmentation_results.append((mask, score, label))
        
        # Extract keypoints
        all_keypoints = []
        for mask, score, label in segmentation_results:
            # Extract skeleton
            skeleton = self.skeleton_extractor.extract_skeleton(mask)
            
            # Detect keypoints
            keypoints = self.keypoint_detector.extract_body_part_keypoints(
                mask, skeleton, label
            )
            keypoints['sam_score'] = float(score)
            all_keypoints.append(keypoints)
        
        # Compute metrics
        # The _infer_pose method is not provided in the original class,
        # so we'll pass None for pose_label for now, or assume it's handled externally.
        # For faithful reproduction, I'll assume _infer_pose is a placeholder.
        # If _infer_pose is meant to be a method of this class, it needs to be defined.
        # For now, I'll comment it out and pass None or a default.
        # pose_label = self._infer_pose(all_keypoints) 
        pose_label = None # Placeholder as _infer_pose is not defined in the provided context
        metrics = self.metric_computer.extract_frame_metrics(all_keypoints, pose_label)
        
        return {
            'segmentation_results': segmentation_results,
            'keypoints': all_keypoints,
            'metrics': metrics
        }
    
    def process_stream(self, frames_dir: str, annotation_file: str, 
                      output_dir: str = None, save_visualizations: bool = False) -> Dict:
        """
        Process an entire video stream
        
        Args:
            frames_dir: Directory containing frame images
            annotation_file: Path to annotations.xml
            output_dir: Directory to save results
            save_visualizations: Whether to save visualization images
        
        Returns:
            Complete stream analysis
        """
        print(f"\nProcessing stream: {Path(frames_dir).name}")
        
        # Parse annotations
        annotations = self.parse_annotation_xml(annotation_file)
        
        # Create output directory
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            if save_visualizations:
                (output_path / 'visualizations').mkdir(exist_ok=True)
        
        # Process each frame
        stream_results = {
            'stream_name': Path(frames_dir).name,
            'total_frames': len(annotations),
            'frame_results': [],
            'metrics_timeline': []
        }
        
        for frame_data in tqdm(annotations, desc="Processing frames"):
            # Load frame image
            frame_path = Path(frames_dir) / frame_data['name']
            if not frame_path.exists():
                continue
            
            image = cv2.imread(str(frame_path))
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Process frame
            if frame_data['boxes']:
                result = self.process_frame(
                    image_rgb,
                    frame_data['boxes'],
                    frame_data['pose']
                )
                
                result['frame_id'] = frame_data['id']
                result['frame_name'] = frame_data['name']
                stream_results['frame_results'].append(result)
                stream_results['metrics_timeline'].append(result['metrics'])
                
                # Save visualization if requested
                if save_visualizations and output_dir:
                    vis_image = self.visualize_results(image_rgb, result)
                    vis_path = output_path / 'visualizations' / f"{frame_data['name']}"
                    cv2.imwrite(str(vis_path), cv2.cvtColor(vis_image, cv2.COLOR_RGB2BGR))
        
        # Compute temporal metrics
        if stream_results['metrics_timeline']:
            stream_results['temporal_metrics'] = \
                self.metric_computer.compute_temporal_metrics(stream_results['metrics_timeline'])
        
        # Save results
        if output_dir:
            results_path = output_path / 'pose_analysis.json'
            
            # Create a clean copy for JSON serialization (avoid circular references)
            clean_results = {
                'stream_name': stream_results['stream_name'],
                'total_frames': stream_results['total_frames'],
                'metrics_timeline': stream_results['metrics_timeline'],
                'temporal_metrics': stream_results.get('temporal_metrics', {})
            }
            
            # Convert numpy types to native Python types
            def convert_to_serializable(obj):
                """Convert numpy types to native Python types"""
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, (np.int32, np.int64)):
                    return int(obj)
                elif isinstance(obj, (np.float32, np.float64)):
                    return float(obj)
                elif isinstance(obj, dict):
                    return {k: convert_to_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_to_serializable(item) for item in obj]
                elif isinstance(obj, tuple):
                    return tuple(convert_to_serializable(item) for item in obj)
                else:
                    return obj
            
            clean_results = convert_to_serializable(clean_results)
            
            with open(results_path, 'w') as f:
                json.dump(clean_results, f, indent=2)
            
            print(f"Results saved to {results_path}")
        
        return stream_results
    
    def visualize_results(self, image: np.ndarray, results: Dict) -> np.ndarray:
        """
        Visualize clean segmentation results with metrics and detected parts legend
        
        Args:
            image: RGB image
            results: Processing results
        
        Returns:
            Annotated image with clean segmentation masks and legend
        """
        vis_image = image.copy()
        
        # Draw clean segmentation masks (no keypoints, no labels on image)
        for mask, score, label in results['segmentation_results']:
            # Create colored overlay
            color = self._get_color_for_label(label)
            overlay = np.zeros_like(vis_image)
            overlay[mask > 0] = color
            vis_image = cv2.addWeighted(vis_image, 0.6, overlay, 0.4, 0)
        
        # Get metrics
        metrics = results['metrics']
        unit = metrics.get('unit', 'px')  # Get unit (mm or px)
        
        # LEFT SIDE: Biometric Measurements
        left_x = 10
        left_y = 30
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 2
        line_height = 25
        
        # Title
        cv2.putText(vis_image, "MEASUREMENTS", (left_x, left_y), 
                   font, 0.6, (255, 255, 255), thickness)
        left_y += line_height
        
        # Pose first
        if 'pose_label' in metrics and metrics['pose_label']:
            cv2.putText(vis_image, f"Pose: {metrics['pose_label']}", 
                       (left_x, left_y), font, font_scale, (255, 255, 255), thickness)
            left_y += line_height
        
        # Then all biometric measurements
        if 'spatial_metrics' in metrics:
            spatial = metrics['spatial_metrics']
            
            # HC (Head Circumference) - if head detected
            if 'head_circumference' in spatial:
                hc = spatial['head_circumference']
                cv2.putText(vis_image, f"HC: {hc:.1f}{unit}", 
                           (left_x, left_y), font, font_scale, (55, 196, 93), thickness)
                left_y += line_height
            
            # AC (Abdominal Circumference) - if abdomen detected
            if 'abdomen_circumference' in spatial:
                ac = spatial['abdomen_circumference']
                cv2.putText(vis_image, f"AC: {ac:.1f}{unit}", 
                           (left_x, left_y), font, font_scale, (158, 37, 148), thickness)
                left_y += line_height
            
            # BPD (Biparietal Diameter) - head width
            if 'biparietal_diameter' in spatial:
                bpd = spatial['biparietal_diameter']
                cv2.putText(vis_image, f"BPD: {bpd:.1f}{unit}", 
                           (left_x, left_y), font, font_scale, (55, 196, 93), thickness)
                left_y += line_height
            
            # FL (Femur Length) - leg length
            if 'femur_length' in spatial:
                fl = spatial['femur_length']
                cv2.putText(vis_image, f"FL: {fl:.1f}{unit}", 
                           (left_x, left_y), font, font_scale, (23, 141, 250), thickness)
                left_y += line_height
            
            # Limb lengths (arms)
            if 'limb_lengths' in spatial and isinstance(spatial['limb_lengths'], dict):
                for limb, length in spatial['limb_lengths'].items():
                    if isinstance(length, (int, float)):
                        cv2.putText(vis_image, f"{limb.capitalize()}: {length:.1f}{unit}", 
                                   (left_x, left_y), font, font_scale, (151, 226, 234), thickness)
                        left_y += line_height
            
            # Head-Abdomen Distance
            if 'head_abdomen_distance' in spatial:
                dist = spatial['head_abdomen_distance']
                cv2.putText(vis_image, f"H-A Dist: {dist:.1f}{unit}", 
                           (left_x, left_y), font, font_scale, (255, 255, 255), thickness)
                left_y += line_height
            
            # Body Length
            if 'body_length' in spatial:
                length = spatial['body_length']
                cv2.putText(vis_image, f"Body Len: {length:.1f}{unit}", 
                           (left_x, left_y), font, font_scale, (255, 255, 255), thickness)
                left_y += line_height

        
        # RIGHT SIDE: Detected Parts Legend
        right_x = vis_image.shape[1] - 180
        right_y = 30
        
        # Title
        cv2.putText(vis_image, "DETECTED PARTS", (right_x, right_y), 
                   font, 0.6, (255, 255, 255), thickness)
        right_y += line_height
        
        # List detected parts with color indicators
        detected_parts = set()
        for kp in results['keypoints']:
            detected_parts.add(kp['label'])
        
        # Sort for consistent display
        part_order = ['head', 'abdomen', 'arm', 'legs']
        for part in part_order:
            if part in detected_parts:
                color = self._get_color_for_label(part)
                
                # Draw color box
                box_size = 15
                cv2.rectangle(vis_image, 
                            (right_x, right_y - box_size + 5), 
                            (right_x + box_size, right_y + 5),
                            color, -1)
                cv2.rectangle(vis_image, 
                            (right_x, right_y - box_size + 5), 
                            (right_x + box_size, right_y + 5),
                            (255, 255, 255), 1)
                
                # Draw part name
                cv2.putText(vis_image, part.capitalize(), 
                           (right_x + box_size + 8, right_y), 
                           font, font_scale, (255, 255, 255), thickness)
                right_y += line_height
        
        return vis_image
    
    def _get_color_for_label(self, label: str) -> Tuple[int, int, int]:
        """Get color for body part label"""
        colors = {
            'head': (55, 196, 93),      # Green
            'arm': (151, 226, 234),     # Cyan
            'abdomen': (158, 37, 148),  # Purple
            'legs': (23, 141, 250)      # Blue
        }
        return colors.get(label, (255, 255, 255))


def main():
    """Example usage of the complete pipeline"""
    
    # Initialize pipeline
    pipeline = SAMPosePipeline(
        sam_model_type='vit_h',
        device='cuda'
    )
    
    # Process a single stream
    results = pipeline.process_stream(
        frames_dir='c:/Projects/Zidane/four_poses/stream_hdvb_aroundabd_h',
        annotation_file='c:/Projects/Zidane/box_annotation/stream_hdvb_aroundabd_h/annotations.xml',
        output_dir='c:/Projects/Zidane/results/stream_hdvb_aroundabd_h',
        save_visualizations=True
    )
    
    print("\n" + "="*60)
    print("Processing Complete!")
    print("="*60)
    print(f"Total frames processed: {results['total_frames']}")
    print(f"Frames with results: {len(results['frame_results'])}")
    
    if 'temporal_metrics' in results:
        print("\nTemporal Analysis:")
        print(json.dumps(results['temporal_metrics'], indent=2))


if __name__ == "__main__":
    main()
