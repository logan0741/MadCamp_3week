import sys
import os
from contextlib import asynccontextmanager

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    print("🚀 Attempting to import backend.main...")
    from backend.main import app
    print("✅ Successfully imported backend.main.app")
    
    print("ℹ️ Checking app configuration...")
    print(f"   Title: {app.title}")
    print(f"   Version: {app.version}")
    
    print("✅ Backend core verification successful!")
    sys.exit(0)
except Exception as e:
    print(f"❌ Failed to load backend: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
