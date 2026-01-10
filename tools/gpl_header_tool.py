#!/usr/bin/env python3

# Copyright (C) 2023-2025 Sage.Is AI a part of Startr, LLC. <https://Sage.is/>
#
# This program is Open-Source Software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
GPL License Header Tool
Automatically adds GPL license headers to source files across multiple languages.
"""

import os
import sys
import argparse
import re
import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Set

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Configuration file template
CONFIG_TEMPLATE = """# GPL License Header Configuration
copyright_holder: "Sage.is part of Startr LLC"
year: "2023-2025"
license_type: "agpl3"  # Options: gpl2, gpl3, agpl3, lgpl2, lgpl3
contact_info: ""  # Optional: email or website

# File patterns to include/exclude
include_patterns:
  - "*.py"
  - "*.js"
  - "*.ts"
  - "*.svelte"
  - "*.html"
  - "*.css"
  - "*.scss"
  - "*.java"
  - "*.c"
  - "*.cpp"
  - "*.h"
  - "*.hpp"

exclude_patterns:
  - "node_modules/**"
  - ".git/**"
  - "dist/**"
  - "build/**"
  - "*.min.js"
  - "*.min.css"

# Directories to scan
scan_directories:
  - "src"
  - "lib"
  - "."
"""

# License templates
LICENSE_TEMPLATES = {
    "gpl2": {
        "name": "GNU General Public License v2.0",
        "url": "https://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
        "text": """This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA."""
    },
    "gpl3": {
        "name": "GNU General Public License v3.0",
        "url": "https://www.gnu.org/licenses/gpl-3.0.html",
        "text": """This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>."""
    },
    "agpl3": {
        "name": "GNU Affero General Public License v3.0",
        "url": "https://www.gnu.org/licenses/agpl-3.0.html",
        "text": """This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>."""
    },
    "lgpl2": {
        "name": "GNU Lesser General Public License v2.1",
        "url": "https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html",
        "text": """This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA"""
    },
    "lgpl3": {
        "name": "GNU Lesser General Public License v3.0",
        "url": "https://www.gnu.org/licenses/lgpl-3.0.html",
        "text": """This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>."""
    }
}

# Comment styles for different file types
COMMENT_STYLES = {
    # C-style comments
    'c': {'start': '/*', 'middle': ' * ', 'end': ' */'},
    'cpp': {'start': '/*', 'middle': ' * ', 'end': ' */'},
    'h': {'start': '/*', 'middle': ' * ', 'end': ' */'},
    'hpp': {'start': '/*', 'middle': ' * ', 'end': ' */'},
    'java': {'start': '/*', 'middle': ' * ', 'end': ' */'},
    'js': {'start': '/*', 'middle': ' * ', 'end': ' */'},
    'ts': {'start': '/*', 'middle': ' * ', 'end': ' */'},
    'css': {'start': '/*', 'middle': ' * ', 'end': ' */'},
    'scss': {'start': '/*', 'middle': ' * ', 'end': ' */'},
    
    # Hash comments
    'py': {'start': '#', 'middle': '# ', 'end': None},
    'sh': {'start': '#', 'middle': '# ', 'end': None},
    'yaml': {'start': '#', 'middle': '# ', 'end': None},
    'yml': {'start': '#', 'middle': '# ', 'end': None},
    
    # HTML comments
    'html': {'start': '<!--', 'middle': '   ', 'end': '-->'},
    'xml': {'start': '<!--', 'middle': '   ', 'end': '-->'},
    'svelte': {'start': '<!--', 'middle': '   ', 'end': '-->'},
}

class LicenseHeaderTool:
    def __init__(self, config_file: str = "license_config.yml"):
        self.config_file = config_file
        self.gitignore_patterns = self.load_gitignore_patterns()
        self.config = self.load_config()
    
    def load_gitignore_patterns(self) -> Set[str]:
        """Load patterns from .gitignore files."""
        patterns = set()
        
        # Common ignore patterns
        patterns.update([
            '.git/**',
            '.git/*',
            'node_modules/**',
            'node_modules/*',
            '*.min.js',
            '*.min.css',
            'dist/**',
            'build/**',
            '__pycache__/**',
            '*.pyc',
            '.DS_Store'
        ])
        
        # Load .gitignore files
        for gitignore_path in ['.gitignore', './.gitignore']:
            if os.path.exists(gitignore_path):
                try:
                    with open(gitignore_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                patterns.add(line)
                                # Also add pattern with /** for directory matching
                                if not line.endswith('/') and not line.endswith('/**'):
                                    patterns.add(line + '/**')
                except Exception as e:
                    print(f"Warning: Could not read {gitignore_path}: {e}")
        
        return patterns
    
    def is_ignored(self, filepath: str) -> bool:
        """Check if file should be ignored based on .gitignore patterns."""
        # Convert to relative path for matching
        try:
            rel_path = os.path.relpath(filepath)
        except ValueError:
            rel_path = filepath
        
        for pattern in self.gitignore_patterns:
            # Handle different pattern types
            if pattern.endswith('/**'):
                # Directory pattern
                dir_pattern = pattern[:-3]
                if rel_path.startswith(dir_pattern + '/') or rel_path == dir_pattern:
                    return True
            elif '/' in pattern:
                # Path pattern
                if fnmatch.fnmatch(rel_path, pattern):
                    return True
            else:
                # Filename pattern - check against basename and full path
                if fnmatch.fnmatch(os.path.basename(rel_path), pattern) or fnmatch.fnmatch(rel_path, pattern):
                    return True
        
        return False
    
    def detect_license_from_file(self) -> Optional[Dict]:
        """Detect license information from LICENSE file."""
        license_files = ['LICENSE', 'LICENSE.txt', 'LICENSE.md', 'COPYING', 'COPYING.txt']
        
        for license_file in license_files:
            if os.path.exists(license_file):
                try:
                    with open(license_file, 'r', encoding='utf-8') as f:
                        content = f.read().upper()
                    
                    # Detect license type based on content
                    if 'AFFERO GENERAL PUBLIC LICENSE' in content:
                        if 'VERSION 3' in content:
                            return {
                                'license_type': 'agpl3',
                                'detected_from': license_file
                            }
                    elif 'GENERAL PUBLIC LICENSE' in content:
                        if 'VERSION 3' in content:
                            return {
                                'license_type': 'gpl3',
                                'detected_from': license_file
                            }
                        elif 'VERSION 2' in content:
                            return {
                                'license_type': 'gpl2',
                                'detected_from': license_file
                            }
                    elif 'LESSER GENERAL PUBLIC LICENSE' in content:
                        if 'VERSION 3' in content:
                            return {
                                'license_type': 'lgpl3',
                                'detected_from': license_file
                            }
                        elif 'VERSION 2' in content:
                            return {
                                'license_type': 'lgpl2',
                                'detected_from': license_file
                            }
                    
                except Exception as e:
                    print(f"Warning: Could not read {license_file}: {e}")
        
        return None
    
    def extract_copyright_from_license(self) -> Optional[Dict]:
        """Extract copyright information from LICENSE file."""
        license_files = ['LICENSE', 'LICENSE.txt', 'LICENSE.md', 'COPYING', 'COPYING.txt']
        
        for license_file in license_files:
            if os.path.exists(license_file):
                try:
                    with open(license_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Look for copyright lines
                    copyright_patterns = [
                        r'Copyright\s*\(C\)\s*(\d{4}(?:-\d{4})?)\s+(.+?)(?:\n|$)',
                        r'Copyright\s+(\d{4}(?:-\d{4})?)\s+(.+?)(?:\n|$)',
                        r'\(C\)\s*(\d{4}(?:-\d{4})?)\s+(.+?)(?:\n|$)'
                    ]
                    
                    for pattern in copyright_patterns:
                        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
                        if match:
                            year = match.group(1)
                            holder = match.group(2).strip()
                            # Clean up holder name
                            holder = re.sub(r'\s+', ' ', holder)
                            holder = holder.rstrip('.')
                            return {
                                'year': year,
                                'copyright_holder': holder
                            }
                    
                except Exception as e:
                    print(f"Warning: Could not read {license_file}: {e}")
        
        return None
    
    def load_config(self) -> dict:
        """Load configuration from YAML file or detect from LICENSE."""
        config = {}
        
        # First, try to detect from LICENSE file
        license_info = self.detect_license_from_file()
        copyright_info = self.extract_copyright_from_license()
        
        if license_info and copyright_info:
            print(f"Detected license: {license_info['license_type']} from {license_info['detected_from']}")
            print(f"Detected copyright: {copyright_info['year']} {copyright_info['copyright_holder']}")
            
            config = {
                'license_type': license_info['license_type'],
                'year': copyright_info['year'],
                'copyright_holder': copyright_info['copyright_holder'],
                'contact_info': '',
                'include_patterns': [
                    "*.py", "*.js", "*.ts", "*.svelte", "*.html", "*.css", "*.scss",
                    "*.java", "*.c", "*.cpp", "*.h", "*.hpp"
                ],
                'exclude_patterns': [],  # Will use .gitignore instead
                'scan_directories': ["."]
            }
            
            return config
        
        # Fallback to config file
        if not os.path.exists(self.config_file):
            print(f"No LICENSE file found and config file {self.config_file} not found.")
            print("Run with --setup to create a configuration.")
            return {}
        
        try:
            if YAML_AVAILABLE:
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f) or {}
            else:
                print("PyYAML not installed. Cannot read YAML config file.")
                print("Install it with: pip install PyYAML")
                print("Or use --setup for interactive configuration.")
                return {}
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
        
        return config
    
    def create_config_template(self):
        """Create a configuration template file."""
        if not YAML_AVAILABLE:
            print("PyYAML not installed. Please install it with: pip install PyYAML")
            print("Or use --setup for interactive configuration without YAML dependency.")
            return
            
        with open(self.config_file, 'w') as f:
            f.write(CONFIG_TEMPLATE)
        print(f"Created {self.config_file}. Please review and modify as needed.")
    
    def get_file_extension(self, filepath: str) -> str:
        """Get file extension without the dot."""
        return Path(filepath).suffix[1:].lower()
    
    def get_comment_style(self, filepath: str) -> Optional[Dict[str, str]]:
        """Get comment style for file type."""
        ext = self.get_file_extension(filepath)
        return COMMENT_STYLES.get(ext)
    
    def generate_header(self, filepath: str) -> str:
        """Generate license header for a specific file."""
        comment_style = self.get_comment_style(filepath)
        if not comment_style:
            return ""
        
        license_info = LICENSE_TEMPLATES[self.config['license_type']]
        
        # Build header content
        header_lines = []
        
        # Copyright line
        copyright_line = f"Copyright (C) {self.config['year']} {self.config['copyright_holder']}"
        header_lines.append(copyright_line)
        
        # Contact info (optional)
        if self.config.get('contact_info'):
            header_lines.append(f"Contact: {self.config['contact_info']}")
        
        header_lines.append("")  # Empty line
        header_lines.extend(license_info['text'].split('\n'))
        
        # Format with comment style
        formatted_lines = []
        
        if comment_style['end']:  # Block comment style
            formatted_lines.append(comment_style['start'])
            for line in header_lines:
                if line.strip():
                    formatted_lines.append(comment_style['middle'] + line)
                else:
                    formatted_lines.append(comment_style['middle'].rstrip())
            formatted_lines.append(comment_style['end'])
        else:  # Line comment style
            for line in header_lines:
                if line.strip():
                    formatted_lines.append(comment_style['middle'] + line)
                else:
                    formatted_lines.append(comment_style['start'])
        
        return '\n'.join(formatted_lines) + '\n\n'
    
    def has_license_header(self, content: str) -> bool:
        """Check if file already has a license header."""
        # Look for common license indicators
        license_indicators = [
            'GNU General Public License',
            'GNU Affero General Public License',
            'GNU Lesser General Public License',
            'This program is free software',
            'This library is free software'
        ]
        
        # Check first 50 lines
        lines = content.split('\n')[:50]
        content_start = '\n'.join(lines).lower()
        
        return any(indicator.lower() in content_start for indicator in license_indicators)
    
    def should_process_file(self, filepath: str) -> bool:
        """Check if file should be processed based on patterns and .gitignore."""
        # First check if file is ignored by .gitignore
        if self.is_ignored(filepath):
            return False
        
        path_obj = Path(filepath)
        
        # Check exclude patterns from config (if any)
        for pattern in self.config.get('exclude_patterns', []):
            if path_obj.match(pattern):
                return False
        
        # Check include patterns
        include_patterns = self.config.get('include_patterns', [])
        if not include_patterns:
            return False
            
        for pattern in include_patterns:
            if path_obj.match(pattern):
                return True
        
        return False
    
    def process_file(self, filepath: str, force: bool = False) -> bool:
        """Add license header to a single file."""
        if not self.should_process_file(filepath):
            return False
        
        if not self.get_comment_style(filepath):
            print(f"Skipping {filepath}: unsupported file type")
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            print(f"Skipping {filepath}: binary file")
            return False
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return False
        
        if not force and self.has_license_header(content):
            print(f"Skipping {filepath}: already has license header")
            return False
        
        header = self.generate_header(filepath)
        if not header:
            return False
        
        # Handle shebang lines
        lines = content.split('\n')
        if lines and lines[0].startswith('#!'):
            new_content = lines[0] + '\n\n' + header + '\n'.join(lines[1:])
        else:
            new_content = header + content
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Added license header to {filepath}")
            return True
        except Exception as e:
            print(f"Error writing {filepath}: {e}")
            return False
    
    def scan_directory(self, directory: str) -> List[str]:
        """Scan directory for files to process."""
        files = []
        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(root, filename)
                if self.should_process_file(filepath):
                    files.append(filepath)
        return files
    
    def process_all(self, force: bool = False, dry_run: bool = False):
        """Process all files in configured directories."""
        if not self.config:
            print("No configuration available. Run with --setup to configure the tool.")
            return
            
        if not self.config.get('license_type'):
            print("No license type specified in configuration.")
            return
        
        all_files = []
        
        for directory in self.config.get('scan_directories', ['.']):
            if os.path.exists(directory):
                files = self.scan_directory(directory)
                all_files.extend(files)
        
        if not all_files:
            print("No files found to process.")
            return
        
        print(f"Found {len(all_files)} files to process:")
        for filepath in all_files:
            print(f"  {filepath}")
        
        if dry_run:
            print("\nDry run mode - no files were modified.")
            return
        
        if not force:
            response = input(f"\nProcess {len(all_files)} files? (y/N): ")
            if response.lower() != 'y':
                print("Cancelled.")
                return
        
        processed = 0
        for filepath in all_files:
            if self.process_file(filepath, force):
                processed += 1
        
        print(f"\nProcessed {processed} out of {len(all_files)} files.")

def show_help():
    """Display help and usage information."""
    help_text = """
