#!/usr/bin/env python3
"""
Composio Setup Script for IncidentDNA
======================================
This script authenticates and configures Composio integrations for:
  - GitHub (create issues for incidents)
  - Slack (post alerts to channels)

Prerequisites:
  1. pip install composio python-dotenv
  2. Set COMPOSIO_API_KEY in .env (get from https://app.composio.dev/settings)

Usage:
  python scripts/setup_composio.py           # Interactive setup
  python scripts/setup_composio.py --check   # Check existing connections
  python scripts/setup_composio.py --test    # Test integrations
"""

import os
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

# Fixed user ID for IncidentDNA agent
COMPOSIO_USER_ID = "incidentdna-agent"


def get_client():
    """Initialize Composio client."""
    try:
        from composio import Composio
    except ImportError:
        print("❌ Composio not installed. Run: pip install composio")
        sys.exit(1)
    
    api_key = os.getenv("COMPOSIO_API_KEY")
    if not api_key or api_key == "your_composio_api_key":
        print("❌ COMPOSIO_API_KEY not set in .env")
        print("   Get your key from: https://app.composio.dev/settings")
        sys.exit(1)
    
    return Composio(api_key=api_key)


def check_connections():
    """Check existing Composio connections."""
    print("\n🔍 Checking Composio connections...\n")
    client = get_client()
    
    try:
        # List connected apps for our user
        connections = client.connected_accounts.get(user_id=COMPOSIO_USER_ID)
        
        github_connected = False
        slack_connected = False
        
        for conn in connections:
            app_name = conn.get("appName", "").lower()
            status = conn.get("status", "unknown")
            print(f"  • {app_name}: {status}")
            if "github" in app_name and status == "ACTIVE":
                github_connected = True
            if "slack" in app_name and status == "ACTIVE":
                slack_connected = True
        
        if not connections:
            print("  (no connections found)")
        
        print()
        return github_connected, slack_connected
        
    except Exception as e:
        print(f"  ⚠️  Could not check connections: {e}")
        return False, False


def setup_github():
    """Set up GitHub integration."""
    print("\n🔧 Setting up GitHub integration...")
    client = get_client()
    
    try:
        # Initiate GitHub OAuth connection
        result = client.integrations.initiate_connection(
            integration_id="github",
            user_id=COMPOSIO_USER_ID,
        )
        
        auth_url = result.get("redirectUrl") or result.get("authUrl")
        if auth_url:
            print(f"\n📎 Open this URL to authorize GitHub:\n")
            print(f"   {auth_url}\n")
            print("   After authorizing, return here and press Enter...")
            input()
            print("✅ GitHub authorization initiated")
        else:
            print("✅ GitHub may already be connected")
            
    except Exception as e:
        if "already" in str(e).lower():
            print("✅ GitHub already connected")
        else:
            print(f"❌ GitHub setup failed: {e}")


def setup_slack():
    """Set up Slack integration."""
    print("\n🔧 Setting up Slack integration...")
    client = get_client()
    
    try:
        # Initiate Slack OAuth connection
        result = client.integrations.initiate_connection(
            integration_id="slack",
            user_id=COMPOSIO_USER_ID,
        )
        
        auth_url = result.get("redirectUrl") or result.get("authUrl")
        if auth_url:
            print(f"\n📎 Open this URL to authorize Slack:\n")
            print(f"   {auth_url}\n")
            print("   After authorizing, return here and press Enter...")
            input()
            print("✅ Slack authorization initiated")
        else:
            print("✅ Slack may already be connected")
            
    except Exception as e:
        if "already" in str(e).lower():
            print("✅ Slack already connected")
        else:
            print(f"❌ Slack setup failed: {e}")


