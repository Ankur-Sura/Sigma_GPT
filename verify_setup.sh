#!/bin/bash

# =============================================================================
#                     SIGMA GPT - SETUP VERIFICATION SCRIPT
# =============================================================================
# This script verifies that everything is set up correctly
# Run: bash verify_setup.sh

set -e

echo "🔍 Sigma GPT - Setup Verification"
echo "================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

# =============================================================================
# CHECK FILES
# =============================================================================
echo "📁 Checking required files..."

# Check .env files
if [ -f "Backend/.env" ]; then
    echo "   ${GREEN}✅${NC} Backend/.env exists"
else
    echo "   ${RED}❌${NC} Backend/.env missing"
    ERRORS=$((ERRORS + 1))
fi

if [ -f "AI/.env" ]; then
    echo "   ${GREEN}✅${NC} AI/.env exists"
else
    echo "   ${RED}❌${NC} AI/.env missing"
    ERRORS=$((ERRORS + 1))
fi

if [ -f "Frontend/.env" ]; then
    echo "   ${GREEN}✅${NC} Frontend/.env exists"
else
    echo "   ${RED}❌${NC} Frontend/.env missing"
    ERRORS=$((ERRORS + 1))
fi

# Check package.json files
if [ -f "Backend/package.json" ]; then
    echo "   ${GREEN}✅${NC} Backend/package.json exists"
else
    echo "   ${RED}❌${NC} Backend/package.json missing"
    ERRORS=$((ERRORS + 1))
fi

if [ -f "AI/requirements.txt" ]; then
    echo "   ${GREEN}✅${NC} AI/requirements.txt exists"
else
    echo "   ${RED}❌${NC} AI/requirements.txt missing"
    ERRORS=$((ERRORS + 1))
fi

if [ -f "Frontend/package.json" ]; then
    echo "   ${GREEN}✅${NC} Frontend/package.json exists"
else
    echo "   ${RED}❌${NC} Frontend/package.json missing"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# =============================================================================
# CHECK ENVIRONMENT VARIABLES
# =============================================================================
echo "🔐 Checking environment variables..."

if [ -f "Backend/.env" ]; then
    if grep -q "MONGODB_URI" "Backend/.env" && ! grep -q "your-" "Backend/.env"; then
        echo "   ${GREEN}✅${NC} Backend MONGODB_URI configured"
    else
        echo "   ${YELLOW}⚠️${NC}  Backend MONGODB_URI needs configuration"
    fi
fi

if [ -f "AI/.env" ]; then
    if grep -q "MONGODB_URI" "AI/.env" && ! grep -q "your-" "AI/.env"; then
        echo "   ${GREEN}✅${NC} AI MONGODB_URI configured"
    else
        echo "   ${YELLOW}⚠️${NC}  AI MONGODB_URI needs configuration"
    fi
fi

if [ -f "Frontend/.env" ]; then
    if grep -q "VITE_API_URL" "Frontend/.env"; then
        echo "   ${GREEN}✅${NC} Frontend VITE_API_URL configured"
    else
        echo "   ${YELLOW}⚠️${NC}  Frontend VITE_API_URL needs configuration"
    fi
fi

echo ""

# =============================================================================
# CHECK DEPENDENCIES
# =============================================================================
echo "📦 Checking dependencies..."

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "   ${GREEN}✅${NC} Node.js installed: $NODE_VERSION"
else
    echo "   ${RED}❌${NC} Node.js not installed"
    ERRORS=$((ERRORS + 1))
fi

# Check npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo "   ${GREEN}✅${NC} npm installed: $NPM_VERSION"
else
    echo "   ${RED}❌${NC} npm not installed"
    ERRORS=$((ERRORS + 1))
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "   ${GREEN}✅${NC} Python installed: $PYTHON_VERSION"
else
    echo "   ${RED}❌${NC} Python not installed"
    ERRORS=$((ERRORS + 1))
fi

# Check pip
if command -v pip3 &> /dev/null; then
    echo "   ${GREEN}✅${NC} pip installed"
else
    echo "   ${YELLOW}⚠️${NC}  pip not found (may need: python3 -m pip)"
fi

echo ""

# =============================================================================
# CHECK NODE MODULES
# =============================================================================
echo "📚 Checking installed packages..."

if [ -d "Backend/node_modules" ]; then
    echo "   ${GREEN}✅${NC} Backend node_modules installed"
else
    echo "   ${YELLOW}⚠️${NC}  Backend node_modules not installed (run: cd Backend && npm install)"
fi

if [ -d "Frontend/node_modules" ]; then
    echo "   ${GREEN}✅${NC} Frontend node_modules installed"
else
    echo "   ${YELLOW}⚠️${NC}  Frontend node_modules not installed (run: cd Frontend && npm install)"
fi

echo ""

# =============================================================================
# SUMMARY
# =============================================================================
echo "================================="
if [ $ERRORS -eq 0 ]; then
    echo "${GREEN}✅ Setup looks good!${NC}"
    echo ""
    echo "🚀 Ready to run:"
    echo "   1. Backend: cd Backend && npm start"
    echo "   2. AI Service: cd AI && python main.py"
    echo "   3. Frontend: cd Frontend && npm run dev"
else
    echo "${RED}❌ Found $ERRORS critical issue(s)${NC}"
    echo "   Please fix the issues above before proceeding"
fi
echo ""

