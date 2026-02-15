import { describe, it, expect } from 'vitest';
import { extractClassSegments, getStaticClasses } from '../src/parser/class-extractor.js';
import { parseElements } from '../src/parser/svelte-parser.js';

describe('Class Extractor', () => {
  it('extracts static classes', () => {
    const segments = extractClassSegments('flex items-center gap-2');
    expect(segments).toHaveLength(1);
    expect(segments[0].type).toBe('static');
    expect(segments[0].classes).toEqual(['flex', 'items-center', 'gap-2']);
  });

  it('extracts mixed static and dynamic', () => {
    const segments = extractClassSegments('flex {isOpen ? "block" : "hidden"} text-sm');
    expect(segments).toHaveLength(3);
    expect(segments[0]).toEqual({ type: 'static', classes: ['flex'] });
    expect(segments[1].type).toBe('dynamic');
    expect(segments[1].expression).toContain('isOpen');
    expect(segments[2]).toEqual({ type: 'static', classes: ['text-sm'] });
  });

  it('handles leading dynamic expression', () => {
    const segments = extractClassSegments('{someClass} flex');
    expect(segments).toHaveLength(2);
    expect(segments[0].type).toBe('dynamic');
    expect(segments[1]).toEqual({ type: 'static', classes: ['flex'] });
  });

  it('handles nested braces in expressions', () => {
    const segments = extractClassSegments('flex {obj.fn({x: 1})} text-sm');
    expect(segments).toHaveLength(3);
    expect(segments[0].type).toBe('static');
    expect(segments[1].type).toBe('dynamic');
    expect(segments[2].type).toBe('static');
  });

  it('getStaticClasses extracts only static classes', () => {
    const segments = extractClassSegments('flex {dynamic} items-center');
    const statics = getStaticClasses(segments);
    expect(statics).toEqual(['flex', 'items-center']);
  });
});

describe('Svelte Parser', () => {
  it('finds elements with class attributes', () => {
    const content = '<div class="flex items-center">Hello</div>';
    const elements = parseElements(content);
    expect(elements).toHaveLength(1);
    expect(elements[0].classAttr.value).toBe('flex items-center');
    expect(elements[0].tagName).toBe('div');
  });

  it('finds elements with style attributes', () => {
    const content = '<div style="--d:flex" class="items-center">Hello</div>';
    const elements = parseElements(content);
    expect(elements).toHaveLength(1);
    expect(elements[0].styleAttr.value).toBe('--d:flex');
    expect(elements[0].classAttr.value).toBe('items-center');
  });

  it('skips script blocks', () => {
    const content = `<script>
  const cls = "flex items-center";
</script>

<div class="flex">Hello</div>`;
    const elements = parseElements(content);
    expect(elements).toHaveLength(1);
    expect(elements[0].classAttr.value).toBe('flex');
  });

  it('skips style blocks', () => {
    const content = `<div class="flex">Hello</div>

<style>
  .flex { display: flex; }
</style>`;
    const elements = parseElements(content);
    expect(elements).toHaveLength(1);
  });

  it('handles multi-line tags', () => {
    const content = `<button
  class="flex items-center gap-2"
  on:click={handler}
>
  Click
</button>`;
    const elements = parseElements(content);
    expect(elements).toHaveLength(1);
    expect(elements[0].classAttr.value).toBe('flex items-center gap-2');
  });

  it('handles Svelte expressions in class values', () => {
    const content = `<div class="flex {isActive ? 'bg-blue' : 'bg-red'} items-center">Hi</div>`;
    const elements = parseElements(content);
    expect(elements).toHaveLength(1);
    expect(elements[0].classAttr.value).toContain('{isActive');
  });
});
