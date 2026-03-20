#!/usr/bin/env python3
"""
SAM-Based Pose Estimator
Generates segmentation masks from bounding boxes using Segment Anything Model
"""

import numpy as np
import torch
import cv2
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from segment_anything import sam_model_registry, SamPredictor


class SAMSegmentor:
    """Segment Anything Model wrapper for generating masks from bounding boxes"""
    
    def __init__(self, model_type: str = "vit_h", checkpoint_path: str = None, device: str = "cuda"):
        """
        Initialize SAM model
        
        Args:
            model_type: SAM model type ('vit_h', 'vit_l', or 'vit_b')
            checkpoint_path: Path to SAM checkpoint file
            device: 'cuda' or 'cpu'
        """
        self.device = device if torch.cuda.is_available() else "cpu"
        
        if checkpoint_path is None:
            checkpoint_path = self._get_default_checkpoint(model_type)
        
        print(f"Loading SAM model ({model_type}) on {self.device}...")
        sam = sam_model_registry[model_type](checkpoint=checkpoint_path)
        sam.to(device=self.device)
        
        self.predictor = SamPredictor(sam)
        self.model_type = model_type
        print("SAM model loaded successfully!")
    
    def _get_default_checkpoint(self, model_type: str) -> str:
        """Get default checkpoint path"""
        checkpoints = {
            'vit_h': 'sam_vit_h_4b8939.pth',
            'vit_l': 'sam_vit_l_0b3195.pth',
            'vit_b': 'sam_vit_b_01ec64.pth'
        }
        return checkpoints.get(model_type, 'sam_vit_h_4b8939.pth')
    
    def set_image(self, image: np.ndarray):
        """
        Set image for segmentation
        
        Args:
            image: RGB image as numpy array (H, W, 3)
        """
        self.predictor.set_image(image)
    
    def segment_from_box(self, box: Dict[str, float]) -> Tuple[np.ndarray, float]:
        """
        Generate segmentation mask from bounding box
        
        Args:
            box: Dictionary with keys 'xtl', 'ytl', 'xbr', 'ybr'
        
        Returns:
            mask: Binary mask (H, W)
            score: Confidence score
        """
        # Validate box dimensions
        w = box['xbr'] - box['xtl']
        h = box['ybr'] - box['ytl']
        if w <= 0 or h <= 0:
            print(f"⚠️  Skipping invalid zero-sized box for {box.get('label', 'unknown')}: {box}")
            return np.zeros(self.predictor.original_size, dtype=np.uint8), 0.0

        # Convert box to SAM format [x1, y1, x2, y2]
        input_box = np.array([
            max(0, box['xtl']),
            max(0, box['ytl']),
            min(self.predictor.original_size[1], box['xbr']),
            min(self.predictor.original_size[0], box['ybr'])
        ])
        
        try:
            # Generate mask
            masks, scores, logits = self.predictor.predict(
                point_coords=None,
                point_labels=None,
                box=input_box[None, :],
                multimask_output=False
            )
            return masks[0], scores[0]
        except Exception as e:
            print(f"❌ SAM prediction failed: {e}")
            return np.zeros(self.predictor.original_size, dtype=np.uint8), 0.0
    
    def segment_multiple_boxes(self, boxes: List[Dict]) -> List[Tuple[np.ndarray, float, str]]:
        """
        Generate segmentation masks for multiple bounding boxes
        
        Args:
            boxes: List of box dictionaries with 'xtl', 'ytl', 'xbr', 'ybr', 'label'
        
        Returns:
            List of (mask, score, label) tuples
        """
        results = []
        for box in boxes:
            mask, score = self.segment_from_box(box)
            label = box.get('label', 'unknown')
            results.append((mask, score, label))
        
        return results
    
    def batch_process_frames(self, frames: List[np.ndarray], 
                            boxes_per_frame: List[List[Dict]]) -> List[List[Tuple]]:
        """
        Process multiple frames in batch
        
        Args:
            frames: List of RGB images
            boxes_per_frame: List of box lists for each frame
        
        Returns:
            List of results per frame
        """
        all_results = []
        
        for frame, boxes in zip(frames, boxes_per_frame):
            self.set_image(frame)
            results = self.segment_multiple_boxes(boxes)
            all_results.append(results)
        
        return all_results


