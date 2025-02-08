#!/bin/bash

# Exit on error
set -e

echo "Installing Rust..."
# Install Rust using rustup
if command -v rustup &> /dev/null; then
    echo "Rust is already installed, updating..."
    rustup update
else
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
fi

# Load cargo into current shell
source "$HOME/.cargo/env"

echo "Installing just..."
# Install just using cargo
cargo install just

echo "Installation complete!"
echo "Please restart your terminal or run: source $HOME/.cargo/env"

# Print versions
echo "Installed versions:"
rustc --version
cargo --version
just --version
