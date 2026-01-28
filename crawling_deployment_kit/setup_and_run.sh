#!/bin/bash
set -e

# Setup/Run Script for Crawling Deployment Kit

echo "🚀 Setting up Crawling Kit Environment..."

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed."
    exit 1
fi

# 2. Setup Virtual Environment for CPU Crawler
echo "📦 Setting up CPU Crawler (Backend)..."
cd cpu_crawler
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Created venv."
fi

source venv/bin/activate
pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    echo "⚠️ No requirements.txt found in cpu_crawler!"
fi

# Install playwright browsers
if pip show playwright &> /dev/null; then
    playwright install chromium
    sudo playwright install-deps || echo "⚠️ Could not run sudo playwright install-deps. Please run manually if needed."
fi

# 3. Verify Logic
echo "✅ verifying scraping logic..."
python3 test_scraper.py

echo "🎉 Setup Complete. Python environment is in cpu_crawler/venv."
echo "To run the server: cd cpu_crawler && source venv/bin/activate && uvicorn main:app --reload"
