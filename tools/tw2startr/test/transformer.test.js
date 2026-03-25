import { describe, it, expect } from 'vitest';
import { mergeStyles, parseStyleValue } from '../src/transformer/style-merger.js';
import { processElement } from '../src/transformer/partial-handler.js';

describe('Style Merger', () => {
  it('creates style from empty', () => {
    const result = mergeStyles(null, [{ prop: '--d', value: 'flex' }, { prop: '--ai', value: 'center' }]);
    expect(result).toContain('--d:flex');
    expect(result).toContain('--ai:center');
  });

  it('merges into existing style', () => {
    const result = mergeStyles('--d:flex; --fd:column', [{ prop: '--ai', value: 'center' }]);
    expect(result).toContain('--d:flex');
    expect(result).toContain('--fd:column');
    expect(result).toContain('--ai:center');
  });

  it('overrides existing properties', () => {
    const result = mergeStyles('--d:block', [{ prop: '--d', value: 'flex' }]);
    expect(result).toContain('--d:flex');
    expect(result).not.toContain('--d:block');
  });

  it('preserves dynamic Svelte expressions', () => {
    const result = mergeStyles('--d:flex; {isActive ? "--bg:red" : ""}', [{ prop: '--ai', value: 'center' }]);
    expect(result).toContain('--d:flex');
    expect(result).toContain('--ai:center');
    expect(result).toContain('{isActive');
  });
});

describe('Parse Style Value', () => {
  it('parses simple declarations', () => {
    const { staticProps } = parseStyleValue('--d:flex; --ai:center');
    expect(staticProps.get('--d')).toBe('flex');
    expect(staticProps.get('--ai')).toBe('center');
  });

  it('parses mixed with Svelte expressions', () => {
    const { staticProps, segments } = parseStyleValue('--d:flex; {expr}');
    expect(staticProps.get('--d')).toBe('flex');
    expect(segments.some(s => s.type === 'dynamic')).toBe(true);
  });
});
