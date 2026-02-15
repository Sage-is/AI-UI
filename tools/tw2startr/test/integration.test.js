import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { parseElements } from '../src/parser/svelte-parser.js';
import { processContent } from '../src/transformer/partial-handler.js';
import { replaceTag } from '../src/parser/svelte-parser.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

describe('Integration: simple.svelte', () => {
  it('converts simple fixture', () => {
    const content = fs.readFileSync(path.join(__dirname, 'fixtures/simple.svelte'), 'utf8');
    const { newContent, stats } = processContent(content, parseElements, replaceTag);

    expect(stats.classesConverted).toBeGreaterThan(0);
    expect(newContent).toContain('style=');
    expect(newContent).toContain('--d:flex');
    expect(newContent).toContain('--ai:center');
    expect(newContent).toContain('--g:0.5rem');
    // Should not contain converted classes in class attribute anymore
    expect(newContent).not.toMatch(/class="[^"]*\bflex\b[^"]*"/);
  });
});

describe('Integration: existing-style.svelte', () => {
  it('merges into existing style attributes', () => {
    const content = fs.readFileSync(path.join(__dirname, 'fixtures/existing-style.svelte'), 'utf8');
    const { newContent, stats } = processContent(content, parseElements, replaceTag);

    expect(stats.classesConverted).toBeGreaterThan(0);
    // Should keep existing startr.style properties
    expect(newContent).toContain('--d:flex');
    expect(newContent).toContain('--fd:column');
    // Should add new conversions
    expect(newContent).toContain('--ai:center');
  });
});

describe('Integration: complex-conditionals.svelte', () => {
  it('preserves dynamic expressions while converting static classes', () => {
    const content = fs.readFileSync(path.join(__dirname, 'fixtures/complex-conditionals.svelte'), 'utf8');
    const { newContent, stats } = processContent(content, parseElements, replaceTag);

    expect(stats.classesConverted).toBeGreaterThan(0);
    // Dynamic expressions should be preserved
    expect(newContent).toContain('isActive');
    expect(newContent).toContain('size ===');
    // Static classes should be converted
    expect(newContent).toContain('--d:flex');
    expect(newContent).toContain('--radius:0.5rem');
    expect(newContent).toContain('--cur:pointer');
  });
});

describe('Integration: mixed-responsive.svelte', () => {
  it('handles responsive prefixes', () => {
    const content = fs.readFileSync(path.join(__dirname, 'fixtures/mixed-responsive.svelte'), 'utf8');
    const { newContent, stats } = processContent(content, parseElements, replaceTag);

    expect(stats.classesConverted).toBeGreaterThan(0);
    // Should have responsive variants
    expect(newContent).toContain('--fd-md:row');
    expect(newContent).toContain('--d:flex');
  });
});
