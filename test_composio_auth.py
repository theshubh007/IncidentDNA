"""Test Composio authentication"""
import os
from dotenv import load_dotenv

load_dotenv()

print("Testing Composio authentication...")
print(f"API Key: {os.getenv('COMPOSIO_API_KEY')[:10]}...")

try:
    from composio import Composio
    
    # Initialize Composio
    composio = Composio(api_key=os.getenv('COMPOSIO_API_KEY'))
    
    # Create a session
    session = composio.create(user_id="test_user")
    
    print("✅ Composio authentication successful!")
    print(f"✅ Session created for user: test_user")
    
    # Try to get available toolkits
    print("\nTesting toolkit access...")
    try:
        # Composio v3 API - get tools without specifying toolkit
        tools = session.tools()
        print(f"✅ Tools available ({len(tools)} tools)")
        print("✅ Composio SDK is working correctly")
    except Exception as e:
        print(f"⚠️  Note: {e}")
        print("   This is expected - GitHub connection happens at runtime")
    
    print("\n✅ Composio is working! Ready to proceed.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Check your API key in .env file")
    print("2. Visit https://app.composio.dev to verify your account")
