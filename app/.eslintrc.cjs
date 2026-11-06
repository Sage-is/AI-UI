module.exports = {
	root: true,
	// Third-party bundles: their findings are not ours to fix and drown the rest.
	ignorePatterns: ['static/pyodide/', 'static/swagger-ui/', 'backend/sage_is_ai/pages/assets/vendor/'],
	extends: [
		'eslint:recommended',
		'plugin:@typescript-eslint/recommended',
		'plugin:svelte/recommended',
		'plugin:cypress/recommended',
		'prettier'
	],
	parser: '@typescript-eslint/parser',
	plugins: ['@typescript-eslint'],
	parserOptions: {
		sourceType: 'module',
		ecmaVersion: 2020,
		extraFileExtensions: ['.svelte']
	},
	env: {
		browser: true,
		es2017: true,
		node: true
	},
	// No string ever becomes code. Chat events carry text from upstream models
	// and REST clients, so a dynamic-code call runs whatever they send in the
	// top frame (the neutered `execute` arm in Chat.svelte).
	rules: {
		'no-eval': 'error',
		'no-implied-eval': 'error',
		'no-new-func': 'error'
	},
	overrides: [
		{
			files: ['*.svelte'],
			parser: 'svelte-eslint-parser',
			parserOptions: {
				parser: '@typescript-eslint/parser'
			}
		}
	]
};
