@echo off
echo.
echo  ================================
echo   KAVACH - Setup and Run
echo  ================================
echo.

echo [1/3] Installing Python dependencies...
cd backend
pip install fastapi uvicorn python-multipart opencv-python numpy Pillow scipy aiofiles
cd ..

echo.
echo [2/3] Building React frontend...
cd kavach-ui
call npm install
call npm run build
cd ..

echo.
echo [3/3] Starting KAVACH server...
echo.
echo  Open http://localhost:8000 in your browser
echo.
cd backend
py -m uvicorn main:app --reload --port 8000