GPL License Header Tool
=======================

This tool automatically adds GPL license headers to source files across multiple languages.
It can automatically detect license information from existing LICENSE files.

USAGE:
    ./gpl_header_tool.py [OPTIONS]

OPTIONS:
    --help, -h          Show this help message
    --config, -c FILE   Configuration file path (default: license_config.yml)
    --force, -f         Force overwrite existing headers
    --dry-run, -n       Show what would be done without making changes
    --file FILE         Process a specific file only
    --init              Create configuration template
    --setup             Interactive project setup

AUTOMATIC LICENSE DETECTION:
    The tool automatically detects license information from:
    - LICENSE, LICENSE.txt, LICENSE.md, COPYING files
    - Extracts copyright holder and year information
    - Supports GPL v2/v3, AGPL v3, LGPL v2.1/v3

GITIGNORE SUPPORT:
    - Automatically respects .gitignore patterns
    - Won't modify files in ignored directories
    - Skips common build/cache directories

EXAMPLES:
    # Auto-detect from LICENSE file and process
    ./gpl_header_tool.py --dry-run
    
    # First time setup (if no LICENSE file exists)
    ./gpl_header_tool.py --setup
    
    # Process all files
    ./gpl_header_tool.py
    
    # Process specific file
    ./gpl_header_tool.py --file src/main.py
    
    # Force overwrite existing headers
    ./gpl_header_tool.py --force

