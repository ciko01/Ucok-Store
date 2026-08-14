@echo off
echo ============================================
echo Netflix Cookie Checker WebApp V4.5
echo ============================================
echo.
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo ============================================
echo Starting web server...
echo.
echo Open your browser and go to:
echo http://localhost:8000
echo.
echo Press CTRL+C to stop the server
echo ============================================
echo.
python app.py
pause
