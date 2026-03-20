#!/usr/bin/env python3
"""
Biometric Extraction from Segmentation Masks
Extract clinical measurements: HC, AC, FL from predicted masks
"""

import cv2
import numpy as np
from scipy import ndimage
from skimage.morphology import skeletonize
from typing import Dict, Tuple


class BiometricExtractor:
    """Extract clinical biometric measurements from segmentation masks"""
    
    def __init__(self, calibration_factor: float = 0.2):
        """
        Initialize biometric extractor
        
        Args:
            calibration_factor: Pixel to millimeter conversion (mm/pixel)
        """
        self.calibration_factor = calibration_factor
        
    def extract_all_metrics(self, mask: np.ndarray, class_id_map: dict = None) -> Dict:
        """
        Extract all biometric measurements from multi-class mask
        
        Args:
            mask: Multi-class segmentation mask (H, W)
            class_id_map: Mapping of class names to IDs
        
        Returns:
            Dictionary of measurements
        """
        if class_id_map is None:
            class_id_map = {
                'background': 0,
                'head': 1,
                'abdomen': 2,
                'arm': 3,
                'legs': 4
            }
        
        measurements = {}
        
        # Extract head circumference
        if 'head' in class_id_map:
            head_mask = (mask == class_id_map['head']).astype(np.uint8)
            if head_mask.sum() > 0:
                hc = self.compute_head_circumference(head_mask)
                measurements['head_circumference_px'] = hc
                measurements['head_circumference_mm'] = hc * self.calibration_factor
                
                # Additional head metrics
                measurements['head_area_px'] = head_mask.sum()
                measurements['head_area_mm2'] = head_mask.sum() * (self.calibration_factor ** 2)
        
        # Extract abdominal circumference
        if 'abdomen' in class_id_map:
            abd_mask = (mask == class_id_map['abdomen']).astype(np.uint8)
            if abd_mask.sum() > 0:
                ac = self.compute_abdominal_circumference(abd_mask)
                measurements['abdominal_circumference_px'] = ac
                measurements['abdominal_circumference_mm'] = ac * self.calibration_factor
                
                # Additional abdomen metrics
                measurements['abdomen_area_px'] = abd_mask.sum()
                measurements['abdomen_area_mm2'] = abd_mask.sum() * (self.calibration_factor ** 2)
        
        # Extract femur length
        if 'legs' in class_id_map:
            legs_mask = (mask == class_id_map['legs']).astype(np.uint8)
            if legs_mask.sum() > 0:
                fl = self.compute_femur_length(legs_mask)
                measurements['femur_length_px'] = fl
                measurements['femur_length_mm'] = fl * self.calibration_factor
        
        # Extract limb measurements
        if 'arm' in class_id_map:
            arm_mask = (mask == class_id_map['arm']).astype(np.uint8)
            if arm_mask.sum() > 0:
                arm_length = self.compute_limb_length(arm_mask)
                measurements['arm_length_px'] = arm_length
                measurements['arm_length_mm'] = arm_length * self.calibration_factor
        
        return measurements
    
    def compute_head_circumference(self, head_mask: np.ndarray) -> float:
        """
        Compute head circumference from mask
        
        Method: Fit ellipse to head contour and calculate circumference
        
        Args:
            head_mask: Binary mask of head region
        
        Returns:
            Head circumference in pixels
        """
        # Find contours
        contours, _ = cv2.findContours(
            head_mask, 
            cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        if not contours:
            return 0.0
        
        # Get largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        
        if len(largest_contour) < 5:
            # Not enough points for ellipse fitting
            # Use contour perimeter as fallback
            return cv2.arcLength(largest_contour, True)
        
        # Fit ellipse
        try:
            ellipse = cv2.fitEllipse(largest_contour)
            (center, axes, angle) = ellipse
            a, b = axes[0] / 2, axes[1] / 2  # Semi-major and semi-minor axes
            
            # Ramanujan's approximation for ellipse circumference
            h = ((a - b) ** 2) / ((a + b) ** 2)
            circumference = np.pi * (a + b) * (1 + (3 * h) / (10 + np.sqrt(4 - 3 * h)))
            
            return circumference
        except:
            # Fallback to contour perimeter
            return cv2.arcLength(largest_contour, True)
    
    def compute_abdominal_circumference(self, abdomen_mask: np.ndarray) -> float:
        """
        Compute abdominal circumference from mask
        
        Args:
            abdomen_mask: Binary mask of abdomen region
        
        Returns:
            Abdominal circumference in pixels
        """
        # Similar to head circumference
        return self.compute_head_circumference(abdomen_mask)
    
    def compute_femur_length(self, legs_mask: np.ndarray) -> float:
        """
        Compute femur length from legs mask
        
        Method: Extract skeleton and find longest path
        
        Args:
            legs_mask: Binary mask of legs region
        
        Returns:
            Femur length in pixels
        """
        if legs_mask.sum() == 0:
            return 0.0
        
        # Extract skeleton
        skeleton = skeletonize(legs_mask > 0)
        
        # Find endpoints
        endpoints = self._find_endpoints(skeleton)
        
        if len(endpoints) < 2:
            # Fallback: use bounding box diagonal
            y_coords, x_coords = np.where(legs_mask > 0)
            if len(y_coords) == 0:
                return 0.0
            height = y_coords.max() - y_coords.min()
            width = x_coords.max() - x_coords.min()
            return np.sqrt(height**2 + width**2)
        
        # Find maximum distance between endpoints
        max_length = 0
        for i, ep1 in enumerate(endpoints):
            for ep2 in endpoints[i+1:]:
                length = np.sqrt((ep1[0] - ep2[0])**2 + (ep1[1] - ep2[1])**2)
                max_length = max(max_length, length)
        
        return max_length
    
    def compute_limb_length(self, limb_mask: np.ndarray) -> float:
        """
        Compute limb length from mask
        
        Args:
            limb_mask: Binary mask of limb region
        
        Returns:
            Limb length in pixels
        """
        # Similar to femur length
        return self.compute_femur_length(limb_mask)
    
    def _find_endpoints(self, skeleton: np.ndarray) -> list:
        """
        Find endpoints in skeleton
        
        Args:
            skeleton: Binary skeleton image
        
        Returns:
            List of endpoint coordinates
        """
        # Endpoint has exactly 1 neighbor
        kernel = np.array([[1, 1, 1],
                          [1, 0, 1],
                          [1, 1, 1]], dtype=np.uint8)
        
        neighbor_count = ndimage.convolve(skeleton.astype(np.uint8), kernel, mode='constant')
        endpoints = np.argwhere((neighbor_count == 1) & (skeleton > 0))
        
        return endpoints.tolist()
    
    def compute_biparietal_diameter(self, head_mask: np.ndarray) -> float:
        """
        Compute biparietal diameter (BPD) - widest part of head
        
        Args:
            head_mask: Binary mask of head region
        
        Returns:
            BPD in pixels
        """
        if head_mask.sum() == 0:
            return 0.0
        
        # Find contour
        contours, _ = cv2.findContours(
            head_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        if not contours:
            return 0.0
        
        largest_contour = max(contours, key=cv2.contourArea)
        
        if len(largest_contour) < 5:
            return 0.0
        
        # Fit ellipse
        try:
            ellipse = cv2.fitEllipse(largest_contour)
            (center, axes, angle) = ellipse
            # BPD is the major axis
            bpd = max(axes)
            return bpd
        except:
            # Fallback: use bounding box width
            x, y, w, h = cv2.boundingRect(largest_contour)
            return max(w, h)
    
    def generate_clinical_report(self, measurements: Dict) -> str:
        """
        Generate clinical report from measurements
        
        Args:
            measurements: Dictionary of measurements
        
        Returns:
            Formatted clinical report
        """
        report = """
FETAL BIOMETRIC MEASUREMENTS
============================

Head Measurements:
  - Head Circumference (HC): {hc:.1f} mm
  - Head Area: {ha:.1f} mm²

Abdominal Measurements:
  - Abdominal Circumference (AC): {ac:.1f} mm
  - Abdominal Area: {aa:.1f} mm²

Limb Measurements:
  - Femur Length (FL): {fl:.1f} mm
  - Arm Length: {al:.1f} mm

Clinical Ratios:
  - HC/AC Ratio: {hc_ac:.3f}
  - FL/AC Ratio: {fl_ac:.3f}

Notes:
  - All measurements in millimeters (mm)
  - Calibration factor: {cal:.2f} mm/pixel
  - Measurements should be validated by clinical expert
""".format(
            hc=measurements.get('head_circumference_mm', 0),
            ha=measurements.get('head_area_mm2', 0),
            ac=measurements.get('abdominal_circumference_mm', 0),
            aa=measurements.get('abdomen_area_mm2', 0),
            fl=measurements.get('femur_length_mm', 0),
            al=measurements.get('arm_length_mm', 0),
            hc_ac=measurements.get('head_circumference_mm', 0) / max(measurements.get('abdominal_circumference_mm', 1), 1),
            fl_ac=measurements.get('femur_length_mm', 0) / max(measurements.get('abdominal_circumference_mm', 1), 1),
            cal=self.calibration_factor
        )
        
        return report


def main():
    """Example usage"""
    
    # Example: Load a predicted mask
    # mask = cv2.imread('predicted_mask.png', cv2.IMREAD_GRAYSCALE)
    
    # Create synthetic example
    mask = np.zeros((389, 672), dtype=np.uint8)
    # Simulate head (class 1)
    cv2.circle(mask, (300, 150), 50, 1, -1)
    # Simulate abdomen (class 2)
    cv2.ellipse(mask, (300, 250), (60, 40), 0, 0, 360, 2, -1)
    
    # Extract biometrics
    extractor = BiometricExtractor(calibration_factor=0.2)
    measurements = extractor.extract_all_metrics(mask)
    
    print("Extracted Measurements:")
    for key, value in measurements.items():
        print(f"  {key}: {value:.2f}")
    
    # Generate report
    report = extractor.generate_clinical_report(measurements)
    print(report)


if __name__ == "__main__":
    main()