SUPPORTED FILE TYPES:
    Python (.py), JavaScript (.js), TypeScript (.ts), Java (.java),
    C/C++ (.c, .cpp, .h, .hpp), CSS/SCSS (.css, .scss),
    HTML/XML (.html, .xml), Svelte (.svelte), Shell (.sh),
    YAML (.yml, .yaml)

For more information about GPL licenses, visit: https://www.gnu.org/licenses/
"""
    print(help_text)

def interactive_setup():
    """Interactive setup for project configuration."""
    print("GPL License Header Tool - Project Setup")
    print("=====================================\n")
    
    # Get basic information
    copyright_holder = input("Copyright holder name [Your Name]: ").strip() or "Your Name"
    year = input("Copyright year [2024]: ").strip() or "2024"
    
    # License type selection
    print("\nAvailable license types:")
    print("1. GPL v2 (GNU General Public License v2.0)")
    print("2. GPL v3 (GNU General Public License v3.0)")
    print("3. AGPL v3 (GNU Affero General Public License v3.0) - for web services")
    print("4. LGPL v2.1 (GNU Lesser General Public License v2.1) - for libraries")
    print("5. LGPL v3 (GNU Lesser General Public License v3.0) - for libraries")
    
    license_map = {
        '1': 'gpl2', '2': 'gpl3', '3': 'agpl3', '4': 'lgpl2', '5': 'lgpl3'
    }
    
    while True:
        choice = input("Select license type [3]: ").strip() or '3'
        if choice in license_map:
            license_type = license_map[choice]
            break
        print("Invalid choice. Please select 1-5.")
    
    contact_info = input("Contact info (email/website) [optional]: ").strip()
    
    # File patterns
    print("\nFile patterns to include (press Enter for defaults):")
    include_patterns = input("Include patterns [*.py,*.js,*.ts,*.c,*.cpp,*.h]: ").strip()
    if not include_patterns:
        include_patterns = ["*.py", "*.js", "*.ts", "*.c", "*.cpp", "*.h", "*.java", "*.css", "*.html"]
    else:
        include_patterns = [p.strip() for p in include_patterns.split(',')]
    
    scan_directories = input("Directories to scan [src,.]: ").strip()
    if not scan_directories:
        scan_directories = ["src", "."]
    else:
        scan_directories = [d.strip() for d in scan_directories.split(',')]
    
    # Generate config
    config_content = f"""# GPL License Header Configuration
