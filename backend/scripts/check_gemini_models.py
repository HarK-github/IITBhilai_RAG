#!/usr/bin/env python3
"""Check available Gemini models"""

import os
from dotenv import load_dotenv
load_dotenv()

try:
    import google.generativeai as genai
    
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("❌ GOOGLE_API_KEY not set")
        exit(1)
    
    genai.configure(api_key=api_key)
    
    print("Available models for embeddings:\n")
    for model in genai.list_models():
        print(f"  ✓ {model.name}")
    
    print("\nRecommended embedding model:")
    print("  models/embedding-001 (works with v1beta)")
    
except Exception as e:
    print(f"Error: {e}")
