# SkinSync AI

SkinSync AI is a simple web application that helps a user record their skin-related information, upload face photos, and receive a skin assessment report.

The application asks about the user's skin, lifestyle, allergies, and diet. It then checks the uploaded photos with OpenCV (a computer-vision library), calculates easy-to-read skin scores, and saves the report so the user can view it again later. An optional AI feature can turn the technical report into plain-language skincare guidance.

> **Important:** This project is an educational assessment tool. It does not diagnose a disease and it is not a replacement for advice from a dermatologist or other qualified medical professional.

## What the project does

In normal use, the application works like this:

1. A user creates an account or logs in.
2. The user answers questions about their skin, lifestyle, allergies, and diet.
3. The user uploads at least three face photos.
4. The application checks whether each photo is usable and looks for a face.
5. OpenCV measures visible concerns such as acne, pigmentation, dark spots, dryness, redness, wrinkles, and pores.
6. The application combines the results into an overall skin-health score.
7. The report and uploaded-image references are saved in PostgreSQL.
8. The user can open previous reports from their report history.
9. If OpenRouter is configured, the user can request an AI-written explanation and practical skincare suggestions.

The image scores are produced by the local OpenCV code. The optional AI feature explains an existing report; it does not calculate the image scores.

## Technology used

- **Python and Flask:** run the web server and connect all parts of the application.
- **HTML, CSS, and JavaScript:** create the screens shown in the browser.
- **PostgreSQL:** stores users, intake answers, uploaded-image records, and reports.
- **SQLAlchemy and Flask-Migrate:** let Python work with the database and apply database changes.
- **JWT:** keeps a user logged in when the browser calls protected API routes.
- **OpenCV and NumPy:** inspect face images and calculate the skin metrics.
- **OpenRouter (optional):** sends report data to a selected language model to create a simple written explanation.

## Folder and file guide

```text
SkinSync-AI/
|-- app.py                    # Starts and connects the Flask application
|-- config.py                 # Reads settings such as database and API keys
|-- models.py                 # Describes the information stored in PostgreSQL
|-- requirements.txt          # Python packages needed by the project
|-- analysis/
|   |-- pipeline.py           # Checks photos and calculates skin scores
|   `-- ai_analysis.py        # Creates the optional AI-written explanation
|-- routes/
|   |-- auth.py               # Registration and login API routes
|   `-- profile.py            # Intake, upload, report, and AI API routes
|-- templates/
|   |-- index.html            # Main login, intake, upload, and history page
|   `-- report_detail.html    # Page used to display one saved report
|-- static/
|   |-- css/style.css         # Colours, spacing, and page appearance
|   |-- js/app.js             # Main browser behaviour and form handling
|   |-- js/report-render.js   # Shared code that turns report data into HTML
|   |-- js/report_detail.js   # Loads and controls the report-details page
|   `-- uploads/              # Stores uploaded images while running locally
|-- migrations/               # Database change history used by Flask-Migrate
|-- tests/
|   `-- test_pipeline_scoring.py # Automated checks for scoring behaviour
|-- test_db.py                # Small manual PostgreSQL connection check
|-- pipeline_test.py          # Manual image-pipeline test helper
|-- test_script.py            # Manual API/profile test helper
|-- run_project.bat           # Windows start helper for a folder named `venv`
|-- run_project.sh            # macOS/Linux start helper for a folder named `venv`
`-- reset_pg.ps1              # Machine-specific PostgreSQL repair helper
```

### Main code in plain language

**`app.py`** is the application's starting point. It loads the settings, connects the database, enables login tokens, registers the API routes, and serves the browser pages.

**`config.py`** reads private settings from a `.env` file. It also contains development defaults. Change the secret values before using the application outside local development.

**`models.py`** is the database plan. It defines users, the four intake sections, uploaded images, and saved analysis reports.

**`analysis/pipeline.py`** is the main scoring file. It checks image quality, finds and crops a face, identifies skin areas, measures visible concerns, and builds the final report. The results are estimates based on image-processing rules, so lighting, camera quality, angle, and filters can affect them.

**`analysis/ai_analysis.py`** is optional. It sends scores and intake information to OpenRouter and asks for a non-diagnostic explanation and general suggestions.

**`routes/auth.py`** handles account registration and login. **`routes/profile.py`** saves intake answers, accepts image uploads, runs the scoring pipeline, stores results, and returns report history.

