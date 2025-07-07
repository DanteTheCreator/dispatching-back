#!/bin/bash

# Python Package Installation Script with SSL Handling and Retry Logic
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info "Starting Python package installation..."

# Upgrade pip first
print_info "Upgrading pip..."
pip install --upgrade pip

# Function to install a package with retries
install_package() {
    local package=$1
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        print_info "Installing $package (attempt $attempt/$max_attempts)..."
        
        if pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --timeout=120 --retries=5 "$package"; then
            print_success "Successfully installed $package"
            return 0
        else
            print_warning "Failed to install $package on attempt $attempt"
            if [ $attempt -eq $max_attempts ]; then
                print_error "Failed to install $package after $max_attempts attempts"
                return 1
            fi
            attempt=$((attempt + 1))
            sleep 5
        fi
    done
}

# Try installing from requirements.txt first, fall back to individual packages
if [ -f "requirements.txt" ]; then
    print_info "Installing from requirements.txt..."
    if pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --timeout=120 --retries=5 -r requirements.txt; then
        print_success "All packages from requirements.txt installed successfully!"
        exit 0
    else
        print_warning "requirements.txt installation failed, trying individual packages..."
    fi
fi

# List of essential packages to install individually
packages=(
    "fastapi==0.104.1"
    "uvicorn[standard]==0.24.0"
    "sqlalchemy==2.0.23"
    "psycopg2-binary==2.9.9"
    "requests==2.31.0"
    "pandas==2.1.3"
    "selenium==4.15.2"
    "python-multipart==0.0.6"
    "pydantic==2.5.0"
    "python-dotenv==1.0.0"
    "geoalchemy2==0.14.2"
)

# Install packages one by one
for package in "${packages[@]}"; do
    if ! install_package "$package"; then
        print_error "Critical: Failed to install $package"
        exit 1
    fi
done

print_success "All packages installed successfully!"
