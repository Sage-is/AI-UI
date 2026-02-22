---
title: "Environment Management Scripts"
description: "Documentation for setup_project_env.sh and manage_env.sh environment variable management scripts."
date: 2025-10-13
tags:
  - environment
  - scripts
  - configuration
  - devops
---

# Environment Management Scripts

This directory contains scripts to help manage environment variables for any project.

## Scripts Overview

### `setup_project_env.sh` - Project-Specific Environment Setup

The main script for setting up essential Docker/Makefile configuration variables that every project needs.

**What it sets up:**
- `IMAGE_NAME`: Docker image name (org/project-name)
- `GHCR_IMAGE_NAME`: GitHub Container Registry name
- `CONTAINER_NAME`: Docker container name
- `PORT_MAPPING`: Port mapping for container
- `VOLUME_DATA`: Volume mapping for data persistence
- `ARCHITECTURES`: Build architectures

**Usage:**
```bash
./setup_project_env.sh                # Interactive setup (recommended)
./setup_project_env.sh --auto         # Auto-generate from project name
./setup_project_env.sh --template     # Show template configuration
./setup_project_env.sh --help         # Show help
```

**Features:**
- Detects existing variables and warns before overwriting
- Auto-generates project name from git repo or directory name
- Creates backups before making changes
- Interactive mode with customizable options
- Template mode to preview configuration

### `manage_env.sh` - General Environment Variable Manager

A comprehensive tool for managing any environment variables in `.env` files.

**Usage:**
```bash
./manage_env.sh                          # Interactive mode
./manage_env.sh set VAR=value            # Set single variable
./manage_env.sh set VAR=value --force    # Set variable (force overwrite)
./manage_env.sh check VAR                # Check if variable exists
./manage_env.sh get VAR                  # Get variable value
./manage_env.sh list                     # List all variables
./manage_env.sh backup                   # Backup current .env
./manage_env.sh restore                  # Restore from backup
```

**Features:**
- Handles both `export VAR=value` and `VAR=value` formats
- Interactive mode for setting multiple variables
- Backup and restore functionality
- Variable existence checking
- Colorized output with clear status messages

## Quick Start

For a new project, use the focused setup script:

```bash
# Quick setup with defaults
./setup_project_env.sh --auto

# Or interactive setup for customization
./setup_project_env.sh
```

For managing additional environment variables:

```bash
# Check what's currently set
./manage_env.sh list

# Add new variables
./manage_env.sh set OPENAI_API_KEY=your-key-here
```

## Safety Features

Both scripts include safety features:

- **Backup Creation**: Automatic backups before making changes
- **Existing Variable Detection**: Warns when variables already exist
- **Confirmation Prompts**: Asks before overwriting existing values
- **Force Flags**: Available to skip confirmations when needed

## File Organization

The scripts create a `.env_backups/` directory for storing backup files with timestamps, making it easy to restore previous configurations if needed.

## Integration with Projects

These scripts are designed to be:

- **Portable**: Can be copied to any project
- **Non-destructive**: Always backs up before changes
- **User-friendly**: Clear prompts and colored output
- **Flexible**: Works with any project structure

The `setup_project_env.sh` script is particularly useful for quickly configuring the essential Docker/Makefile variables that most projects need, while `manage_env.sh` provides comprehensive environment variable management for any additional configuration needs.
