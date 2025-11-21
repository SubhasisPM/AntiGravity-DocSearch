@echo off
echo Installing DocSearch Dependencies...
echo.

pip install -r requirements.txt

echo.
echo Installation complete!
echo.
echo To start the server, run: python app.py
echo Then open http://localhost:5000 in your browser
echo.
pause
