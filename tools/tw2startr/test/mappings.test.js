import { describe, it, expect } from 'vitest';
import { convertClass } from '../src/transformer/class-converter.js';

describe('Layout mappings', () => {
  it('converts display classes', () => {
    expect(convertClass('flex')).toMatchObject({ converted: true, properties: [{ prop: '--d', value: 'flex' }] });
    expect(convertClass('hidden')).toMatchObject({ converted: true, properties: [{ prop: '--d', value: 'none' }] });
    expect(convertClass('block')).toMatchObject({ converted: true, properties: [{ prop: '--d', value: 'block' }] });
    expect(convertClass('inline-flex')).toMatchObject({ converted: true, properties: [{ prop: '--d', value: 'inline-flex' }] });
    expect(convertClass('grid')).toMatchObject({ converted: true, properties: [{ prop: '--d', value: 'grid' }] });
  });

  it('converts position classes', () => {
    expect(convertClass('relative')).toMatchObject({ converted: true, properties: [{ prop: '--pos', value: 'relative' }] });
    expect(convertClass('absolute')).toMatchObject({ converted: true, properties: [{ prop: '--pos', value: 'absolute' }] });
    expect(convertClass('fixed')).toMatchObject({ converted: true, properties: [{ prop: '--pos', value: 'fixed' }] });
    expect(convertClass('sticky')).toMatchObject({ converted: true, properties: [{ prop: '--pos', value: 'sticky' }] });
  });

  it('converts flex direction', () => {
    expect(convertClass('flex-col')).toMatchObject({ converted: true, properties: [{ prop: '--fd', value: 'column' }] });
    expect(convertClass('flex-row')).toMatchObject({ converted: true, properties: [{ prop: '--fd', value: 'row' }] });
  });

  it('converts flex shorthand', () => {
    expect(convertClass('flex-1')).toMatchObject({ converted: true, properties: [{ prop: '--fx', value: '1 1 0%' }] });
    expect(convertClass('flex-none')).toMatchObject({ converted: true, properties: [{ prop: '--fx', value: 'none' }] });
  });

  it('converts alignment', () => {
    expect(convertClass('items-center')).toMatchObject({ converted: true, properties: [{ prop: '--ai', value: 'center' }] });
    expect(convertClass('justify-between')).toMatchObject({ converted: true, properties: [{ prop: '--jc', value: 'space-between' }] });
    expect(convertClass('self-start')).toMatchObject({ converted: true, properties: [{ prop: '--as', value: 'flex-start' }] });
  });

  it('converts z-index', () => {
    expect(convertClass('z-50')).toMatchObject({ converted: true, properties: [{ prop: '--z', value: '50' }] });
    expect(convertClass('z-0')).toMatchObject({ converted: true, properties: [{ prop: '--z', value: '0' }] });
  });

  it('converts position offsets', () => {
    expect(convertClass('top-0')).toMatchObject({ converted: true, properties: [{ prop: '--top', value: '0' }] });
    expect(convertClass('right-4')).toMatchObject({ converted: true, properties: [{ prop: '--right', value: '1rem' }] });
  });

  it('converts gap', () => {
    expect(convertClass('gap-2')).toMatchObject({ converted: true, properties: [{ prop: '--g', value: '0.5rem' }] });
    expect(convertClass('gap-4')).toMatchObject({ converted: true, properties: [{ prop: '--g', value: '1rem' }] });
  });

  it('converts grow/shrink', () => {
    expect(convertClass('shrink-0')).toMatchObject({ converted: true, properties: [{ prop: '--fs', value: '0' }] });
    expect(convertClass('grow')).toMatchObject({ converted: true, properties: [{ prop: '--fg', value: '1' }] });
  });

  it('converts visibility', () => {
    expect(convertClass('visible')).toMatchObject({ converted: true, properties: [{ prop: '--v', value: 'visible' }] });
    expect(convertClass('invisible')).toMatchObject({ converted: true, properties: [{ prop: '--v', value: 'hidden' }] });
  });
});

