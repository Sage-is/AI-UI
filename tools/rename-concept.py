#!/usr/bin/env python3
"""
Universal Concept Renaming Tool
===============================
Systematically renames any concept throughout the codebase following DRY/KISS principles.

Usage:
    python3 rename-concept.py OLD_NAME NEW_NAME [--dry-run]

Examples:
    python3 rename-concept.py workspace workshop
    python3 rename-concept.py channels spaces --dry-run
    python3 rename-concept.py modelfiles models

Order of operations (case-sensitive):
1. OLD_NAME_UPPER → NEW_NAME_UPPER (environment variables)
2. OldNameTitle → NewNameTitle (class names, titles)  
3. old_name_lower → new_name_lower (URLs, variables, paths)
"""

import os
import re
import shutil
import sys
import argparse
from pathlib import Path

# Configuration
ROOT_DIR = Path("/Users/somma/Documents/Projects/GitHub/WEB-AI-Sage-WebUI")
APP_DIR = ROOT_DIR / "app"

# File patterns to process
FILE_PATTERNS = [
    "**/*.py", "**/*.js", "**/*.ts", "**/*.svelte", 
    "**/*.json", "**/*.md", "**/*.yml", "**/*.yaml"
]

# Directories to skip
SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", 
    "dist", "build", ".svelte-kit", "submodules"
}

def get_files_to_process():
    """Get all files that need processing."""
    files = []
    for pattern in FILE_PATTERNS:
        for file_path in APP_DIR.rglob(pattern):
            # Skip if in excluded directory
            if any(skip_dir in file_path.parts for skip_dir in SKIP_DIRS):
                continue
            files.append(file_path)
    return files

def create_backup(old_name):
    """Create backup of app directory."""
    backup_dir = ROOT_DIR / f"app_backup_{old_name}_rename"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    print(f"Creating backup at {backup_dir}")
    shutil.copytree(APP_DIR, backup_dir)
    return backup_dir

def get_case_variants(old_name, new_name):
    """Generate all case variants for renaming."""
    return [
        (old_name.upper(), new_name.upper()),           # WORKSPACE → WORKSHOP
        (old_name.capitalize(), new_name.capitalize()), # Workspace → Workshop
        (old_name.lower(), new_name.lower())            # workspace → workshop
    ]

def find_directories_to_rename(old_name, new_name):
    """Find directories that need renaming."""
    old_lower = old_name.lower()
    new_lower = new_name.lower()
    
    directories = []
    for root, dirs, files in os.walk(APP_DIR):
        for dir_name in dirs:
            if old_lower in dir_name.lower():
                old_path = Path(root) / dir_name
                new_dir_name = dir_name.replace(old_lower, new_lower)
                new_path = Path(root) / new_dir_name
                directories.append((old_path, new_path))
    
    return directories

