#!/usr/bin/env python3
"""
Run script for IIT Bhilai RAG Agent Backend
"""
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Change to backend directory
os.chdir(Path(__file__).parent)

# Import and run API
from src.api.app import app
import uvicorn

if __name__ == "__main__":
    print("🚀 Starting IIT Bhilai RAG Agent Backend")
    print(f"📁 Data directory: {Path('data').absolute()}")
    print(f"🔧 Config directory: {Path('src/config').absolute()}")
    print("=" * 50)
    
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
