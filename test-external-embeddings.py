#!/usr/bin/env python3
"""
Test script for external embedding service
Run this to verify the solution works before deploying to Railway
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_external_embeddings():
    """Test the external embedding service"""
    print("🧪 Testing External Embedding Service...")
    
    try:
        # Import the service
        from backend.external_embeddings import embedding_service
        
        # Test texts
        test_texts = [
            "Hello, this is a test message.",
            "Another test message for embeddings.",
            "Testing the external embedding service."
        ]
        
        print(f"📝 Testing with {len(test_texts)} texts...")
        
        # Get embeddings
        embeddings = embedding_service.get_embeddings(test_texts)
        
        if embeddings:
            print(f"✅ Successfully generated {len(embeddings)} embeddings")
            print(f"📊 Embedding dimensions: {len(embeddings[0])}")
            
            # Show provider info
            provider_info = embedding_service.get_provider_info()
            print(f"🔌 Provider: {provider_info['provider']}")
            print(f"📡 Available: {provider_info['available']}")
            
            return True
        else:
            print("❌ No embeddings generated")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're running from the project root")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_build_size():
    """Test that build requirements are minimal"""
    print("\n📦 Testing Build Requirements Size...")
    
    try:
        # Check build requirements file
        build_req_file = "railway-build-requirements.txt"
        if os.path.exists(build_req_file):
            with open(build_req_file, 'r') as f:
                content = f.read()
                lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
                
            print(f"✅ Build requirements: {len(lines)} packages")
            print("📋 Packages:")
            for pkg in lines:
                print(f"   • {pkg}")
            
            # Check for heavy dependencies
            heavy_deps = ['torch', 'transformers', 'sentence-transformers', 'accelerate']
            found_heavy = [dep for dep in heavy_deps if any(dep in pkg for pkg in lines)]
            
            if found_heavy:
                print(f"⚠️  Warning: Found heavy dependencies: {found_heavy}")
                return False
            else:
                print("✅ No heavy dependencies found in build requirements")
                return True
        else:
            print(f"❌ Build requirements file not found: {build_req_file}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking build requirements: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Synapse External Embeddings Test")
    print("=" * 50)
    
    # Test 1: External embedding service
    test1_passed = test_external_embeddings()
    
    # Test 2: Build requirements size
    test2_passed = test_build_size()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"   • External Embeddings: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"   • Build Size Check: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Ready for Railway deployment.")
        print("💡 Your build image will stay well under 4GB.")
        return True
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