describe('Spacing mappings', () => {
  it('converts padding', () => {
    expect(convertClass('p-4')).toMatchObject({ converted: true, properties: [{ prop: '--p', value: '1rem' }] });
    expect(convertClass('px-3.5')).toMatchObject({ converted: true, properties: [{ prop: '--px', value: '0.8rem' }] });
    expect(convertClass('py-2')).toMatchObject({ converted: true, properties: [{ prop: '--py', value: '0.5rem' }] });
    expect(convertClass('pt-0')).toMatchObject({ converted: true, properties: [{ prop: '--pt', value: '0' }] });
  });

  it('converts margin', () => {
    expect(convertClass('m-4')).toMatchObject({ converted: true, properties: [{ prop: '--m', value: '1rem' }] });
    expect(convertClass('mt-2')).toMatchObject({ converted: true, properties: [{ prop: '--mt', value: '0.5rem' }] });
    expect(convertClass('mx-auto')).toMatchObject({ converted: true, properties: [{ prop: '--mx', value: 'auto' }] });
    expect(convertClass('ml-0')).toMatchObject({ converted: true, properties: [{ prop: '--ml', value: '0' }] });
  });

  it('converts negative margin', () => {
    const result = convertClass('-mt-4');
    expect(result.converted).toBe(true);
    expect(result.properties[0].prop).toBe('--mt');
    expect(result.properties[0].value).toMatch(/-1rem/);
  });
});

describe('Sizing mappings', () => {
  it('converts width', () => {
    expect(convertClass('w-full')).toMatchObject({ converted: true, properties: [{ prop: '--w', value: '100%' }] });
    expect(convertClass('w-4')).toMatchObject({ converted: true, properties: [{ prop: '--w', value: '1rem' }] });
    expect(convertClass('w-screen')).toMatchObject({ converted: true, properties: [{ prop: '--w', value: '100vw' }] });
  });

  it('converts height', () => {
    expect(convertClass('h-screen')).toMatchObject({ converted: true, properties: [{ prop: '--h', value: '100vh' }] });
    expect(convertClass('h-full')).toMatchObject({ converted: true, properties: [{ prop: '--h', value: '100%' }] });
  });

  it('converts size (w+h)', () => {
    const result = convertClass('size-4');
    expect(result.converted).toBe(true);
    expect(result.properties).toHaveLength(2);
    expect(result.properties).toContainEqual({ prop: '--w', value: '1rem' });
    expect(result.properties).toContainEqual({ prop: '--h', value: '1rem' });
  });

  it('converts max dimensions', () => {
    expect(convertClass('max-w-lg')).toMatchObject({ converted: true, properties: [{ prop: '--maxw', value: '32rem' }] });
    expect(convertClass('max-h-[22rem]')).toMatchObject({ converted: true, properties: [{ prop: '--maxh', value: '22rem' }] });
  });

  it('converts min dimensions', () => {
    expect(convertClass('min-w-0')).toMatchObject({ converted: true, properties: [{ prop: '--minw', value: '0' }] });
    expect(convertClass('min-h-screen')).toMatchObject({ converted: true, properties: [{ prop: '--minh', value: '100vh' }] });
  });

  it('converts fractions', () => {
    const result = convertClass('w-1/2');
    expect(result.converted).toBe(true);
    expect(result.properties[0].value).toBe('50%');
  });
});

