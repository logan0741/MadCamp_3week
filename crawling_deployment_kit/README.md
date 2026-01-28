# Crawling Deployment Kit

This folder contains the crawling and backend logic for the project.
It is designed to be usable immediately by another AI agent.

## Folder Structure

- `cpu_crawler/`: Contains the Selenium/Playwright/HTTPX based crawler and FastAPI backend.
- `prompts/`: Contains all prompt engineerng files and context documents.
- `gpu_crawler_missing/`: (Note) The YOLO/GPU crawler code was not found in the source directory and the backup zip was corrupted. 

## instructions

1. **Setup**: Run `./setup_and_run.sh` to initialize the environment and test the CPU crawler.
2. **Database**: The system uses `sqlite:///./musinsa_tracker.db` by default (located in `cpu_crawler/`).
3. **Running**:
   - Go to `cpu_crawler/`
   - Activate venv: `source venv/bin/activate`
   - Run server: `uvicorn main:app --reload`

## Missing Components
The "GPU/YOLO" crawling component (likely `ai-pipeline` folder) was missing.
If you have a backup of `ai-pipeline/`, place it in `gpu_crawler/` folder.
The `AI_PROMPT.md` in `prompts/` describes how it *should* work.
