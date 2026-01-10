#!/bin/bash
# filepath: scripts/reorganize-for-docker.sh

# Project Reorganization Script for Docker Build Optimization
# Moves files that are copied to /app/ in Dockerfile into a local /app/ folder
# This keeps the project structure clean and organized

set -e  # Exit on any error

echo "🚀 Starting project reorganization for Docker build optimization..."

# Create the app directory if it doesn't exist
mkdir -p app

# Function to move files/folders safely
move_to_app() {
    local source="$1"
    local dest="app/$1"
    
    if [ -e "$source" ]; then
        echo "📁 Moving $source to $dest"
        # Create destination directory if needed
        mkdir -p "$(dirname "$dest")"
        mv "$source" "$dest"
    else
        echo "⚠️  $source not found, skipping..."
    fi
}

echo "📂 Moving folders to app/..."

# Move directories
move_to_app "backend"
move_to_app "cypress"
move_to_app "scripts"
move_to_app "test"
move_to_app "src"

echo "📄 Moving configuration files to app/..."

# Move individual configuration files
move_to_app ".eslintrc.cjs"
move_to_app ".prettierrc"
move_to_app "cypress.config.ts"
move_to_app "hatch_build.py"
move_to_app "i18next-parser.config.ts"
move_to_app "postcss.config.js"
move_to_app "pyproject.toml"
move_to_app "svelte.config.js"
move_to_app "tailwind.config.js"
move_to_app "tsconfig.json"
move_to_app "vite.config.ts"
move_to_app "CHANGELOG.md"

echo "📋 Creating symbolic links for development convenience..."

# Create symlinks back to root for common development files
# This maintains developer experience while keeping files organized
for file in package.json package-lock.json bun.lockb Makefile; do
    if [ -e "app/$file" ]; then
        ln -sf "app/$file" "$file"
        echo "🔗 Created symlink: $file → app/$file"
    fi
done

echo "📝 Updating .gitignore to handle new structure..."

# Add entries to .gitignore if they don't exist
if [ -f ".gitignore" ]; then
    # Remove old entries and add new ones
    grep -v "^# Docker app structure" .gitignore > .gitignore.tmp || true
    echo "# Docker app structure" >> .gitignore.tmp
    echo "# Symlinks for development convenience" >> .gitignore.tmp
    mv .gitignore.tmp .gitignore
fi

echo "✅ Project reorganization complete!"
echo ""
echo "📌 Next steps:"
echo "1. Update Dockerfile to use 'COPY app/ /app/' instead of individual COPY commands"
echo "2. Test Docker build with: docker build -t test-build ."
echo "3. Update documentation if needed"
echo "4. Commit changes and update TODO.md"
echo ""
echo "⚡ The reorganized structure:"
echo "   app/"
echo "   ├── backend/"
echo "   ├── cypress/"
echo "   ├── scripts/"
echo "   ├── test/"
echo "   ├── src/"
echo "   └── [configuration files]"