describe('Typography mappings', () => {
  it('converts font size', () => {
    expect(convertClass('text-sm')).toMatchObject({ converted: true, properties: [{ prop: '--size', value: '0.8rem' }] });
    expect(convertClass('text-2xl')).toMatchObject({ converted: true, properties: [{ prop: '--size', value: '1.5rem' }] });
  });

  it('converts font weight', () => {
    expect(convertClass('font-bold')).toMatchObject({ converted: true, properties: [{ prop: '--weight', value: '700' }] });
    expect(convertClass('font-semibold')).toMatchObject({ converted: true, properties: [{ prop: '--weight', value: '600' }] });
    expect(convertClass('font-medium')).toMatchObject({ converted: true, properties: [{ prop: '--weight', value: '500' }] });
  });

  it('converts text alignment', () => {
    expect(convertClass('text-center')).toMatchObject({ converted: true, properties: [{ prop: '--ta', value: 'center' }] });
    expect(convertClass('text-left')).toMatchObject({ converted: true, properties: [{ prop: '--ta', value: 'left' }] });
  });

  it('converts text transform', () => {
    expect(convertClass('uppercase')).toMatchObject({ converted: true, properties: [{ prop: '--tt', value: 'uppercase' }] });
    expect(convertClass('lowercase')).toMatchObject({ converted: true, properties: [{ prop: '--tt', value: 'lowercase' }] });
  });

  it('converts line clamp', () => {
    expect(convertClass('line-clamp-1')).toMatchObject({ converted: true, properties: [{ prop: '--line-clamp', value: '1' }] });
    expect(convertClass('line-clamp-3')).toMatchObject({ converted: true, properties: [{ prop: '--line-clamp', value: '3' }] });
  });

  it('converts whitespace', () => {
    expect(convertClass('whitespace-nowrap')).toMatchObject({ converted: true, properties: [{ prop: '--ws', value: 'nowrap' }] });
  });

  it('converts text decoration', () => {
    expect(convertClass('underline')).toMatchObject({ converted: true, properties: [{ prop: '--td', value: 'underline' }] });
    expect(convertClass('no-underline')).toMatchObject({ converted: true, properties: [{ prop: '--td', value: 'none' }] });
  });
});

describe('Color mappings', () => {
  it('converts background colors', () => {
    expect(convertClass('bg-white')).toMatchObject({ converted: true, properties: [{ prop: '--bgc', value: 'hsl(0 0% 100%)' }] });
    expect(convertClass('bg-gray-850')).toMatchObject({ converted: true, properties: [{ prop: '--bgc', value: 'var(--color-gray-850, hsl(0 0% 15%))' }] });
  });

  it('converts text colors', () => {
    expect(convertClass('text-gray-700')).toMatchObject({ converted: true, properties: [{ prop: '--c', value: 'var(--color-gray-700, hsl(0 0% 31%))' }] });
    expect(convertClass('text-white')).toMatchObject({ converted: true, properties: [{ prop: '--c', value: 'hsl(0 0% 100%)' }] });
  });

  it('converts colors with opacity', () => {
    const result = convertClass('bg-white/50');
    expect(result.converted).toBe(true);
    expect(result.properties[0].prop).toBe('--bgc');
    expect(result.properties[0].value).toMatch(/hsl\(0 0% 100% \/ 0\.5\)/);
  });

  it('converts border colors', () => {
    const result = convertClass('border-gray-200');
    expect(result.converted).toBe(true);
    expect(result.properties[0].prop).toBe('--bc');
  });
});

describe('Border mappings', () => {
  it('converts border shorthand', () => {
    expect(convertClass('border')).toMatchObject({ converted: true, properties: [{ prop: '--b', value: '1px solid' }] });
  });

  it('converts border radius', () => {
    expect(convertClass('rounded-lg')).toMatchObject({ converted: true, properties: [{ prop: '--radius', value: '0.5rem' }] });
    expect(convertClass('rounded-full')).toMatchObject({ converted: true, properties: [{ prop: '--radius', value: '9999px' }] });
    expect(convertClass('rounded')).toMatchObject({ converted: true, properties: [{ prop: '--radius', value: '0.2rem' }] });
  });

  it('converts box shadow', () => {
    expect(convertClass('shadow-md')).toMatchObject({ converted: true, properties: [{ prop: '--shadow', value: '3' }] });
    expect(convertClass('shadow-xl')).toMatchObject({ converted: true, properties: [{ prop: '--shadow', value: '5' }] });
  });
});

