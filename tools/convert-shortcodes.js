const fs = require('fs');
const path = require('path');

// Helper function to convert hex code to emoji
function hexToEmoji(hex) {
    // Handle complex sequences with multiple parts
    const parts = hex.split('-');
    let result = '';
    
    for (const part of parts) {
        if (part === 'FE0F' || part === '200D') {
            // Variation selectors and zero-width joiners
            if (part === 'FE0F') {
                result += '\uFE0F';
            } else if (part === '200D') {
                result += '\u200D';
            }
        } else if (part === '20E3') {
            // Combining enclosing keycap
            result += '\u20E3';
        } else {
            // Regular unicode codepoint
            const codePoint = parseInt(part, 16);
            result += String.fromCodePoint(codePoint);
        }
    }
    
    return result;
}

// Read the original shortcodes file
const shortcodesPath = path.join(process.cwd(), 'app/src/lib/emoji-shortcodes.json');
const shortcodes = JSON.parse(fs.readFileSync(shortcodesPath, 'utf8'));

// Convert to emoji-based mapping
const emojiToShortcodes = {};

for (const [hex, shortcode] of Object.entries(shortcodes)) {
    try {
        const emoji = hexToEmoji(hex);
        
        if (Array.isArray(shortcode)) {
            emojiToShortcodes[emoji] = shortcode;
        } else {
            emojiToShortcodes[emoji] = [shortcode];
        }
    } catch (error) {
        console.warn(`Failed to convert hex ${hex} to emoji:`, error.message);
    }
}

// Write the new emoji-based shortcodes file
const outputPath = path.join(process.cwd(), 'app/src/lib/emoji-shortcodes-clean.json');
fs.writeFileSync(outputPath, JSON.stringify(emojiToShortcodes, null, '\t'));

console.log(`Converted ${Object.keys(shortcodes).length} hex codes to ${Object.keys(emojiToShortcodes).length} emoji mappings`);
console.log('Written to:', outputPath);
