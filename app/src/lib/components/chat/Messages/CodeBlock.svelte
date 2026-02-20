<script lang="ts">
	import mermaid from 'mermaid';

	import { v4 as uuidv4 } from 'uuid';

	import { getContext, onMount, tick, onDestroy } from 'svelte';
	import { copyToClipboard } from '$lib/utils';

	import 'highlight.js/styles/github-dark.min.css';

	import PyodideWorker from '$lib/workers/pyodide.worker?worker';
	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import SvgPanZoom from '$lib/components/common/SVGPanZoom.svelte';
	import { config } from '$lib/stores';
	import { executeCode } from '$lib/apis/utils';
	import { toast } from 'svelte-sonner';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronUpDown from '$lib/components/icons/ChevronUpDown.svelte';
	import CommandLine from '$lib/components/icons/CommandLine.svelte';
	import Cube from '$lib/components/icons/Cube.svelte';

	const i18n = getContext('i18n');

	export let id = '';

	export let onSave = (e) => {};
	export let onUpdate = (e) => {};
	export let onPreview = (e) => {};

	export let save = false;
	export let run = true;
	export let preview = false;
	export let collapsed = false;

	export let token;
	export let lang = '';
	export let code = '';
	export let attributes = {};

	export let className = 'my-2';
	export let editorClassName = '';
	export let stickyButtonsClassName = 'top-8';

	let pyodideWorker = null;

	let _code = '';
	$: if (code) {
		updateCode();
	}

	const updateCode = () => {
		_code = code;
	};

	let _token = null;

	let mermaidHtml = null;

	let highlightedCode = null;
	let executing = false;

	let stdout = null;
	let stderr = null;
	let result = null;
	let files = null;

	let copied = false;
	let saved = false;

	const collapseCodeBlock = () => {
		collapsed = !collapsed;
	};

	const saveCode = () => {
		saved = true;

		code = _code;
		onSave(code);

		setTimeout(() => {
			saved = false;
		}, 1000);
	};

	const copyCode = async () => {
		copied = true;
		await copyToClipboard(code);

		setTimeout(() => {
			copied = false;
		}, 1000);
	};

	const previewCode = () => {
		onPreview(code);
	};

	const checkPythonCode = (str) => {
		// Check if the string contains typical Python syntax characters
		const pythonSyntax = [
			'def ',
			'else:',
			'elif ',
			'try:',
			'except:',
			'finally:',
			'yield ',
			'lambda ',
			'assert ',
			'nonlocal ',
			'del ',
			'True',
			'False',
			'None',
			' and ',
			' or ',
			' not ',
			' in ',
			' is ',
			' with '
		];

		for (let syntax of pythonSyntax) {
			if (str.includes(syntax)) {
				return true;
			}
		}

		// If none of the above conditions met, it's probably not Python code
		return false;
	};

	const executePython = async (code) => {
		result = null;
		stdout = null;
		stderr = null;

		executing = true;

		if ($config?.code?.engine === 'jupyter') {
			const output = await executeCode(localStorage.token, code).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (output) {
				if (output['stdout']) {
					stdout = output['stdout'];
					const stdoutLines = stdout.split('\n');

					for (const [idx, line] of stdoutLines.entries()) {
						if (line.startsWith('data:image/png;base64')) {
							if (files) {
								files.push({
									type: 'image/png',
									data: line
								});
							} else {
								files = [
									{
										type: 'image/png',
										data: line
									}
								];
							}

							if (stdout.startsWith(`${line}\n`)) {
								stdout = stdout.replace(`${line}\n`, ``);
							} else if (stdout.startsWith(`${line}`)) {
								stdout = stdout.replace(`${line}`, ``);
							}
						}
					}
				}

				if (output['result']) {
					result = output['result'];
					const resultLines = result.split('\n');

					for (const [idx, line] of resultLines.entries()) {
						if (line.startsWith('data:image/png;base64')) {
							if (files) {
								files.push({
									type: 'image/png',
									data: line
								});
							} else {
								files = [
									{
										type: 'image/png',
										data: line
									}
								];
							}

							if (result.startsWith(`${line}\n`)) {
								result = result.replace(`${line}\n`, ``);
							} else if (result.startsWith(`${line}`)) {
								result = result.replace(`${line}`, ``);
							}
						}
					}
				}

				output['stderr'] && (stderr = output['stderr']);
			}

			executing = false;
		} else {
			executePythonAsWorker(code);
		}
	};

	const executePythonAsWorker = async (code) => {
		let packages = [
			code.includes('requests') ? 'requests' : null,
			code.includes('bs4') ? 'beautifulsoup4' : null,
			code.includes('numpy') ? 'numpy' : null,
			code.includes('pandas') ? 'pandas' : null,
			code.includes('sklearn') ? 'scikit-learn' : null,
			code.includes('scipy') ? 'scipy' : null,
			code.includes('re') ? 'regex' : null,
			code.includes('seaborn') ? 'seaborn' : null,
			code.includes('sympy') ? 'sympy' : null,
			code.includes('tiktoken') ? 'tiktoken' : null,
			code.includes('matplotlib') ? 'matplotlib' : null,
			code.includes('pytz') ? 'pytz' : null,
			code.includes('openai') ? 'openai' : null
		].filter(Boolean);

		console.log(packages);

		pyodideWorker = new PyodideWorker();

		pyodideWorker.postMessage({
			id: id,
			code: code,
			packages: packages
		});

		setTimeout(() => {
			if (executing) {
				executing = false;
				stderr = 'Execution Time Limit Exceeded';
				pyodideWorker.terminate();
			}
		}, 60000);

		pyodideWorker.onmessage = (event) => {
			console.log('pyodideWorker.onmessage', event);
			const { id, ...data } = event.data;

			console.log(id, data);

			if (data['stdout']) {
				stdout = data['stdout'];
				const stdoutLines = stdout.split('\n');

				for (const [idx, line] of stdoutLines.entries()) {
					if (line.startsWith('data:image/png;base64')) {
						if (files) {
							files.push({
								type: 'image/png',
								data: line
							});
						} else {
							files = [
								{
									type: 'image/png',
									data: line
								}
							];
						}

						if (stdout.startsWith(`${line}\n`)) {
							stdout = stdout.replace(`${line}\n`, ``);
						} else if (stdout.startsWith(`${line}`)) {
							stdout = stdout.replace(`${line}`, ``);
						}
					}
				}
			}

			if (data['result']) {
				result = data['result'];
				const resultLines = result.split('\n');

				for (const [idx, line] of resultLines.entries()) {
					if (line.startsWith('data:image/png;base64')) {
						if (files) {
							files.push({
								type: 'image/png',
								data: line
							});
						} else {
							files = [
								{
									type: 'image/png',
									data: line
								}
							];
						}

						if (result.startsWith(`${line}\n`)) {
							result = result.replace(`${line}\n`, ``);
						} else if (result.startsWith(`${line}`)) {
							result = result.replace(`${line}`, ``);
						}
					}
				}
			}

			data['stderr'] && (stderr = data['stderr']);
			data['result'] && (result = data['result']);

			executing = false;
		};

		pyodideWorker.onerror = (event) => {
			console.log('pyodideWorker.onerror', event);
			executing = false;
		};
	};

	let debounceTimeout;

	const drawMermaidDiagram = async () => {
		try {
			if (await mermaid.parse(code)) {
				const { svg } = await mermaid.render(`mermaid-${uuidv4()}`, code);
				mermaidHtml = svg;
			}
		} catch (error) {
			console.log('Error:', error);
		}
	};

	const render = async () => {
		if (lang === 'mermaid' && (token?.raw ?? '').slice(-4).includes('```')) {
			(async () => {
				await drawMermaidDiagram();
			})();
		}

		onUpdate(token);
	};

	$: if (token) {
		if (JSON.stringify(token) !== JSON.stringify(_token)) {
			_token = token;
		}
	}

	$: if (_token) {
		render();
	}

	$: if (attributes) {
		onAttributesUpdate();
	}

	const onAttributesUpdate = () => {
		if (attributes?.output) {
			// Create a helper function to unescape HTML entities
			const unescapeHtml = (html) => {
				const textArea = document.createElement('textarea');
				textArea.innerHTML = html;
				return textArea.value;
			};

			try {
				// Unescape the HTML-encoded string
				const unescapedOutput = unescapeHtml(attributes.output);

				// Parse the unescaped string into JSON
				const output = JSON.parse(unescapedOutput);

				// Assign the parsed values to variables
				stdout = output.stdout;
				stderr = output.stderr;
				result = output.result;
			} catch (error) {
				console.error('Error:', error);
			}
		}
	};

	onMount(async () => {
		if (token) {
			onUpdate(token);
		}

		if (document.documentElement.classList.contains('dark')) {
			mermaid.initialize({
				startOnLoad: true,
				theme: 'dark',
				securityLevel: 'loose'
			});
		} else {
			mermaid.initialize({
				startOnLoad: true,
				theme: 'default',
				securityLevel: 'loose'
			});
		}
	});

	onDestroy(() => {
		if (pyodideWorker) {
			pyodideWorker.terminate();
		}
	});
