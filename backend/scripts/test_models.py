#!/usr/bin/env python3
"""Test model configurations"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_model_names():
    print("Testing model configurations...")
    print(f"Gemini Model: {os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')}")
    print(f"Embedding Model: {os.getenv('GEMINI_EMBEDDING_MODEL', 'text-embedding-004')}")
    
    # Test imports
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
        
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            print("❌ GOOGLE_API_KEY not set in .env")
            return False
        
        # Test LLM initialization
        print("\nTesting LLM initialization...")
        llm = ChatGoogleGenerativeAI(
            model=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
            google_api_key=api_key,
            temperature=0.1
        )
        print(f"✅ LLM initialized: {llm.model}")
        
        # Test embeddings initialization
        print("\nTesting embeddings initialization...")
        embeddings = GoogleGenerativeAIEmbeddings(
            model=os.getenv('GEMINI_EMBEDDING_MODEL', 'text-embedding-004'),
            google_api_key=api_key
        )
        print(f"✅ Embeddings initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_model_names()
    exit(0 if success else 1)
