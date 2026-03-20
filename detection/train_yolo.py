#!/usr/bin/env python3
"""
Train YOLOv8 for Fetal Body Part Detection
Medical-grade automatic detection system
"""

from ultralytics import YOLO
from pathlib import Path
import torch

def train_yolo():
    """Train YOLOv8 model on fetal ultrasound dataset"""
    
    print("="*70)
    print("YOLOv8 Training - Fetal Body Part Detection")
    print("="*70)
    
    # Check CUDA
    print(f"\nPyTorch: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    
    # Model selection
    # yolov8n.pt - Nano (fastest, ~6M params)
    # yolov8s.pt - Small (better accuracy, ~11M params)
    # yolov8m.pt - Medium (best for medical, ~25M params)
    
    model_size = 's'  # Change to 'n' for faster training, 'm' for better accuracy
    
    print(f"\nModel: YOLOv8{model_size}")
    print("Loading pre-trained weights...")
    
    # Load pre-trained model
    model = YOLO(f'yolov8{model_size}.pt')
    
    # Training parameters
    print("\nTraining Configuration:")
    config = {
        'data': 'yolo_dataset/dataset.yaml',
        'epochs': 100,
        'imgsz': 640,
        'batch': 16,  # Adjust based on GPU memory (RTX 3050 4GB)
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        'patience': 20,  # Early stopping
        'save': True,
        'save_period': 10,  # Save checkpoint every 10 epochs
        'project': 'runs/detect',
        'name': 'fetal_detection',
        'exist_ok': True,
        'pretrained': True,
        'optimizer': 'AdamW',
        'lr0': 0.001,
        'lrf': 0.01,
        'momentum': 0.937,
        'weight_decay': 0.0005,
        'warmup_epochs': 3,
        'warmup_momentum': 0.8,
        'warmup_bias_lr': 0.1,
        'box': 7.5,
        'cls': 0.5,
        'dfl': 1.5,
        'pose': 12.0,
        'kobj': 1.0,
        'label_smoothing': 0.0,
        'nbs': 64,
        'hsv_h': 0.015,
        'hsv_s': 0.7,
        'hsv_v': 0.4,
        'degrees': 0.0,
        'translate': 0.1,
        'scale': 0.5,
        'shear': 0.0,
        'perspective': 0.0,
        'flipud': 0.0,
        'fliplr': 0.5,
        'mosaic': 1.0,
        'mixup': 0.0,
        'copy_paste': 0.0,
        'plots': True,
        'verbose': True
    }
    
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    print("\n" + "="*70)
    print("Starting Training...")
    print("="*70)
    print("\nThis will take 2-3 hours on RTX 3050")
    print("Training progress will be saved to: runs/detect/fetal_detection")
    print("\nPress Ctrl+C to stop training\n")
    
    # Train model
    results = model.train(**config)
    
    print("\n" + "="*70)
    print("✅ Training Complete!")
    print("="*70)
    
    # Validate
    print("\nValidating model...")
    metrics = model.val()
    
    print(f"\nValidation Results:")
    print(f"  mAP50: {metrics.box.map50:.3f}")
    print(f"  mAP50-95: {metrics.box.map:.3f}")
    print(f"  Precision: {metrics.box.mp:.3f}")
    print(f"  Recall: {metrics.box.mr:.3f}")
    
    # Save best model
    best_model_path = Path('runs/detect/fetal_detection/weights/best.pt')
    if best_model_path.exists():
        print(f"\n✅ Best model saved: {best_model_path}")
        print(f"\n🎯 Next step: Test automatic detection")
        print(f"   Command: python automatic_pipeline.py --image test.png")
    
    return results, metrics


if __name__ == "__main__":
    try:
        results, metrics = train_yolo()
    except KeyboardInterrupt:
        print("\n\n⚠️  Training interrupted by user")
        print("Partial model saved in runs/detect/fetal_detection/weights/")
    except Exception as e:
        print(f"\n❌ Error during training: {e}")
        raise