def process_file_content(file_path, replacements):
    """Process file content with ordered replacements."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        replacements_made = 0
        
        for old, new in replacements:
            before_count = content.count(old)
            content = content.replace(old, new)
            after_count = content.count(old)
            replacements_made += (before_count - after_count)
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return replacements_made
        
        return 0
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0

def rename_directories(directories, dry_run=False):
    """Rename directories using git mv to preserve history."""
    for old_path, new_path in directories:
        if old_path.exists():
            print(f"{'[DRY RUN] ' if dry_run else ''}Moving: {old_path} → {new_path}")
            if not dry_run:
                # Use git mv to preserve history
                os.system(f'cd "{ROOT_DIR}" && git mv "{old_path}" "{new_path}"')
        else:
            print(f"Directory not found: {old_path}")

def analyze_files(old_name, new_name):
    """Analyze all files and show what will be changed."""
    files = get_files_to_process()
    replacements = get_case_variants(old_name, new_name)
    
    total_files = 0
    total_replacements = 0
    
    print(f"\nAnalyzing {len(files)} files for '{old_name}' → '{new_name}'...")
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_replacements = 0
            for old, new in replacements:
                file_replacements += content.count(old)
            
            if file_replacements > 0:
                total_files += 1
                total_replacements += file_replacements
                print(f"  {file_path.relative_to(APP_DIR)}: {file_replacements} replacements")
                
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    # Check for directories to rename
    directories = find_directories_to_rename(old_name, new_name)
    if directories:
        print(f"\nDirectories to rename:")
        for old_path, new_path in directories:
            print(f"  {old_path.relative_to(APP_DIR)} → {new_path.relative_to(APP_DIR)}")
    
    print(f"\nSummary:")
    print(f"  Files to modify: {total_files}")
    print(f"  Total replacements: {total_replacements}")
    print(f"  Directories to rename: {len(directories)}")
    
    return total_files, total_replacements, directories

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Universal concept renaming tool')
    parser.add_argument('old_name', help='Old concept name (e.g., workspace)')
    parser.add_argument('new_name', help='New concept name (e.g., workshop)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    
    args = parser.parse_args()
    
    old_name = args.old_name
    new_name = args.new_name
    dry_run = args.dry_run
    
    print(f"=== {old_name.title()} → {new_name.title()} Renaming Tool ===")
    print(f"Working directory: {ROOT_DIR}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    
    # Step 1: Analyze
    print(f"\n1. ANALYSIS PHASE")
    total_files, total_replacements, directories = analyze_files(old_name, new_name)
    
    if total_replacements == 0 and len(directories) == 0:
        print(f"No {old_name} references found. Exiting.")
        return
    
    # Step 2: Confirm (skip if dry run)
    if not dry_run:
        response = input(f"\nProceed with {total_replacements} replacements in {total_files} files and {len(directories)} directory renames? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
    
    # Step 3: Backup (skip if dry run)
    if not dry_run:
        print(f"\n2. BACKUP PHASE")
        backup_dir = create_backup(old_name)
    
    # Step 4: Process files
    print(f"\n{'3' if not dry_run else '2'}. CONTENT REPLACEMENT PHASE")
    files = get_files_to_process()
    replacements = get_case_variants(old_name, new_name)
    processed_files = 0
    total_actual_replacements = 0
    
    for file_path in files:
        if dry_run:
            # Just analyze for dry run
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                file_replacements = 0
                for old, new in replacements:
                    file_replacements += content.count(old)
                if file_replacements > 0:
                    processed_files += 1
                    total_actual_replacements += file_replacements
                    print(f"  [DRY RUN] {file_path.relative_to(APP_DIR)}: {file_replacements} replacements")
            except:
                pass
        else:
            # Actually process files
            file_replacements = process_file_content(file_path, replacements)
            if file_replacements > 0:
                processed_files += 1
                total_actual_replacements += file_replacements
                print(f"  ✓ {file_path.relative_to(APP_DIR)}: {file_replacements} replacements")
    
    # Step 5: Rename directories
    print(f"\n{'4' if not dry_run else '3'}. DIRECTORY RENAME PHASE")
    rename_directories(directories, dry_run)
    
    # Step 6: Summary
    print(f"\n=== {'DRY RUN ' if dry_run else ''}COMPLETION SUMMARY ===")
    print(f"{'Would process' if dry_run else '✓ Processed'} {processed_files} files")
    print(f"{'Would make' if dry_run else '✓ Made'} {total_actual_replacements} replacements")
    print(f"{'Would rename' if dry_run else '✓ Renamed'} {len(directories)} directories")
    
    if not dry_run:
        print(f"✓ Backup created at: {backup_dir}")
        print(f"\nNext steps:")
        print(f"1. Test the application: npm run dev")
        print(f"2. Check all routes work correctly")
        print(f"3. Commit changes: git add . && git commit -m 'Rename {old_name} to {new_name}'")
        print(f"4. Remove backup if all works: rm -rf {backup_dir}")
    else:
        print(f"\nTo execute the changes, run:")
        print(f"python3 {sys.argv[0]} {old_name} {new_name}")

if __name__ == "__main__":
    main()
