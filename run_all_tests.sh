#!/bin/bash

# Advanced Test Runner for Expense Processor
# ------------------------------------------

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

LOGFILE="test_run.log"
echo "Test run started at $(date)" > "$LOGFILE"

# Activate virtual environment
if [ -d "venv" ]; then
    echo -e "${CYAN}Activating virtual environment...${NC}"
    source venv/bin/activate
else
    echo -e "${YELLOW}No venv found. Please create one for best results.${NC}"
fi

# Install dependencies
echo -e "${CYAN}Installing dependencies...${NC}"
pip install -r requirements.txt >> "$LOGFILE" 2>&1

success=0
fail=0

echo -e "${CYAN}Running all test scripts...${NC}"

for f in test_*.py; do
    echo -e "${CYAN}----------------------------------------${NC}"
    echo -e "${CYAN}Running $f${NC}"
    echo "Running $f" >> "$LOGFILE"
    if python3 "$f" >> "$LOGFILE" 2>&1; then
        echo -e "${GREEN}✅ $f PASSED${NC}"
        ((success++))
    else
        echo -e "${RED}❌ $f FAILED${NC}"
        ((fail++))
        echo "FAILED: $f" >> "$LOGFILE"
    fi

done

echo -e "${CYAN}----------------------------------------${NC}"
echo -e "${CYAN}Test summary: ${GREEN}$success passed${NC}, ${RED}$fail failed${NC}"
echo "Test summary: $success passed, $fail failed" >> "$LOGFILE"

if [ $fail -gt 0 ]; then
    echo -e "${YELLOW}Some tests failed. Check $LOGFILE for details.${NC}"
else
    echo -e "${GREEN}All tests passed!${NC}"
fi 