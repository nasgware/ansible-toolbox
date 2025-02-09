#!/bin/bash
set -e

echo "Installing Rust..."

if command -v rustup &> /dev/null; then
    echo "Rust is already installed, updating..."
    rustup update
else
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
fi

source "$HOME/.cargo/env"

echo "Installing just..."
cargo install just

echo "Installation complete!"
echo "Please restart your terminal or run: source $HOME/.cargo/env"

echo "Installed versions:"
rustc --version
cargo --version
just --version
