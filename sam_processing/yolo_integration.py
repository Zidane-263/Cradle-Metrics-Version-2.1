"""
Helper method for SAM pipeline to process frame with YOLO boxes
Add this to sam_pipeline.py
"""

def process_frame_with_boxes(self, image: np.ndarray, boxes_dict: Dict[str, List]) -> Dict:
    """
    Process frame with pre-detected bounding boxes from YOLO
    
    Args:
        image: RGB image
        boxes_dict: Dictionary mapping labels to list of boxes [x1, y1, x2, y2]
    
    Returns:
        Processing results with segmentation and metrics
    """
    # Convert boxes to SAM format
    all_boxes = []
    all_labels = []
    
    for label, boxes in boxes_dict.items():
        for box in boxes:
            all_boxes.append(box)
            all_labels.append(label)
    
    # Segment with SAM
    segmentation_results = []
    for box, label in zip(all_boxes, all_labels):
        masks, scores, _ = self.sam_segmentor.segment_with_box(image, box)
        
        if len(masks) > 0:
            # Use best mask
            best_idx = scores.argmax()
            segmentation_results.append((masks[best_idx], scores[best_idx], label))
    
    # Extract keypoints
    keypoints = []
    for mask, score, label in segmentation_results:
        kp = self.keypoint_detector.extract_keypoints(mask, label)
        keypoints.append(kp)
    
    # Compute metrics
    pose_label = self._infer_pose(keypoints)
    metrics = self.metric_computer.extract_frame_metrics(keypoints, pose_label)
    
    return {
        'segmentation_results': segmentation_results,
        'keypoints': keypoints,
        'metrics': metrics
    }
