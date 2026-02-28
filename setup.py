#!/usr/bin/env python3
"""
IncidentDNA Setup Script
Automates the complete setup process
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color

def print_step(step_num, total, message):
    print(f"\n{Colors.YELLOW}[STEP {step_num}/{total}]{Colors.NC} {message}")

def print_success(message):
    print(f"{Colors.GREEN}✓{Colors.NC} {message}")

def print_error(message):
    print(f"{Colors.RED}✗{Colors.NC} {message}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠{Colors.NC}  {message}")

def run_command(cmd, check=True):
    """Run a shell command"""
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False

def main():
    print("=" * 60)
    print("IncidentDNA Setup Script")
    print("=" * 60)
    
    # Step 1: Install dependencies
    print_step(1, 7, "Installing Python dependencies...")
    if not Path("requirements.txt").exists():
        print_error("requirements.txt not found!")
        sys.exit(1)
    
    if run_command(f"{sys.executable} -m pip install -r requirements.txt"):
        print_success("Dependencies installed")
    else:
        print_error("Failed to install dependencies")
        sys.exit(1)
    
    # Step 2: Setup .env file
    print_step(2, 7, "Setting up environment file...")
    if not Path(".env").exists():
        if Path(".env.example").exists():
            shutil.copy(".env.example", ".env")
            print_success("Created .env file from .env.example")
            print_warning("Please edit .env and add your COMPOSIO_API_KEY")
            print("\nRequired variables:")
            print("  - COMPOSIO_API_KEY (get from https://app.composio.dev)")
            print("  - SNOWFLAKE_* (already configured)")
            print()
            input("Press Enter after you've updated .env file...")
        else:
            print_error(".env.example not found!")
            sys.exit(1)
    else:
        print_success(".env file already exists")
    
    # Step 3: Composio authentication
    print_step(3, 7, "Authenticating with Composio...")
    print("This will open a browser window for authentication...")
    if run_command("composio login"):
        print_success("Composio authentication successful")
    else:
        print_error("Composio authentication failed")
        print("Please run: composio login")
        sys.exit(1)
    
    # Step 4: Connect GitHub
    print_step(4, 7, "Connecting GitHub...")
    print("This will open a browser window for GitHub OAuth...")
    if run_command("composio add github"):
        print_success("GitHub connected")
    else:
        print_error("GitHub connection failed")
        print("Please run: composio add github")
        sys.exit(1)
    
    # Step 5: Connect Slack
    print_step(5, 7, "Connecting Slack...")
    print("This will open a browser window for Slack OAuth...")
    if run_command("composio add slack", check=False):
        print_success("Slack connected")
    else:
        print_warning("Slack connection failed (optional, continuing...)")
    
    # Step 6: Verify connections
    print_step(6, 7, "Verifying connections...")
    run_command("composio connected-accounts", check=False)
    
    # Step 7: Snowflake setup instructions
    print_step(7, 7, "Snowflake setup required...")
    print("\nPlease run these SQL files in Snowflake (in order):")
    print("  1. snowflake/01_schema.sql")
    print("  2. snowflake/02_seed_data.sql")
    print("  3. snowflake/03_dynamic_tables.sql")
    print("\nSnowflake connection details:")
    print("  URL: https://sfsehol-llama_lounge_hackathon_sudhag.snowflakecomputing.com")
    print("  User: USER")
    print("  Password: sn0wf@ll")
    print("  Database: INCIDENTDNA")
    print()
    input("Press Enter after you've run the SQL files in Snowflake...")
    
    # Verification
    print("\n" + "=" * 60)
    print("Running verification tests...")
    print("=" * 60)
    print()
    
    if run_command(f"{sys.executable} test_setup.py", check=False):
        print("\n" + "=" * 60)
        print(f"{Colors.GREEN}✓ SETUP COMPLETE!{Colors.NC}")
        print("=" * 60)
        print("\nNext steps:")
        print("\n1. (Optional) Import CrewAI history:")
        print("   python import_crewai_to_snowflake.py")
        print("\n2. Start the trigger listener:")
        print("   python ingestion/trigger_listener.py")
        print("\n3. Test with a simulation:")
        print("   python test_crewai_trigger.py")
        print("\n" + "=" * 60)
    else:
        print("\n" + "=" * 60)
        print(f"{Colors.RED}✗ SETUP INCOMPLETE{Colors.NC}")
        print("=" * 60)
        print("\nPlease fix the errors above and run setup.py again")
        print()

if __name__ == "__main__":
    main()
