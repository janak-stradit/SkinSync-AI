@echo off
echo Starting SkinSync AI Project...

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Set Flask environment variables
set FLASK_APP=app.py
set FLASK_ENV=development

:: Run the Flask application
echo Running Flask...
flask run
