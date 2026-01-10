#!/usr/bin/env python3
"""
Channel → Space Filename Fix Script
===================================
Fixes remaining filename issues from the Channel → Space rename.
This handles files that should have been renamed but weren't.
"""

import os
import shutil
from pathlib import Path

# Configuration
ROOT_DIR = Path("/Users/somma/Documents/Projects/GitHub/WEB-AI-Sage-WebUI")
APP_DIR = ROOT_DIR / "app"

def find_files_to_rename():
    """Find specific files that need renaming."""
    renames = []
    
    # Look for Channel* files in components that should be Space*
    for file_path in APP_DIR.rglob("*.svelte"):
        if "Channel" in file_path.name:
            new_name = file_path.name.replace("Channel", "Space")
            new_path = file_path.parent / new_name
            renames.append((file_path, new_path))
    
    # Look for channels.py that should be spaces.py
    for file_path in APP_DIR.rglob("*.py"):
        if file_path.name == "channels.py":
            new_name = "spaces.py"
            new_path = file_path.parent / new_name
            renames.append((file_path, new_path))
    
    # Look for channels API directory that should be spaces
    channels_api = APP_DIR / "src/lib/apis/channels"
    if channels_api.exists():
        spaces_api = APP_DIR / "src/lib/apis/spaces"
        renames.append((channels_api, spaces_api))
    
    return renames

def main():
    """Main execution function."""
    print("=== Channel → Space Filename Fix Script ===")
    print(f"Working directory: {ROOT_DIR}")
    
    # Find files to rename
    renames = find_files_to_rename()
    
    if not renames:
        print("No files need renaming.")
        return
    
    print(f"\nFound {len(renames)} files/directories to rename:")
    for old_path, new_path in renames:
        print(f"  {old_path.relative_to(APP_DIR)} → {new_path.relative_to(APP_DIR)}")
    
    response = input(f"\nProceed with renaming {len(renames)} files? (y/N): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    # Perform renames using git mv
    for old_path, new_path in renames:
        if old_path.exists():
            print(f"Renaming: {old_path.relative_to(APP_DIR)} → {new_path.relative_to(APP_DIR)}")
            os.system(f'cd "{ROOT_DIR}" && git mv "{old_path}" "{new_path}"')
        else:
            print(f"File not found: {old_path}")
    
    print(f"\n✓ Completed {len(renames)} file renames")
    print("Next step: Test the application to ensure all imports work")

if __name__ == "__main__":
    main()
