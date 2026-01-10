const fs = require('fs');
const path = require('path');

// Read the clean emoji shortcodes
const shortcodesPath = path.join(process.cwd(), 'app/src/lib/emoji-shortcodes-clean.json');
const emojiToShortcodes = JSON.parse(fs.readFileSync(shortcodesPath, 'utf8'));

// Create a reverse mapping: shortcode -> emoji
const shortcodeToEmoji = {};

for (const [emoji, shortcodes] of Object.entries(emojiToShortcodes)) {
    for (const shortcode of shortcodes) {
        shortcodeToEmoji[shortcode] = emoji;
    }
}

// Now create the ultra-concise format: just the shortcodes as a single string
// We'll separate them with a delimiter that won't appear in shortcodes
const allShortcodes = Object.keys(shortcodeToEmoji).sort().join('|');

// Create the clean mapping files
const conciseMapping = {
    // Single string of all shortcodes separated by |
    shortcodes: allShortcodes,
    // Simple lookup object
    lookup: shortcodeToEmoji
};

// Write the ultra-concise shortcode file
const outputPath = path.join(process.cwd(), 'app/src/lib/emoji-shortcodes-ultra-clean.json');
fs.writeFileSync(outputPath, JSON.stringify(conciseMapping, null, '\t'));

console.log(`Created ultra-clean shortcode mapping with ${Object.keys(shortcodeToEmoji).length} shortcodes`);
console.log('Sample shortcodes:', Object.keys(shortcodeToEmoji).slice(0, 10).join(', '));
console.log('Written to:', outputPath);
