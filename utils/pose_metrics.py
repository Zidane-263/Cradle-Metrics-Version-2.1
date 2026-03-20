#!/usr/bin/env python3
"""
Metric Extractor for SAM-Based Pose Estimation
Computes clinical and geometric metrics from keypoints
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.spatial.distance import euclidean
from scipy.stats import describe
import json


class PoseMetrics:
    """Compute metrics from detected keypoints with pixel-to-mm calibration"""
    
    def __init__(self, pixel_to_mm: float = None):
        """
        Initialize metrics computer
        
        Args:
            pixel_to_mm: Calibration factor (pixels per mm). 
                        If None, measurements will be in pixels.
                        Typical values: 0.1-0.3 depending on ultrasound settings
        """
        self.metric_history = []
        self.pixel_to_mm = pixel_to_mm
        self.use_mm = pixel_to_mm is not None
    
    def set_calibration(self, pixel_to_mm: float):
        """Set pixel-to-mm calibration factor"""
        self.pixel_to_mm = pixel_to_mm
        self.use_mm = True
    
    def get_unit(self) -> str:
        """Get current measurement unit"""
        return "mm" if self.use_mm else "px"
    
    def convert_to_mm(self, pixels: float) -> float:
        """Convert pixels to mm if calibration is set"""
        if self.use_mm and self.pixel_to_mm:
            return pixels / self.pixel_to_mm
        return pixels
    
    def compute_distance(self, point1: Tuple[int, int], point2: Tuple[int, int]) -> float:
        """Compute Euclidean distance between two points"""
        return euclidean(point1, point2)
    
    def compute_angle(self, p1: Tuple, p2: Tuple, p3: Tuple) -> float:
        """
        Compute angle at p2 formed by p1-p2-p3
        
        Returns:
            Angle in degrees
        """
        v1 = np.array(p1) - np.array(p2)
        v2 = np.array(p3) - np.array(p2)
        
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
        angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
        
        return np.degrees(angle)
    
    def compute_body_axis_angle(self, head_center: Tuple, abdomen_center: Tuple) -> float:
        """
        Compute body axis orientation angle
        
        Returns:
            Angle in degrees from horizontal
        """
        dx = abdomen_center[0] - head_center[0]
        dy = abdomen_center[1] - head_center[1]
        
        angle = np.degrees(np.arctan2(dy, dx))
        return angle
    
    def compute_limb_length(self, keypoints: Dict) -> float:
        """
        Compute limb length from endpoints
        
        Args:
            keypoints: Keypoint dictionary with 'endpoints' and 'centroid'
        
        Returns:
            Maximum distance from centroid to endpoints
        """
        if not keypoints.get('endpoints'):
            return 0.0
        
        centroid = keypoints['centroid']
        max_dist = 0.0
        
        for endpoint in keypoints['endpoints']:
            dist = self.compute_distance(centroid, endpoint)
            max_dist = max(max_dist, dist)
        
        return max_dist
    
    def compute_symmetry_index(self, left_keypoints: Dict, right_keypoints: Dict) -> float:
        """
        Compute left-right symmetry index
        
        Returns:
            Symmetry score (1.0 = perfect symmetry, 0.0 = no symmetry)
        """
        if not left_keypoints or not right_keypoints:
            return 0.0
        
        left_length = self.compute_limb_length(left_keypoints)
        right_length = self.compute_limb_length(right_keypoints)
        
        if left_length == 0 or right_length == 0:
            return 0.0
        
        ratio = min(left_length, right_length) / max(left_length, right_length)
        return ratio
    
    def compute_compactness(self, all_keypoints: List[Dict]) -> float:
        """
        Compute pose compactness (how curled up the fetus is)
        
        Returns:
            Compactness score (higher = more compact/curled)
        """
        all_points = []
        
        for kp in all_keypoints:
            all_points.append(kp['centroid'])
            if 'contour_points' in kp:
                for point in kp['contour_points'].values():
                    all_points.append(point)
        
        if len(all_points) < 2:
            return 0.0
        
        # Compute convex hull area
        points_array = np.array(all_points)
        from scipy.spatial import ConvexHull
        
        try:
            hull = ConvexHull(points_array)
            hull_area = hull.volume  # In 2D, volume is area
        except:
            return 0.0
        
        # Compute total bounding box area
        x_min, y_min = points_array.min(axis=0)
        x_max, y_max = points_array.max(axis=0)
        bbox_area = (x_max - x_min) * (y_max - y_min)
        
        if bbox_area == 0:
            return 0.0
        
    # Compactness = hull_area / bbox_area
        compactness = hull_area / bbox_area
        
        return compactness

    def compute_aspect_ratio(self, contour_points: Dict) -> float:
        """Compute aspect ratio (width / height)"""
        if not all(k in contour_points for k in ['left', 'right', 'top', 'bottom']):
            return 0.0
        
        width = self.compute_distance(contour_points['left'], contour_points['right'])
        height = self.compute_distance(contour_points['top'], contour_points['bottom'])
        
        if height == 0: return 0.0
        return width / height

    def compute_bpd_ofd(self, contour_points: Dict) -> Tuple[float, float]:
        """
        Compute BPD and OFD correctly by identifying major/minor axes.
        Anatomical rule: OFD (longitudinal) is always >= BPD (transverse).
        """
        if not all(k in contour_points for k in ['left', 'right', 'top', 'bottom']):
            return 0.0, 0.0
            
        d1 = self.compute_distance(contour_points['left'], contour_points['right'])
        d2 = self.compute_distance(contour_points['top'], contour_points['bottom'])
        
        # Fix for rotated heads: BPD is the minor axis, OFD is the major axis
        bpd = min(d1, d2)
        ofd = max(d1, d2)
        
        return bpd, ofd

    def compute_cephalic_index(self, bpd: float, ofd: float) -> float:
        """Compute Cephalic Index (CI) = (BPD / OFD) * 100"""
        if ofd == 0:
            return 0.0
        return (bpd / ofd) * 100
    
    def compute_circumference(self, contour_points: Dict) -> float:
        """
        Compute circumference from contour points
        Approximates using ellipse formula
        """
        if 'left' not in contour_points or 'right' not in contour_points:
            return 0.0
        if 'top' not in contour_points or 'bottom' not in contour_points:
            return 0.0
        
        # Get width and height
        width = self.compute_distance(contour_points['left'], contour_points['right'])
        height = self.compute_distance(contour_points['top'], contour_points['bottom'])
        
        # Approximate circumference using Ramanujan's formula for ellipse
        a = width / 2
        b = height / 2
        circumference = np.pi * (3 * (a + b) - np.sqrt((3 * a + b) * (a + 3 * b)))
        
        return circumference
    
    def extract_frame_metrics(self, keypoints_list: List[Dict], 
                             pose_label: str = None) -> Dict:
        """
        Extract all metrics for a single frame including clinical biometrics
        
        Args:
            keypoints_list: List of keypoint dictionaries for all body parts
            pose_label: Pose orientation label (hdvb, hdvf, etc.)
        
        Returns:
            Dictionary of computed metrics with HC, AC, BPD, FL
        """
        metrics = {
            'pose_label': pose_label,
            'spatial_metrics': {},
            'size_metrics': {},
            'geometric_metrics': {},
            'body_parts': {}
        }
        
        # Organize keypoints by label
        kp_dict = {kp['label']: kp for kp in keypoints_list}
        
        # CLINICAL BIOMETRICS (with mm conversion)
        
        # HC - Head Circumference
        if 'head' in kp_dict and 'contour_points' in kp_dict['head']:
            hc = self.compute_circumference(kp_dict['head']['contour_points'])
            if hc > 0:
                hc_converted = self.convert_to_mm(hc)
                metrics['spatial_metrics']['head_circumference'] = hc_converted
                metrics['spatial_metrics']['HC'] = hc_converted  # Alias
            
            # Aspect Ratio for Head (BPD/OFD approximation)
            metrics['spatial_metrics']['head_aspect_ratio'] = self.compute_aspect_ratio(kp_dict['head']['contour_points'])
        
        # BPD and OFD extraction
        if 'head' in kp_dict and 'contour_points' in kp_dict['head']:
            bpd, ofd = self.compute_bpd_ofd(kp_dict['head']['contour_points'])
            if ofd > 0:
                bpd_mm = self.convert_to_mm(bpd)
                ofd_mm = self.convert_to_mm(ofd)
                
                metrics['spatial_metrics']['biparietal_diameter'] = bpd_mm
                metrics['spatial_metrics']['BPD'] = bpd_mm
                metrics['spatial_metrics']['occipitofrontal_diameter'] = ofd_mm
                metrics['spatial_metrics']['OFD'] = ofd_mm
                
                # Cephalic Index (CI)
                ci = self.compute_cephalic_index(bpd_mm, ofd_mm)
                metrics['spatial_metrics']['cephalic_index'] = ci
                metrics['spatial_metrics']['CI'] = ci
        
        # AC - Abdominal Circumference
        if 'abdomen' in kp_dict and 'contour_points' in kp_dict['abdomen']:
            ac = self.compute_circumference(kp_dict['abdomen']['contour_points'])
            if ac > 0:
                ac_converted = self.convert_to_mm(ac)
                metrics['spatial_metrics']['abdomen_circumference'] = ac_converted
                metrics['spatial_metrics']['AC'] = ac_converted  # Alias
                
            # Aspect Ratio for Abdomen (Circularity check)
            metrics['spatial_metrics']['abdomen_aspect_ratio'] = self.compute_aspect_ratio(kp_dict['abdomen']['contour_points'])
        
        # FL - Femur Length (from legs)
        if 'legs' in kp_dict:
            fl = self.compute_limb_length(kp_dict['legs'])
            if fl > 0:
                fl_converted = self.convert_to_mm(fl)
                metrics['spatial_metrics']['femur_length'] = fl_converted
                metrics['spatial_metrics']['FL'] = fl_converted  # Alias
        
        # Limb lengths (arms)
        limb_lengths = {}
        for label in ['arm', 'arms']:
            if label in kp_dict:
                length = self.compute_limb_length(kp_dict[label])
                if length > 0:
                    limb_lengths[label] = self.convert_to_mm(length)
        
        if limb_lengths:
            metrics['spatial_metrics']['limb_lengths'] = limb_lengths
        
        # Add unit information
        metrics['unit'] = self.get_unit()
        
        # Spatial metrics
        if 'head' in kp_dict and 'abdomen' in kp_dict:
            head_center = kp_dict['head']['centroid']
            abdomen_center = kp_dict['abdomen']['centroid']
            
            metrics['spatial_metrics']['head_abdomen_distance'] = \
                self.compute_distance(head_center, abdomen_center)
            
            metrics['geometric_metrics']['body_axis_angle'] = \
                self.compute_body_axis_angle(head_center, abdomen_center)
        
        # Body length (head to legs)
        if 'head' in kp_dict and 'legs' in kp_dict:
            head_center = kp_dict['head']['centroid']
            legs_center = kp_dict['legs']['centroid']
            body_length = self.compute_distance(head_center, legs_center)
            metrics['spatial_metrics']['body_length'] = body_length
        
        # Size and limb metrics for each body part
        for label, kp in kp_dict.items():
            part_metrics = {
                'centroid': kp['centroid'],
                'num_endpoints': len(kp.get('endpoints', [])),
                'num_branch_points': len(kp.get('branch_points', [])),
                'limb_length': self.compute_limb_length(kp)
            }
            
            # Contour-based measurements
            if 'contour_points' in kp:
                cp = kp['contour_points']
                if 'left' in cp and 'right' in cp:
                    part_metrics['width'] = self.compute_distance(cp['left'], cp['right'])
                if 'top' in cp and 'bottom' in cp:
                    part_metrics['height'] = self.compute_distance(cp['top'], cp['bottom'])
            
            metrics['body_parts'][label] = part_metrics
        
        # Geometric metrics
        metrics['geometric_metrics']['compactness'] = \
            self.compute_compactness(keypoints_list)
        
        # Flexion angle (if head, abdomen, and legs are present)
        if all(part in kp_dict for part in ['head', 'abdomen', 'legs']):
            head_c = kp_dict['head']['centroid']
            abd_c = kp_dict['abdomen']['centroid']
            leg_c = kp_dict['legs']['centroid']
            
            metrics['geometric_metrics']['flexion_angle'] = \
                self.compute_angle(head_c, abd_c, leg_c)
        
        return metrics

    
    def compute_temporal_metrics(self, metrics_timeline: List[Dict]) -> Dict:
        """
        Compute temporal metrics from a sequence of frame metrics
        
        Args:
            metrics_timeline: List of frame metrics over time
        
        Returns:
            Temporal analysis metrics
        """
        if len(metrics_timeline) < 2:
            return {}
        
        temporal_metrics = {
            'total_frames': len(metrics_timeline),
            'movement_analysis': {},
            'stability_analysis': {}
        }
        
        # Track centroid movements
        head_positions = []
        abdomen_positions = []
        
        for frame_metrics in metrics_timeline:
            if 'head' in frame_metrics.get('body_parts', {}):
                head_positions.append(frame_metrics['body_parts']['head']['centroid'])
            if 'abdomen' in frame_metrics.get('body_parts', {}):
                abdomen_positions.append(frame_metrics['body_parts']['abdomen']['centroid'])
        
        # Compute velocities
        if len(head_positions) > 1:
            head_velocities = []
            for i in range(1, len(head_positions)):
                dist = self.compute_distance(head_positions[i-1], head_positions[i])
                head_velocities.append(dist)
            
            temporal_metrics['movement_analysis']['head_avg_velocity'] = np.mean(head_velocities)
            temporal_metrics['movement_analysis']['head_max_velocity'] = np.max(head_velocities)
            temporal_metrics['stability_analysis']['head_position_std'] = np.std(head_positions, axis=0).tolist()
        
        # Activity classification
        if 'head_avg_velocity' in temporal_metrics['movement_analysis']:
            avg_vel = temporal_metrics['movement_analysis']['head_avg_velocity']
            if avg_vel < 1.0:
                activity_level = 'resting'
            elif avg_vel < 5.0:
                activity_level = 'low_activity'
            elif avg_vel < 10.0:
                activity_level = 'moderate_activity'
            else:
                activity_level = 'high_activity'
            
            temporal_metrics['activity_level'] = activity_level
        
        return temporal_metrics
    
    def save_metrics(self, metrics: Dict, output_path: str):
        """Save metrics to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(metrics, f, indent=2)
    
    def load_metrics(self, input_path: str) -> Dict:
        """Load metrics from JSON file"""
        with open(input_path, 'r') as f:
            return json.load(f)


def example_metric_computation():
    """Example of computing metrics from keypoints"""
    
    # Example keypoints from SAM pipeline
    keypoints_list = [
        {
            'label': 'head',
            'centroid': (350, 150),
            'endpoints': [(320, 120), (380, 120)],
            'branch_points': [],
            'contour_points': {
                'top': (350, 120),
                'bottom': (350, 180),
                'left': (320, 150),
                'right': (380, 150)
            }
        },
        {
            'label': 'abdomen',
            'centroid': (390, 180),
            'endpoints': [(360, 150), (420, 210)],
            'branch_points': [(390, 180)],
            'contour_points': {
                'top': (390, 150),
                'bottom': (390, 210),
                'left': (360, 180),
                'right': (420, 180)
            }
        }
    ]
    
    # Compute metrics
    metric_computer = PoseMetrics()
    frame_metrics = metric_computer.extract_frame_metrics(
        keypoints_list, 
        pose_label='hdvb'
    )
    
    print("Frame Metrics:")
    print(json.dumps(frame_metrics, indent=2))
    
    return frame_metrics


if __name__ == "__main__":
    print("Pose Metrics Computation Module")
    print("=" * 50)
    example_metric_computation()