def test_github():
    """Test GitHub integration by listing available actions."""
    print("\n🧪 Testing GitHub integration...")
    client = get_client()
    
    try:
        # Test by getting available GitHub actions
        actions = client.actions.get(
            app_name="github",
            user_id=COMPOSIO_USER_ID,
        )
        
        issue_action = None
        for action in actions:
            if "create" in action.get("name", "").lower() and "issue" in action.get("name", "").lower():
                issue_action = action
                break
        
        if issue_action:
            print(f"✅ GitHub connected - found action: {issue_action.get('name')}")
            return True
        else:
            print("⚠️  GitHub connected but GITHUB_CREATE_AN_ISSUE action not found")
            return False
            
    except Exception as e:
        print(f"❌ GitHub test failed: {e}")
        return False


def test_slack():
    """Test Slack integration by listing available actions."""
    print("\n🧪 Testing Slack integration...")
    client = get_client()
    
    try:
        # Test by getting available Slack actions
        actions = client.actions.get(
            app_name="slack",
            user_id=COMPOSIO_USER_ID,
        )
        
        post_action = None
        for action in actions:
            if "post" in action.get("name", "").lower() and "message" in action.get("name", "").lower():
                post_action = action
                break
        
        if post_action:
            print(f"✅ Slack connected - found action: {post_action.get('name')}")
            return True
        else:
            print("⚠️  Slack connected but SLACKBOT_CHAT_POST_MESSAGE action not found")
            return False
            
    except Exception as e:
        print(f"❌ Slack test failed: {e}")
        return False


def test_send_slack_message():
    """Send a test message to Slack."""
    print("\n🧪 Sending test Slack message...")
    client = get_client()
    
    channel = os.getenv("SLACK_CHANNEL", "#incidents")
    
    try:
        result = client.actions.execute(
            action_name="SLACKBOT_CHAT_POST_MESSAGE",
            params={
                "channel": channel,
                "text": "🧪 *IncidentDNA Test Message*\n\nIf you see this, Slack integration is working correctly!",
            },
            user_id=COMPOSIO_USER_ID,
        )
        print(f"✅ Test message sent to {channel}")
        return True
    except Exception as e:
        print(f"❌ Failed to send test message: {e}")
        return False


def interactive_setup():
    """Run interactive setup wizard."""
    print("=" * 60)
    print("  IncidentDNA — Composio Setup Wizard")
    print("=" * 60)
    
    # Check current state
    github_ok, slack_ok = check_connections()
    
    if github_ok and slack_ok:
        print("✅ All integrations already connected!")
        print("\nRun with --test to verify they work correctly.")
        return
    
    # Setup missing integrations
    if not github_ok:
        setup_github()
    
    if not slack_ok:
        setup_slack()
    
    # Verify
    print("\n" + "=" * 60)
    print("  Verification")
    print("=" * 60)
    
    github_ok, slack_ok = check_connections()
    
    if github_ok and slack_ok:
        print("\n✅ Setup complete! All integrations connected.")
    else:
        print("\n⚠️  Some integrations may need manual setup.")
        print("   Visit https://app.composio.dev to manage connections.")


def run_tests():
    """Run integration tests."""
    print("=" * 60)
    print("  IncidentDNA — Composio Integration Tests")
    print("=" * 60)
    
    github_ok = test_github()
    slack_ok = test_slack()
    
    print("\n" + "-" * 60)
    
    if github_ok and slack_ok:
        print("\n✅ All tests passed!")
        
        # Offer to send test message
        response = input("\nSend a test message to Slack? (y/N): ").strip().lower()
        if response == 'y':
            test_send_slack_message()
    else:
        print("\n⚠️  Some tests failed. Run setup first:")
        print("   python scripts/setup_composio.py")


def main():
    parser = argparse.ArgumentParser(description="IncidentDNA Composio Setup")
    parser.add_argument("--check", action="store_true", help="Check existing connections")
    parser.add_argument("--test", action="store_true", help="Test integrations")
    parser.add_argument("--github", action="store_true", help="Setup GitHub only")
    parser.add_argument("--slack", action="store_true", help="Setup Slack only")
    
    args = parser.parse_args()
    
    if args.check:
        check_connections()
    elif args.test:
        run_tests()
    elif args.github:
        setup_github()
    elif args.slack:
        setup_slack()
    else:
        interactive_setup()


if __name__ == "__main__":
    main()
