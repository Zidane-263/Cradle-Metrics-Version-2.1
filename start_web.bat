@echo off
REM Start the Fetal Ultrasound Analysis Web Interface

echo ======================================================================
echo Starting Fetal Ultrasound Analysis Web Interface
echo ======================================================================
echo.
echo Starting Flask server...
echo.
echo Once started, open your browser and go to:
echo.
echo     http://localhost:5000
echo.
echo Press CTRL+C to stop the server
echo.
echo ======================================================================
echo.

cd web_app
python app.py

pause