describe('Effects mappings', () => {
  it('converts opacity', () => {
    expect(convertClass('opacity-50')).toMatchObject({ converted: true, properties: [{ prop: '--op', value: '0.5' }] });
    expect(convertClass('opacity-75')).toMatchObject({ converted: true, properties: [{ prop: '--op', value: '0.75' }] });
  });

  it('converts cursor', () => {
    expect(convertClass('cursor-pointer')).toMatchObject({ converted: true, properties: [{ prop: '--cur', value: 'pointer' }] });
  });

  it('converts user select', () => {
    expect(convertClass('select-none')).toMatchObject({ converted: true, properties: [{ prop: '--us', value: 'none' }] });
  });

  it('converts object fit', () => {
    expect(convertClass('object-cover')).toMatchObject({ converted: true, properties: [{ prop: '--objf', value: 'cover' }] });
  });

  it('converts overflow', () => {
    expect(convertClass('overflow-hidden')).toMatchObject({ converted: true, properties: [{ prop: '--of', value: 'hidden' }] });
    expect(convertClass('overflow-y-auto')).toMatchObject({ converted: true, properties: [{ prop: '--ofy', value: 'auto' }] });
  });

  it('converts pointer events', () => {
    expect(convertClass('pointer-events-none')).toMatchObject({ converted: true, properties: [{ prop: '--pe', value: 'none' }] });
  });
});

describe('Transform mappings', () => {
  it('converts transition', () => {
    const result = convertClass('transition');
    expect(result.converted).toBe(true);
    expect(result.properties[0].prop).toBe('--tn');
  });

  it('converts duration', () => {
    expect(convertClass('duration-200')).toMatchObject({ converted: true, properties: [{ prop: '--tdn', value: '200ms' }] });
  });
});

describe('Responsive prefixes', () => {
  it('applies responsive suffix', () => {
    expect(convertClass('sm:flex')).toMatchObject({ converted: true, properties: [{ prop: '--d-sm', value: 'flex' }] });
    expect(convertClass('md:hidden')).toMatchObject({ converted: true, properties: [{ prop: '--d-md', value: 'none' }] });
    expect(convertClass('lg:flex-row')).toMatchObject({ converted: true, properties: [{ prop: '--fd-lg', value: 'row' }] });
  });

  it('applies responsive to spacing', () => {
    expect(convertClass('md:p-6')).toMatchObject({ converted: true, properties: [{ prop: '--p-md', value: '1.5rem' }] });
  });
});

describe('Hover state', () => {
  it('converts hover:bg to --hvr-bgc', () => {
    const result = convertClass('hover:bg-gray-100');
    expect(result.converted).toBe(true);
    expect(result.properties[0].prop).toBe('--hvr-bgc');
  });

  it('converts hover:text to --hvr-c', () => {
    const result = convertClass('hover:text-white');
    expect(result.converted).toBe(true);
    expect(result.properties[0].prop).toBe('--hvr-c');
  });
});

describe('Dark mode', () => {
  it('converts dark:bg to --dark-bgc', () => {
    const result = convertClass('dark:bg-gray-800');
    expect(result.converted).toBe(true);
    expect(result.properties[0].prop).toBe('--dark-bgc');
  });

  it('converts dark:text to --dark-c', () => {
    const result = convertClass('dark:text-gray-100');
    expect(result.converted).toBe(true);
    expect(result.properties[0].prop).toBe('--dark-c');
  });
});

describe('Unconvertible classes', () => {
  it('flags focus: prefix as unconvertible', () => {
    const result = convertClass('focus:outline-none');
    expect(result.converted).toBe(false);
    expect(result.reason).toMatch(/unconvertible prefix/);
  });

  it('flags group-hover: as unconvertible', () => {
    const result = convertClass('group-hover:visible');
    expect(result.converted).toBe(false);
  });

  it('flags data-* selectors as unconvertible', () => {
    const result = convertClass('data-[state=checked]:translate-x-3.5');
    expect(result.converted).toBe(false);
  });
});

describe('Arbitrary values', () => {
  it('converts arbitrary spacing', () => {
    expect(convertClass('p-[1.5rem]')).toMatchObject({ converted: true, properties: [{ prop: '--p', value: '1.5rem' }] });
  });

  it('converts arbitrary width', () => {
    expect(convertClass('w-[200px]')).toMatchObject({ converted: true, properties: [{ prop: '--w', value: '200px' }] });
  });

  it('converts arbitrary max-height', () => {
    expect(convertClass('max-h-[22rem]')).toMatchObject({ converted: true, properties: [{ prop: '--maxh', value: '22rem' }] });
  });
});