class SkeletonExtractor:
    """Extract skeletons from segmentation masks"""
    
    def __init__(self):
        pass
    
    def extract_skeleton(self, mask: np.ndarray) -> np.ndarray:
        """
        Extract skeleton from binary mask using morphological thinning
        
        Args:
            mask: Binary mask (H, W)
        
        Returns:
            skeleton: Skeletonized binary image
        """
        from skimage.morphology import skeletonize, medial_axis
        
        # Ensure binary mask
        binary_mask = mask.astype(bool)
        
        # Extract skeleton using medial axis transform
        skeleton = skeletonize(binary_mask)
        
        return skeleton.astype(np.uint8) * 255
    
    def extract_medial_axis(self, mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract medial axis with distance transform
        
        Args:
            mask: Binary mask
        
        Returns:
            skeleton: Medial axis
            distance: Distance transform
        """
        from skimage.morphology import medial_axis
        
        binary_mask = mask.astype(bool)
        skeleton, distance = medial_axis(binary_mask, return_distance=True)
        
        return skeleton.astype(np.uint8) * 255, distance
    
    def clean_skeleton(self, skeleton: np.ndarray, min_branch_length: int = 10) -> np.ndarray:
        """
        Clean skeleton by removing small branches
        
        Args:
            skeleton: Binary skeleton image
            min_branch_length: Minimum branch length to keep
        
        Returns:
            cleaned_skeleton: Cleaned skeleton
        """
        from skimage.morphology import remove_small_objects
        
        # Remove small connected components
        cleaned = remove_small_objects(skeleton.astype(bool), min_size=min_branch_length)
        
        return cleaned.astype(np.uint8) * 255


class KeypointDetector:
    """Detect anatomical keypoints from skeletons and masks"""
    
    def __init__(self):
        pass
    
    def detect_endpoints(self, skeleton: np.ndarray) -> List[Tuple[int, int]]:
        """
        Detect skeleton endpoints (extremities)
        
        Args:
            skeleton: Binary skeleton image
        
        Returns:
            List of (x, y) endpoint coordinates
        """
        # Find pixels with exactly one neighbor (endpoints)
        kernel = np.array([[1, 1, 1],
                          [1, 0, 1],
                          [1, 1, 1]], dtype=np.uint8)
        
        # Convolve to count neighbors
        skeleton_binary = (skeleton > 0).astype(np.uint8)
        neighbor_count = cv2.filter2D(skeleton_binary, -1, kernel)
        
        # Endpoints have exactly 1 neighbor
        endpoints = np.where((neighbor_count == 1) & (skeleton_binary == 1))
        
        return list(zip(endpoints[1], endpoints[0]))  # (x, y) format
    
    def detect_branch_points(self, skeleton: np.ndarray) -> List[Tuple[int, int]]:
        """
        Detect skeleton branch points (joints)
        
        Args:
            skeleton: Binary skeleton image
        
        Returns:
            List of (x, y) branch point coordinates
        """
        kernel = np.array([[1, 1, 1],
                          [1, 0, 1],
                          [1, 1, 1]], dtype=np.uint8)
        
        skeleton_binary = (skeleton > 0).astype(np.uint8)
        neighbor_count = cv2.filter2D(skeleton_binary, -1, kernel)
        
        # Branch points have 3 or more neighbors
        branch_points = np.where((neighbor_count >= 3) & (skeleton_binary == 1))
        
        return list(zip(branch_points[1], branch_points[0]))
    
    def compute_centroid(self, mask: np.ndarray) -> Tuple[int, int]:
        """
        Compute centroid of mask
        
        Args:
            mask: Binary mask
        
        Returns:
            (x, y) centroid coordinates
        """
        moments = cv2.moments(mask.astype(np.uint8))
        
        if moments['m00'] == 0:
            return (0, 0)
        
        cx = int(moments['m10'] / moments['m00'])
        cy = int(moments['m01'] / moments['m00'])
        
        return (cx, cy)
    
    def extract_contour_keypoints(self, mask: np.ndarray) -> Dict[str, Tuple[int, int]]:
        """
        Extract keypoints from mask contour
        
        Args:
            mask: Binary mask
        
        Returns:
            Dictionary of keypoint names to (x, y) coordinates
        """
        contours, _ = cv2.findContours(mask.astype(np.uint8), 
                                       cv2.RETR_EXTERNAL, 
                                       cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return {}
        
        # Get largest contour
        contour = max(contours, key=cv2.contourArea)
        
        # Find extreme points
        leftmost = tuple(contour[contour[:, :, 0].argmin()][0])
        rightmost = tuple(contour[contour[:, :, 0].argmax()][0])
        topmost = tuple(contour[contour[:, :, 1].argmin()][0])
        bottommost = tuple(contour[contour[:, :, 1].argmax()][0])
        
        # Centroid
        centroid = self.compute_centroid(mask)
        
        return {
            'left': leftmost,
            'right': rightmost,
            'top': topmost,
            'bottom': bottommost,
            'center': centroid
        }
    
    def extract_body_part_keypoints(self, mask: np.ndarray, skeleton: np.ndarray, 
                                   label: str) -> Dict[str, any]:
        """
        Extract comprehensive keypoints for a body part
        
        Args:
            mask: Segmentation mask
            skeleton: Skeleton of the mask
            label: Body part label ('head', 'arm', 'abdomen', 'legs')
        
        Returns:
            Dictionary of keypoints and features
        """
        keypoints = {
            'label': label,
            'contour_points': self.extract_contour_keypoints(mask),
            'endpoints': self.detect_endpoints(skeleton),
            'branch_points': self.detect_branch_points(skeleton),
            'centroid': self.compute_centroid(mask)
        }
        
        return keypoints


def example_usage():
    """Example usage of SAM-based pose estimation"""
    
    # Initialize components
    sam_segmentor = SAMSegmentor(model_type='vit_h', device='cuda')
    skeleton_extractor = SkeletonExtractor()
    keypoint_detector = KeypointDetector()
    
    # Load image
    image = cv2.imread('path/to/frame.png')
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Set image for SAM
    sam_segmentor.set_image(image_rgb)
    
    # Example bounding boxes
    boxes = [
        {'xtl': 280, 'ytl': 117, 'xbr': 499, 'ybr': 240, 'label': 'abdomen'},
        {'xtl': 270, 'ytl': 143, 'xbr': 315, 'ybr': 272, 'label': 'arm'}
    ]
    
    # Generate masks
    results = sam_segmentor.segment_multiple_boxes(boxes)
    
    # Process each body part
    all_keypoints = []
    for mask, score, label in results:
        # Extract skeleton
        skeleton = skeleton_extractor.extract_skeleton(mask)
        
        # Detect keypoints
        keypoints = keypoint_detector.extract_body_part_keypoints(mask, skeleton, label)
        all_keypoints.append(keypoints)
        
        print(f"{label}: {len(keypoints['endpoints'])} endpoints, "
              f"{len(keypoints['branch_points'])} branch points")
    
    return all_keypoints


if __name__ == "__main__":
    print("SAM-Based Pose Estimation Module")
    print("=" * 50)
    print("\nThis module provides:")
    print("1. SAMSegmentor - Generate masks from bounding boxes")
    print("2. SkeletonExtractor - Extract skeletons from masks")
    print("3. KeypointDetector - Detect anatomical keypoints")
    print("\nSee example_usage() for implementation details")
