@echo off
REM Fix OpenMP conflict and start training
REM This sets an environment variable to allow multiple OpenMP runtimes

echo Setting OpenMP environment variable...
set KMP_DUPLICATE_LIB_OK=TRUE

echo Starting YOLOv8 training...
python detection\train_yolo.py

pause