copyright_holder: "{copyright_holder}"
year: "{year}"
license_type: "{license_type}"
contact_info: "{contact_info}"

# File patterns to include/exclude
include_patterns:
{chr(10).join(f'  - "{pattern}"' for pattern in include_patterns)}

exclude_patterns:
  - "node_modules/**"
  - ".git/**"
  - "dist/**"
  - "build/**"
  - "*.min.js"
  - "*.min.css"

# Directories to scan
scan_directories:
{chr(10).join(f'  - "{directory}"' for directory in scan_directories)}
"""
    
    config_file = "license_config.yml"
    
    # Check if config exists
    if os.path.exists(config_file):
        overwrite = input(f"\n{config_file} already exists. Overwrite? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("Setup cancelled.")
            return
    
    # Write config
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    print(f"\nConfiguration saved to {config_file}")
    print("You can now run the tool with:")
    print("  ./gpl_header_tool.py --dry-run  # Preview changes")
    print("  ./gpl_header_tool.py            # Apply changes")

def main():
    # Check if no arguments provided
    if len(sys.argv) == 1:
        print("GPL License Header Tool")
        print("======================")
        
        # Check if we can auto-detect from LICENSE file
        tool = LicenseHeaderTool()
        if tool.config:
            print(f"✓ Auto-detected license configuration from LICENSE file")
            print("What would you like to do?\n")
            print("1. Show help and usage information")
            print("2. Preview changes (dry-run)")
            print("3. Process files and add headers")
            print("4. Setup custom configuration")
            print("5. Exit")
            
            while True:
                choice = input("\nSelect an option (1-5): ").strip()
                if choice == '1':
                    show_help()
                    return
                elif choice == '2':
                    tool.process_all(dry_run=True)
                    return
                elif choice == '3':
                    tool.process_all()
                    return
                elif choice == '4':
                    interactive_setup()
                    return
                elif choice == '5':
                    print("Goodbye!")
                    return
                else:
                    print("Invalid choice. Please select 1-5.")
        else:
            print("No LICENSE file found and no configuration exists.")
            print("What would you like to do?\n")
            print("1. Show help and usage information")
            print("2. Setup configuration for this project")
            print("3. Exit")
            
            while True:
                choice = input("\nSelect an option (1-3): ").strip()
                if choice == '1':
                    show_help()
                    return
                elif choice == '2':
                    interactive_setup()
                    return
                elif choice == '3':
                    print("Goodbye!")
                    return
                else:
                    print("Invalid choice. Please select 1-3.")
    
    parser = argparse.ArgumentParser(description="Add GPL license headers to source files")
    parser.add_argument("--config", "-c", default="license_config.yml", 
                      help="Configuration file path")
    parser.add_argument("--force", "-f", action="store_true",
                      help="Force overwrite existing headers")
    parser.add_argument("--dry-run", "-n", action="store_true",
                      help="Show what would be done without making changes")
    parser.add_argument("--file", help="Process specific file")
    parser.add_argument("--init", action="store_true",
                      help="Create configuration template")
    parser.add_argument("--setup", action="store_true",
                      help="Interactive project setup")
    
    args = parser.parse_args()
    
    if args.setup:
        interactive_setup()
        return
    
    tool = LicenseHeaderTool(args.config)
    
    if args.init:
        tool.create_config_template()
        return
    
    if not tool.config:
        print("No configuration available. Run with --setup to configure the tool.")
        return
    
    if args.file:
        if tool.process_file(args.file, args.force):
            print(f"Successfully processed {args.file}")
        else:
            print(f"Failed to process {args.file}")
    else:
        tool.process_all(args.force, args.dry_run)

if __name__ == "__main__":
    main()