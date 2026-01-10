#!/bin/bash

# =============================================================================
# PROJECT ENV SETUP SCRIPT
# =============================================================================
# 
# This script helps set up essential environment variables for any project
# Focuses on the core Docker/Makefile configuration that every project needs
# Works from anywhere (resolves repo root from script location)
#
# Usage:
#   tools/setup_project_env.sh                # Interactive setup
#   tools/setup_project_env.sh --auto         # Auto-generate from project name
#   tools/setup_project_env.sh --template     # Show template only
#
# =============================================================================

set -euo pipefail

# Resolve repo root based on this script's directory
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)

# Configuration
ENV_FILE="${REPO_ROOT}/.env"
BACKUP_DIR="${REPO_ROOT}/.env_backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_prompt() { echo -e "${CYAN}[INPUT]${NC} $1"; }

# Get project name from repo root or git repo
get_project_name() {
    local project_name=""
    if command -v git >/dev/null 2>&1 && git -C "${REPO_ROOT}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        project_name=$(basename "$(git -C "${REPO_ROOT}" rev-parse --show-toplevel)")
    else
        project_name=$(basename "${REPO_ROOT}")
    fi
    # Normalize: lowercase, hyphens
    project_name=$(echo "$project_name" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-\|-$//g')
    echo "$project_name"
}

generate_image_name() { local project_name="$1"; local org_name="${2:-startr}"; echo "$org_name/$project_name"; }
generate_ghcr_name() { local project_name="$1"; local org_name="${2:-startr}"; echo "ghcr.io/$org_name/$project_name"; }
generate_container_name() { local project_name="$1"; echo "$project_name"; }

var_exists() { local var_name="$1"; [[ -f "$ENV_FILE" ]] && grep -q "^[[:space:]]*\(export[[:space:]]\+\)\?$var_name=" "$ENV_FILE" 2>/dev/null; }
get_current_value() { local var_name="$1"; if [[ -f "$ENV_FILE" ]]; then grep "^[[:space:]]*\(export[[:space:]]\+\)\?$var_name=" "$ENV_FILE" | head -1 | cut -d'=' -f2- | tr -d '"' || echo ""; else echo ""; fi; }

backup_env() {
    if [[ -f "$ENV_FILE" ]]; then
        mkdir -p "$BACKUP_DIR"
        local backup_file="$BACKUP_DIR/env_backup_$TIMESTAMP"
        cp "$ENV_FILE" "$backup_file"
        log_success "Backed up existing .env to: $backup_file"
    fi
}

setup_env_vars() {
    local project_name="$1"
    local org_name="${2:-startr}"
    local port="${3:-8080}"
    local architectures="${4:-amd64 arm64}"
    local force="${5:-false}"

    local image_name=$(generate_image_name "$project_name" "$org_name")
    local ghcr_image_name=$(generate_ghcr_name "$project_name" "$org_name")
    local container_name=$(generate_container_name "$project_name")
    local volume_data="$project_name-data:/app/backend/data"

    local existing_vars=()
    local vars_to_check=("IMAGE_NAME" "GHCR_IMAGE_NAME" "CONTAINER_NAME" "PORT_MAPPING" "VOLUME_DATA" "ARCHITECTURES")
    for var in "${vars_to_check[@]}"; do
        if var_exists "$var"; then existing_vars+=("$var"); fi
    done

    if [[ ${#existing_vars[@]} -gt 0 ]] && [[ "$force" != "true" ]]; then
        log_warn "The following variables already exist in $ENV_FILE:"
        for var in "${existing_vars[@]}"; do
            local current_value=$(get_current_value "$var"); echo "  $var = $current_value";
        done
        echo
        read -p "Do you want to overwrite these variables? (y/N): " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then log_info "Setup cancelled."; return 1; fi
        force="true"
    fi

    backup_env

    local temp_file=$(mktemp)
    if [[ -f "$ENV_FILE" ]]; then
        cp "$ENV_FILE" "$temp_file"
        for var in "${vars_to_check[@]}"; do
            if var_exists "$var"; then
                if [[ "${OSTYPE:-}" == darwin* ]]; then sed -i '' "/^[[:space:]]*\(export[[:space:]]\+\)\?$var=/d" "$temp_file"; else sed -i "/^[[:space:]]*\(export[[:space:]]\+\)\?$var=/d" "$temp_file"; fi
            fi
        done
    else
        cat > "$temp_file" << EOF
# =============================================================================
# MAKEFILE CONFIGURATION
# =============================================================================

EOF
    fi

    if ! grep -q "# MAKEFILE CONFIGURATION" "$temp_file" 2>/dev/null; then
        cat > "${temp_file}.new" << EOF
# =============================================================================
# MAKEFILE CONFIGURATION
# =============================================================================

EOF
        cat "$temp_file" >> "${temp_file}.new" && mv "${temp_file}.new" "$temp_file"
    fi

    local insert_line=1
    if grep -n "# MAKEFILE CONFIGURATION" "$temp_file" >/dev/null; then
        insert_line=$(($(grep -n "# MAKEFILE CONFIGURATION" "$temp_file" | head -1 | cut -d: -f1) + 2))
    fi

    local config_block="
# Docker Image Configuration
IMAGE_NAME=$image_name
GHCR_IMAGE_NAME=$ghcr_image_name

# Container Configuration  
CONTAINER_NAME=$container_name
PORT_MAPPING=$port:$port

# Volume Configuration
VOLUME_DATA=$volume_data

# Build Configuration
ARCHITECTURES=\"$architectures\"
"

    { head -n $((insert_line - 1)) "$temp_file"; echo "$config_block"; tail -n +$insert_line "$temp_file"; } > "$ENV_FILE"
    rm "$temp_file"

    log_success "Environment variables configured for project: $project_name"
    echo
    log_info "Configuration applied:"
    echo "  IMAGE_NAME = $image_name"
    echo "  GHCR_IMAGE_NAME = $ghcr_image_name"
    echo "  CONTAINER_NAME = $container_name"
    echo "  PORT_MAPPING = $port:$port"
    echo "  VOLUME_DATA = $volume_data"
    echo "  ARCHITECTURES = \"$architectures\""
}

interactive_setup() {
    log_info "Interactive Project Environment Setup"
    echo
    local default_project=$(get_project_name)
    log_prompt "Project name (default: $default_project):"; read -p "> " project_name; project_name=${project_name:-$default_project}
    log_prompt "Organization name (default: startr):"; read -p "> " org_name; org_name=${org_name:-startr}
    log_prompt "Port number (default: 8080):"; read -p "> " port; port=${port:-8080}
    log_prompt "Architectures (default: amd64 arm64):"; read -p "> " architectures; architectures=${architectures:-"amd64 arm64"}
    echo
    log_info "Configuration Preview:"
    echo "  Project: $project_name"
    echo "  Organization: $org_name"
    echo "  Image: $(generate_image_name "$project_name" "$org_name")"
    echo "  GHCR: $(generate_ghcr_name "$project_name" "$org_name")"
    echo "  Container: $(generate_container_name "$project_name")"
    echo "  Port: $port:$port"
    echo "  Volume: $project_name-data:/app/backend/data"
    echo "  Architectures: $architectures"
    echo
    read -p "Proceed with this configuration? (Y/n): " proceed
    if [[ "$proceed" =~ ^[Nn]$ ]]; then log_info "Setup cancelled."; return 1; fi
    setup_env_vars "$project_name" "$org_name" "$port" "$architectures"
}

auto_setup() { local project_name=$(get_project_name); log_info "Auto-generating configuration for project: $project_name"; setup_env_vars "$project_name" "startr" "8080" "amd64 arm64" "false"; }

show_template() {
    local project_name=$(get_project_name)
    local image_name=$(generate_image_name "$project_name" "startr")
    local ghcr_image_name=$(generate_ghcr_name "$project_name" "startr")
    cat << EOF
# =============================================================================
# MAKEFILE CONFIGURATION
# =============================================================================

# Docker Image Configuration
IMAGE_NAME=$image_name
GHCR_IMAGE_NAME=$ghcr_image_name

# Container Configuration  
CONTAINER_NAME=$project_name
PORT_MAPPING=8080:8080

# Volume Configuration
VOLUME_DATA=$project_name-data:/app/backend/data

# Build Configuration
ARCHITECTURES="amd64 arm64"

EOF
}

show_usage() {
    cat << EOF
Project Environment Setup Script

This script helps set up essential Docker/Makefile configuration variables
that every project needs.

USAGE:
    tools/setup_project_env.sh            Interactive setup (recommended)
    tools/setup_project_env.sh --auto     Auto-generate from project name
    tools/setup_project_env.sh --template Show template configuration
    tools/setup_project_env.sh --help     Show this help

WHAT IT SETS UP:
    - IMAGE_NAME: Docker image name (org/project-name)
    - GHCR_IMAGE_NAME: GitHub Container Registry name  
    - CONTAINER_NAME: Docker container name
    - PORT_MAPPING: Port mapping for container
    - VOLUME_DATA: Volume mapping for data persistence
    - ARCHITECTURES: Build architectures

The script will warn you if variables already exist and ask for confirmation
before overwriting them.

EOF
}

main() {
    local command=${1:-""}
    case "$command" in
        "--auto"|"-a") auto_setup ;;
        "--template"|"-t") show_template ;;
        "--help"|"-h"|"help") show_usage ;;
        "") interactive_setup ;;
        *) log_error "Unknown command: $command"; show_usage; exit 1 ;;
    esac
}

main "$@"