**`templates/` and `static/`** make up the frontend. The templates contain the page structure, the CSS controls how it looks, and the JavaScript sends information to the Flask API and updates the page.

**`migrations/`** contains ordered database changes. Running the migrations creates or updates the required tables without manually writing SQL.

## Before you start

Install these tools first:

1. **Python 3.10 or newer**
2. **PostgreSQL**
3. **Git** (only needed if you are cloning the project)

Check that Python is available:

```powershell
python --version
```

If `python` is not recognised on Windows, try `py` in the commands below.

## Run the project on Windows

Open PowerShell in the project folder and follow these steps.

### 1. Create a PostgreSQL database

Open PostgreSQL's `psql` tool or pgAdmin and create a database named `skinsync`:

```sql
CREATE DATABASE skinsync;
```

The default local connection used by the project is:

```text
postgresql://postgres:postgres@localhost/skinsync
```

If your PostgreSQL username, password, host, port, or database name is different, put the correct connection in the `.env` file in step 4.

### 2. Create a Python virtual environment

A virtual environment keeps this project's packages separate from other Python projects.

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run this once in the same window and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 3. Install the required Python packages

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Create the local settings file

Create a file named `.env` in the project root. Do not commit this file because it contains private values.

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/skinsync
SECRET_KEY=replace-this-with-a-long-random-value
JWT_SECRET_KEY=replace-this-with-another-long-random-value
```

The AI explanation is optional. To enable it, add:

```env
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_MODEL=openai/gpt-5.1
```

Without an OpenRouter key, registration, intake, photo scoring, reports, and history still work. Only the AI explanation button is unavailable.

### 5. Create or update the database tables

```powershell
python -m flask --app app db upgrade
```

### 6. Start the application

```powershell
python -m flask --app app run --debug
```

Open this address in your browser:

```text
http://127.0.0.1:5000
```

Keep the PowerShell window open while using the application. Press `Ctrl+C` to stop the server.

## Run the project on macOS or Linux

After creating the PostgreSQL database, run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m flask --app app db upgrade
python -m flask --app app run --debug
```

Create the same `.env` file described in the Windows instructions before applying the database migrations.

## How to use the application

1. Visit `http://127.0.0.1:5000`.
2. Create an account, then log in.
3. Complete the skin, lifestyle, allergy, and diet sections.
4. Upload at least three clear face photos. Use good, even lighting and avoid beauty filters.
5. Submit the photos and wait for the local analysis to finish.
6. Read the overall score and the individual skin metrics.
7. Open report history to revisit a saved result.
8. If OpenRouter is configured, request the written AI explanation from the report page.

## Run the automated test

With the virtual environment active, run:

```powershell
python -m pytest -q
```

The automated test checks important scoring behaviour. Some files beginning with `test_` in the project root are manual helper scripts and may require a running server, a working database, or extra setup.

## Common problems

### The application cannot connect to PostgreSQL

- Make sure the PostgreSQL service is running.
- Check that the `skinsync` database exists.
- Check the username, password, host, and port in `DATABASE_URL`.
- Run `python test_db.py` to perform a small connection check.

### A database table is missing

Apply all saved database changes again:

```powershell
python -m flask --app app db upgrade
```

### PowerShell cannot activate the virtual environment

Use the temporary execution-policy command shown in step 2, or run the virtual environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m flask --app app run --debug
```

### `ModuleNotFoundError` appears

Make sure the virtual environment is active, then reinstall the packages:

```powershell
python -m pip install -r requirements.txt
```

### A photo is rejected or produces an unexpected score

Use a clear photo with one visible face, even front lighting, little motion blur, and no beauty filter. Different lighting or repeated copies of the same image can produce misleading or repeated results.

### The AI explanation is unavailable

Check that `OPENROUTER_API_KEY` is present in `.env`, restart Flask after changing the file, and confirm that the computer can reach OpenRouter. This feature uses an external paid or rate-limited service depending on the OpenRouter account and model.

## Development notes

- Uploaded files are stored locally in `static/uploads/`; do not commit personal face images.
- The included `run_project.bat` and `run_project.sh` expect a virtual-environment folder named `venv`. The guide above uses `.venv`, so the manual start command is the clearest option unless those scripts are updated.
- `reset_pg.ps1` contains machine-specific PostgreSQL 18 paths and temporarily changes authentication settings. Do not run it as a normal setup step; use pgAdmin or `psql` instead.
- Replace the development secret keys and use secure deployment settings before putting the application on a public server.
