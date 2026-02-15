import layoutRules from './layout.js';
import spacingRules from './spacing.js';
import sizingRules from './sizing.js';
import typographyRules from './typography.js';
import colorRules from './colors.js';
import borderRules from './borders.js';
import effectRules from './effects.js';
import transformRules from './transforms.js';

// Combine all rules. Order matters: more specific rules should come first.
// Typography rules before color rules (so text-sm matches font-size, not color).
const allRules = [
  ...layoutRules,
  ...spacingRules,
  ...sizingRules,
  ...typographyRules,
  ...colorRules,
  ...borderRules,
  ...effectRules,
  ...transformRules,
];

export default allRules;
export { layoutRules, spacingRules, sizingRules, typographyRules, colorRules, borderRules, effectRules, transformRules };
