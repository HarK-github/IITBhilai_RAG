#!/usr/bin/env python3
"""Test all module imports"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    tests = [
        ("src.caching", ["CacheManager", "ExactMatchCache", "SemanticCache"]),
        ("src.tools", ["BaseTool", "WebsiteTool", "ToolResult", "ToolRegistry"]),
    ]
    
    for module_name, classes in tests:
        try:
            module = __import__(module_name, fromlist=classes)
            for cls in classes:
                assert hasattr(module, cls), f"Missing {cls} in {module_name}"
            print(f"✅ {module_name}")
        except Exception as e:
            print(f"❌ {module_name}: {e}")
            return False
    
    print("\n🎉 All imports successful!")
    return True

if __name__ == "__main__":
    test_imports()
