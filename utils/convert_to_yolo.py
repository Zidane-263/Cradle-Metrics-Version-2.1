#!/usr/bin/env python3
"""
Convert CVAT XML Annotations to YOLO Format
Converts bounding box annotations from box_annotation/ to YOLO format
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
import shutil
from typing import List, Tuple, Dict
import random
import json

class CVATtoYOLO:
    """Convert CVAT XML annotations to YOLO format"""
    
    def __init__(self, box_annotation_dir: str, images_dir: str, output_dir: str):
        """
        Initialize converter
        
        Args:
            box_annotation_dir: Path to box_annotation folder
            images_dir: Path to four_poses folder
            output_dir: Path to output YOLO dataset
        """
        self.box_annotation_dir = Path(box_annotation_dir)
        self.images_dir = Path(images_dir)
        self.output_dir = Path(output_dir)
        
        # Class mapping
        self.class_names = ['head', 'abdomen', 'arm', 'legs']
        self.class_to_id = {name: idx for idx, name in enumerate(self.class_names)}
        
        print(f"Class mapping: {self.class_to_id}")
    
    def parse_xml(self, xml_path: Path) -> List[Dict]:
        """
        Parse CVAT XML file
        
        Returns:
            List of annotations with image info and boxes
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        annotations = []
        
        for image in root.findall('image'):
            img_name = image.get('name')
            img_width = float(image.get('width'))
            img_height = float(image.get('height'))
            
            boxes = []
            for box in image.findall('box'):
                label = box.get('label').lower()
                
                # Skip if label not in our classes
                if label not in self.class_to_id:
                    continue
                
                # Get box coordinates
                xtl = float(box.get('xtl'))
                ytl = float(box.get('ytl'))
                xbr = float(box.get('xbr'))
                ybr = float(box.get('ybr'))
                
                boxes.append({
                    'label': label,
                    'class_id': self.class_to_id[label],
                    'xtl': xtl,
                    'ytl': ytl,
                    'xbr': xbr,
                    'ybr': ybr
                })
            
            if boxes:  # Only add if there are valid boxes
                annotations.append({
                    'image_name': img_name,
                    'width': img_width,
                    'height': img_height,
                    'boxes': boxes
                })
        
        return annotations
    
    def convert_to_yolo_format(self, box: Dict, img_width: float, img_height: float) -> str:
        """
        Convert box to YOLO format: class x_center y_center width height (normalized)
        """
        # Calculate center and dimensions
        x_center = (box['xtl'] + box['xbr']) / 2.0
        y_center = (box['ytl'] + box['ybr']) / 2.0
        width = box['xbr'] - box['xtl']
        height = box['ybr'] - box['ytl']
        
        # Normalize to [0, 1]
        x_center /= img_width
        y_center /= img_height
        width /= img_width
        height /= img_height
        
        # YOLO format: class x_center y_center width height
        return f"{box['class_id']} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
    
    def convert_stream(self, stream_name: str) -> List[Tuple[str, str, str]]:
        """
        Convert one stream's annotations
        
        Returns:
            List of (image_path, label_content, image_name) tuples
        """
        xml_path = self.box_annotation_dir / stream_name / 'annotations.xml'
        images_path = self.images_dir / stream_name
        
        if not xml_path.exists():
            print(f"⚠️  XML not found: {xml_path}")
            return []
        
        if not images_path.exists():
            print(f"⚠️  Images not found: {images_path}")
            return []
        
        # Parse XML
        annotations = self.parse_xml(xml_path)
        
        results = []
        for ann in annotations:
            img_name = ann['image_name']
            img_path = images_path / img_name
            
            if not img_path.exists():
                continue
            
            # Convert boxes to YOLO format
            yolo_lines = []
            for box in ann['boxes']:
                yolo_line = self.convert_to_yolo_format(box, ann['width'], ann['height'])
                yolo_lines.append(yolo_line)
            
            label_content = '\n'.join(yolo_lines)
            results.append((str(img_path), label_content, img_name))
        
        return results
    
    def create_dataset(self, train_split: float = 0.8, val_split: float = 0.1):
        """
        Create YOLO dataset with train/val/test splits
        """
        print("\n" + "="*70)
        print("Converting CVAT XML to YOLO Format")
        print("="*70)
        
        # Get all streams
        streams = [d.name for d in self.box_annotation_dir.iterdir() if d.is_dir()]
        print(f"\nFound {len(streams)} streams")
        
        # Collect all annotations
        all_data = []
        for stream in streams:
            print(f"Processing: {stream}")
            stream_data = self.convert_stream(stream)
            all_data.extend(stream_data)
            print(f"  → {len(stream_data)} images")
        
        print(f"\nTotal images: {len(all_data)}")
        
        # Shuffle
        random.shuffle(all_data)
        
        # Split
        n_total = len(all_data)
        n_train = int(n_total * train_split)
        n_val = int(n_total * val_split)
        
        train_data = all_data[:n_train]
        val_data = all_data[n_train:n_train + n_val]
        test_data = all_data[n_train + n_val:]
        
        print(f"\nSplit:")
        print(f"  Train: {len(train_data)} ({train_split*100:.0f}%)")
        print(f"  Val:   {len(val_data)} ({val_split*100:.0f}%)")
        print(f"  Test:  {len(test_data)} ({(1-train_split-val_split)*100:.0f}%)")
        
        # Create directories
        for split in ['train', 'val', 'test']:
            (self.output_dir / 'images' / split).mkdir(parents=True, exist_ok=True)
            (self.output_dir / 'labels' / split).mkdir(parents=True, exist_ok=True)
        
        # Copy files
        print("\nCopying files...")
        self._copy_split(train_data, 'train')
        self._copy_split(val_data, 'val')
        self._copy_split(test_data, 'test')
        
        # Create dataset.yaml
        self._create_yaml()
        
        print("\n" + "="*70)
        print("✅ Conversion Complete!")
        print("="*70)
        print(f"\nDataset saved to: {self.output_dir}")
        print(f"Configuration: {self.output_dir / 'dataset.yaml'}")
    
    def _copy_split(self, data: List[Tuple], split: str):
        """Copy images and labels for a split"""
        for img_path, label_content, img_name in data:
            # Copy image
            dst_img = self.output_dir / 'images' / split / img_name
            shutil.copy2(img_path, dst_img)
            
            # Save label
            label_name = Path(img_name).stem + '.txt'
            dst_label = self.output_dir / 'labels' / split / label_name
            dst_label.write_text(label_content)
    
    def _create_yaml(self):
        """Create dataset.yaml for YOLO training"""
        yaml_content = f"""# Fetal Ultrasound Dataset
path: {self.output_dir.absolute()}
train: images/train
val: images/val
test: images/test

# Classes
names:
  0: head
  1: abdomen
  2: arm
  3: legs

# Number of classes
nc: 4
"""
        yaml_path = self.output_dir / 'dataset.yaml'
        yaml_path.write_text(yaml_content)
        print(f"\n✅ Created: {yaml_path}")


def main():
    """Main conversion function"""
    
    # Paths
    box_annotation_dir = 'box_annotation'
    images_dir = 'four_poses'
    output_dir = 'yolo_dataset'
    
    # Create converter
    converter = CVATtoYOLO(box_annotation_dir, images_dir, output_dir)
    
    # Convert dataset
    converter.create_dataset(train_split=0.8, val_split=0.1)
    
    print("\n🎯 Next step: Train YOLO model")
    print("   Command: python detection/train_yolo.py")


if __name__ == "__main__":
    main()
