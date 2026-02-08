#!/bin/bash
set -e

# ChatGemini Rust Installer (SakiTool)
# Universal Installer script

# Define colors
PURPLE='\033[1;35m'
BLUE='\033[1;34m'
GREEN='\033[1;32m'
RED='\033[1;31m'
NC='\033[0m' # No Color

echo -e "${PURPLE}== ChatGemini Rust Installer ==${NC}"

# Check Rust
if ! command -v cargo &> /dev/null; then
    echo -e "${RED}Error: Rust (cargo) is not installed.${NC}"
    echo "Please install Rust via https://rustup.rs/ or your package manager."
    exit 1
fi

# Detect directory structure
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$SCRIPT_DIR/rust_rewrite/chat_gemini_rust"

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}Error: Project directory not found at $PROJECT_DIR${NC}"
    echo "Please ensure you are running this script from the root of the repository."
    exit 1
fi

echo -e "${BLUE}-> Building Release Binary...${NC}"
cd "$PROJECT_DIR"
cargo build --release

echo -e "${BLUE}-> Setting up Environment...${NC}"
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "Created .env file from example."
    else
        # Create minimal .env
        echo "GEMINI_MODEL=gemini-2.0-flash" > .env
        echo "GEMINI_LANG=zh-TW" >> .env
        echo "Created fresh .env file."
    fi
else
    echo ".env already exists. Skipping."
fi

# Link binary to root
echo -e "${BLUE}-> Linking Binary...${NC}"
# Go back to root
cd "$SCRIPT_DIR"
TARGET_BIN="$PROJECT_DIR/target/release/chat_gemini_rust"
LINK_NAME="chatgemini"

if [ -f "$LINK_NAME" ] || [ -L "$LINK_NAME" ]; then
    rm "$LINK_NAME"
fi

ln -s "$TARGET_BIN" "$LINK_NAME"

echo -e "${GREEN}== Installation Complete ==${NC}"
echo -e "Run ${PURPLE}./$LINK_NAME${NC} to start."
echo -e "Note: First run will guide you through authentication setup."