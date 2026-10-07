@echo off
setlocal
cd /d %~dp0backend

echo Preparing Support Studio...
if not exist venv (
  echo Creating virtual environment...
  python -m venv venv
)

echo Installing dependencies...
call venv\Scripts\activate
python -m pip install --upgrade pip >nul
pip install -r requirements.txt

echo Starting Streamlit AI app...
start "AI Chatbot" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate && streamlit run streamlit_app.py"
timeout /t 3 /nobreak >nul
start http://localhost:8501
