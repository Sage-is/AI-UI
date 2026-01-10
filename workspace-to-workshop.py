#!/usr/bin/env python3
"""
Workspace → Workshop Renaming Script
=====================================
Systematically renames all workspace references to workshop following DRY/KISS principles.

Order of operations (case-sensitive):
1. WORKSPACE → WORKSHOP (environment variables)
2. Workspace → Workshop (class names, titles)  
3. workspace → workshop (URLs, variables, paths)
"""

import os
import re
import shutil
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

def create_backup():
    """Create backup of app directory."""
    backup_dir = ROOT_DIR / "app_backup_workspace_rename"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    print(f"Creating backup at {backup_dir}")
    shutil.copytree(APP_DIR, backup_dir)
    return backup_dir

def process_file_content(file_path):
    """Process file content with ordered replacements."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        replacements_made = 0
        
        # Ordered replacements (case-sensitive)
        replacements = [
            ("WORKSPACE", "WORKSHOP"),
            ("Workspace", "Workshop"), 
            ("workspace", "workshop")
        ]
        
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

def rename_directories():
    """Rename the main workspace directories."""
    moves = [
        (APP_DIR / "src/lib/components/workspace", APP_DIR / "src/lib/components/workshop"),
        (APP_DIR / "src/routes/(app)/workspace", APP_DIR / "src/routes/(app)/workshop")
    ]
    
    for old_path, new_path in moves:
        if old_path.exists():
            print(f"Moving: {old_path} → {new_path}")
            # Use git mv to preserve history
            os.system(f'cd "{ROOT_DIR}" && git mv "{old_path}" "{new_path}"')
        else:
            print(f"Directory not found: {old_path}")

def analyze_files():
    """Analyze all files and show what will be changed."""
    files = get_files_to_process()
    total_files = 0
    total_replacements = 0
    
    print(f"\nAnalyzing {len(files)} files...")
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_replacements = 0
            for old, new in [("WORKSPACE", "WORKSHOP"), ("Workspace", "Workshop"), ("workspace", "workshop")]:
                file_replacements += content.count(old)
            
            if file_replacements > 0:
                total_files += 1
                total_replacements += file_replacements
                print(f"  {file_path.relative_to(APP_DIR)}: {file_replacements} replacements")
                
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    print(f"\nSummary:")
    print(f"  Files to modify: {total_files}")
    print(f"  Total replacements: {total_replacements}")
    return total_files, total_replacements

def main():
    """Main execution function."""
    print("=== Workspace → Workshop Renaming Script ===")
    print(f"Working directory: {ROOT_DIR}")
    
    # Step 1: Analyze
    print("\n1. ANALYSIS PHASE")
    total_files, total_replacements = analyze_files()
    
    if total_replacements == 0:
        print("No workspace references found. Exiting.")
        return
    
    # Step 2: Confirm
    response = input(f"\nProceed with {total_replacements} replacements in {total_files} files? (y/N): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    # Step 3: Backup
    print("\n2. BACKUP PHASE")
    backup_dir = create_backup()
    
    # Step 4: Process files
    print("\n3. CONTENT REPLACEMENT PHASE")
    files = get_files_to_process()
    processed_files = 0
    total_actual_replacements = 0
    
    for file_path in files:
        replacements = process_file_content(file_path)
        if replacements > 0:
            processed_files += 1
            total_actual_replacements += replacements
            print(f"  ✓ {file_path.relative_to(APP_DIR)}: {replacements} replacements")
    
    # Step 5: Rename directories
    print("\n4. DIRECTORY RENAME PHASE")
    rename_directories()
    
    # Step 6: Summary
    print(f"\n=== COMPLETION SUMMARY ===")
    print(f"✓ Processed {processed_files} files")
    print(f"✓ Made {total_actual_replacements} replacements")
    print(f"✓ Renamed workspace directories to workshop")
    print(f"✓ Backup created at: {backup_dir}")
    print(f"\nNext steps:")
    print(f"1. Test the application: npm run dev")
    print(f"2. Check all routes work correctly")
    print(f"3. Commit changes: git add . && git commit -m 'Rename workspace to workshop'")
    print(f"4. Remove backup if all works: rm -rf {backup_dir}")

if __name__ == "__main__":
    main()
