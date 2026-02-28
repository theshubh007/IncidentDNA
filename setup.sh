#!/bin/bash

# IncidentDNA Setup Script
# Automates the complete setup process

set -e  # Exit on error

echo "============================================================"
echo "IncidentDNA Setup Script"
echo "============================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Install Python dependencies
echo -e "${YELLOW}[STEP 1/7]${NC} Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}✓${NC} Dependencies installed"
else
    echo -e "${RED}✗${NC} requirements.txt not found!"
    exit 1
fi
echo ""

# Step 2: Setup environment file
echo -e "${YELLOW}[STEP 2/7]${NC} Setting up environment file..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✓${NC} Created .env file from .env.example"
        echo -e "${YELLOW}⚠${NC}  Please edit .env and add your COMPOSIO_API_KEY"
        echo ""
        echo "Required variables:"
        echo "  - COMPOSIO_API_KEY (get from https://app.composio.dev)"
        echo "  - SNOWFLAKE_* (already configured)"
        echo ""
        read -p "Press Enter after you've updated .env file..."
    else
        echo -e "${RED}✗${NC} .env.example not found!"
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} .env file already exists"
fi
echo ""

# Step 3: Composio authentication
echo -e "${YELLOW}[STEP 3/7]${NC} Authenticating with Composio..."
echo "This will open a browser window for authentication..."
composio login

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Composio authentication successful"
else
    echo -e "${RED}✗${NC} Composio authentication failed"
    exit 1
fi
echo ""

# Step 4: Connect GitHub
echo -e "${YELLOW}[STEP 4/7]${NC} Connecting GitHub..."
echo "This will open a browser window for GitHub OAuth..."
composio add github

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} GitHub connected"
else
    echo -e "${RED}✗${NC} GitHub connection failed"
    exit 1
fi
echo ""

# Step 5: Connect Slack
echo -e "${YELLOW}[STEP 5/7]${NC} Connecting Slack..."
echo "This will open a browser window for Slack OAuth..."
composio add slack

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Slack connected"
else
    echo -e "${YELLOW}⚠${NC}  Slack connection failed (optional, continuing...)"
fi
echo ""

# Step 6: Verify connections
echo -e "${YELLOW}[STEP 6/7]${NC} Verifying connections..."
composio connected-accounts
echo ""

# Step 7: Snowflake setup instructions
echo -e "${YELLOW}[STEP 7/7]${NC} Snowflake setup required..."
echo ""
echo "Please run these SQL files in Snowflake (in order):"
echo "  1. snowflake/01_schema.sql"
echo "  2. snowflake/02_seed_data.sql"
echo "  3. snowflake/03_dynamic_tables.sql"
echo ""
echo "Snowflake connection details:"
echo "  URL: https://sfsehol-llama_lounge_hackathon_sudhag.snowflakecomputing.com"
echo "  User: USER"
echo "  Password: sn0wf@ll"
echo "  Database: INCIDENTDNA"
echo ""
read -p "Press Enter after you've run the SQL files in Snowflake..."
echo ""

# Verification
echo "============================================================"
echo "Running verification tests..."
echo "============================================================"
echo ""

python test_setup.py

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo -e "${GREEN}✓ SETUP COMPLETE!${NC}"
    echo "============================================================"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. (Optional) Import CrewAI history:"
    echo "   python import_crewai_to_snowflake.py"
    echo ""
    echo "2. Start the trigger listener:"
    echo "   python ingestion/trigger_listener.py"
    echo ""
    echo "3. Test with a simulation:"
    echo "   python test_crewai_trigger.py"
    echo ""
    echo "============================================================"
else
    echo ""
    echo "============================================================"
    echo -e "${RED}✗ SETUP INCOMPLETE${NC}"
    echo "============================================================"
    echo ""
    echo "Please fix the errors above and run setup.sh again"
    echo ""
fi