</script>

<div>
	<div style="--pos:relative; --d:flex; --fd:column; --radius:0.5rem"
	class="{className}" dir="ltr">
		{#if lang === 'mermaid'}
			{#if mermaidHtml}
				<SvgPanZoom
					className=" border border-gray-100 dark:border-gray-850 rounded-lg max-h-fit overflow-hidden"
					svg={mermaidHtml}
					content={_token.text}
				/>
			{:else}
				<pre class="mermaid">{code}</pre>
			{/if}
		{:else}
			<div style="--pos:absolute; --pl:1rem; --py:0.375rem; --size:0.75rem; --weight:500; --dark-c:#fff"
	class="text-text-300">
				{lang}
			</div>

			<div
				style="--pos:sticky; --mb:0.25rem; --py:0.25rem; --pr:0.625rem; --d:flex; --ai:center; --jc:flex-end; --z:10; --size:0.75rem; --c:#000; --dark-c:#fff"
	class="{stickyButtonsClassName}"
			>
				<div style="--d:flex; --ai:center; --g:0.125rem; --translatey:1px">
					<button
						style="--d:flex; --g:0.25rem; --ai:center; --bs:none; --bgc:var(--color-gray-50, #f9f9f9); --hvr-bgc:var(--color-gray-100, #ececec); --dark-bgc:var(--color-gray-850, #262626); --hvr-dark-bgc:var(--color-gray-800, #333); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.375rem; --px:0.375rem; --py:0.125rem"
	class="bg-none"
						on:click={collapseCodeBlock}
					>
						<div style="--translatey:-0.5px">
							<ChevronUpDown className="size-3" />
						</div>

						<div>
							{collapsed ? $i18n.t('Expand') : $i18n.t('Collapse')}
						</div>
					</button>

					{#if preview && ['html', 'svg'].includes(lang)}
						<button
							style="--d:flex; --g:0.25rem; --ai:center; --bs:none; --bgc:var(--color-gray-50, #f9f9f9); --hvr-bgc:var(--color-gray-100, #ececec); --dark-bgc:var(--color-gray-850, #262626); --hvr-dark-bgc:var(--color-gray-800, #333); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.375rem; --px:0.375rem; --py:0.125rem"
	class="run-code-button bg-none"
							on:click={previewCode}
						>
							<div style="--translatey:-0.5px">
								<Cube className="size-3" />
							</div>

							<div>
								{$i18n.t('Preview')}
							</div>
						</button>
					{/if}

					{#if ($config?.features?.enable_code_execution ?? true) && (lang.toLowerCase() === 'python' || lang.toLowerCase() === 'py' || (lang === '' && checkPythonCode(code)))}
						{#if executing}
							<div style="--bs:none; --p:0.25rem; --cur:not-allowed"
	class="run-code-button bg-none">
								{$i18n.t('Running')}
							</div>
						{:else if run}
							<button
								style="--d:flex; --g:0.25rem; --ai:center; --bs:none; --bgc:var(--color-gray-50, #f9f9f9); --hvr-bgc:var(--color-gray-100, #ececec); --dark-bgc:var(--color-gray-850, #262626); --hvr-dark-bgc:var(--color-gray-800, #333); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.375rem; --px:0.375rem; --py:0.125rem"
	class="run-code-button bg-none"
								on:click={async () => {
									code = _code;
									await tick();
									executePython(code);
								}}
							>
								<div style="--translatey:-0.5px">
									<CommandLine className="size-3" />
								</div>

								<div>
									{$i18n.t('Run')}
								</div>
							</button>
						{/if}
					{/if}

					{#if save}
						<button
							style="--bs:none; --bgc:var(--color-gray-50, #f9f9f9); --hvr-bgc:var(--color-gray-100, #ececec); --dark-bgc:var(--color-gray-850, #262626); --hvr-dark-bgc:var(--color-gray-800, #333); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.375rem; --px:0.375rem; --py:0.125rem"
	class="save-code-button bg-none"
							on:click={saveCode}
						>
							{saved ? $i18n.t('Saved') : $i18n.t('Save')}
						</button>
					{/if}

					<button
						style="--bs:none; --bgc:var(--color-gray-50, #f9f9f9); --hvr-bgc:var(--color-gray-100, #ececec); --dark-bgc:var(--color-gray-850, #262626); --hvr-dark-bgc:var(--color-gray-800, #333); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.375rem; --px:0.375rem; --py:0.125rem"
	class="copy-code-button bg-none"
						on:click={copyCode}>{copied ? $i18n.t('Copied') : $i18n.t('Copy')}</button
					>
				</div>
			</div>

			<div
				style="--btlr:0.5rem; --btrr:0.5rem; --mt:-2rem; --of:hidden"
	class="language- {lang} {editorClassName
					? editorClassName
					: executing || stdout || stderr || result
						? ''
						: 'rounded-b-lg'}"
			>
				<div style="--pt:1.75rem; --bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:var(--color-gray-850, #262626)"></div>

				{#if !collapsed}
					<CodeEditor
						value={code}
						{id}
						{lang}
						onSave={() => {
							saveCode();
						}}
						onChange={(value) => {
							_code = value;
						}}
					/>
				{:else}
					<div
						style="--bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:#000; --dark-c:#fff; --pt:0.5rem;  --px:1rem; --d:flex; --fd:column; --g:0.5rem; --size:0.75rem"
	class="rounded-b-lg!"
					>
						<span style="--c:var(--color-gray-500, #9b9b9b); font-style:italic">
							{$i18n.t('{{COUNT}} hidden lines', {
								COUNT: code.split('\n').length
							})}
						</span>
					</div>
				{/if}
			</div>

			{#if !collapsed}
				<div
					id="plt-canvas-{id}"
					style="--bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:#202123; --dark-c:#fff; --maxw:100%; --ofx:auto"
	class="scrollbar-hidden"
				/>

				{#if executing || stdout || stderr || result || files}
					<div
						style="--bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:#202123; --dark-c:#fff; --py:1rem; --px:1rem; --d:flex; --fd:column; --g:0.5rem"
	class="rounded-b-lg!"
					>
						{#if executing}
							<div class=" ">
								<div style="--c:var(--color-gray-500, #9b9b9b); --size:0.75rem; --mb:0.25rem">STDOUT/STDERR</div>
								<div style="--size:0.875rem">Running...</div>
							</div>
						{:else}
							{#if stdout || stderr}
								<div class=" ">
									<div style="--c:var(--color-gray-500, #9b9b9b); --size:0.75rem; --mb:0.25rem">STDOUT/STDERR</div>
									<div
										style="--size:0.875rem; --ofy:auto"
	class="{stdout?.split('\n')?.length > 100
											? `max-h-96`
											: ''}"
									>
										{stdout || stderr}
									</div>
								</div>
							{/if}
							{#if result || files}
								<div class=" ">
									<div style="--c:var(--color-gray-500, #9b9b9b); --size:0.75rem; --mb:0.25rem">RESULT</div>
									{#if result}
										<div style="--size:0.875rem">{`${JSON.stringify(result)}`}</div>
									{/if}
									{#if files}
										<div style="--d:flex; --fd:column; --g:0.5rem">
											{#each files as file}
												{#if file.type.startsWith('image')}
													<img src={file.data} alt="Output" style="--w:100%; --maxw:36rem" />
												{/if}
											{/each}
										</div>
									{/if}
								</div>
							{/if}
						{/if}
					</div>
				{/if}
			{/if}
		{/if}
	</div>
</div>
