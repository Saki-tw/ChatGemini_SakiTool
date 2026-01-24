#!/bin/bash
set -e

# ChatGemini Rust Installer (SakiTool)
# Auto-detect OS and install dependencies if possible

echo -e "\033[1;35m== ChatGemini Rust Installer ==\033[0m"

# Check Rust
if ! command -v cargo &> /dev/null; then
    echo -e "\033[1;31mError: Rust (cargo) is not installed.\033[0m"
    echo "Please install Rust via https://rustup.rs/"
    exit 1
fi

echo -e "\033[1;34m-> Building Release Binary...\033[0m"
cd rust_rewrite/chat_gemini_rust
cargo build --release

echo -e "\033[1;34m-> Setting up Environment...\033[0m"
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please edit it to add your API Key."
else
    echo ".env already exists. Skipping."
fi

# Link binary to root
echo -e "\033[1;34m-> Linking Binary...\033[0m"
cd ../..
ln -sf rust_rewrite/chat_gemini_rust/target/release/chat_gemini_rust chatgemini

echo -e "\033[1;32m== Installation Complete ==\033[0m"
echo -e "Run \033[1m./chatgemini\033[0m to start."
