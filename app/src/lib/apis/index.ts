import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
import { convertOpenApiToToolPayload } from '$lib/utils';
import { getOpenAIModelsDirect } from './openai';

import { parse } from 'yaml';
import { toast } from 'svelte-sonner';

async function api(url: string, method = 'GET', body?: any, context = '') {
	try {
		console.log(`[Main API] ${context}: Calling ${method} ${url}`);

		const res = await fetch(url, {
			method,
			credentials: 'include',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json'
			},
			...(body && { body: JSON.stringify(body) })
		});

		console.log(`[Main API] ${context}: Response status ${res.status} ${res.statusText}`);

		if (!res.ok) {
			const responseText = await res.text();
			console.error(`[Main API] ${context}: Error response body:`, responseText);

			try {
				const errorJson = JSON.parse(responseText);
				throw errorJson;
			} catch (parseError) {
				console.error(`[Main API] ${context}: Response is not valid JSON, got HTML/text instead:`, responseText.substring(0, 200) + '...');
				throw new Error(`Server returned HTML instead of JSON for ${context}. Status: ${res.status}. Response starts with: ${responseText.substring(0, 100)}...`);
			}
		}

		const responseText = await res.text();
		console.log(`[Main API] ${context}: Response body:`, responseText.substring(0, 200) + (responseText.length > 200 ? '...' : ''));

		try {
			return JSON.parse(responseText);
		} catch (parseError) {
			console.error(`[Main API] ${context}: Success response is not valid JSON:`, responseText.substring(0, 200) + '...');
			throw new Error(`Server returned HTML instead of JSON for ${context}. Expected JSON but got: ${responseText.substring(0, 100)}...`);
		}
	} catch (err: any) {
		console.error(`[Main API] ${context}: Error details:`, err);
		throw err.detail || err.message || err;
	}
}

export const getModels = async (
	connections: Record<string, any> | null = null,
	base: boolean = false,
	refresh: boolean = false
) => {
	const searchParams = new URLSearchParams();
	if (refresh) {
		searchParams.append('refresh', 'true');
	}

	let error = null;
	const res = await fetch(
		`${WEBUI_BASE_URL}/api/models${base ? '/base' : ''}?${searchParams.toString()}`,
		{
			method: 'GET',
			credentials: 'include',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json'
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	let models = res?.data ?? [];

	if (connections && !base) {
		let localModels: any[] = [];

		if (connections) {
			const OPENAI_API_BASE_URLS = connections.OPENAI_API_BASE_URLS;
			const OPENAI_API_KEYS = connections.OPENAI_API_KEYS;
			const OPENAI_API_CONFIGS = connections.OPENAI_API_CONFIGS;

			const requests = [];
			for (const idx in OPENAI_API_BASE_URLS) {
				const url = OPENAI_API_BASE_URLS[idx];

				if (idx.toString() in OPENAI_API_CONFIGS) {
					const apiConfig = OPENAI_API_CONFIGS[idx.toString()] ?? {};

					const enable = apiConfig?.enable ?? true;
					const modelIds = apiConfig?.model_ids ?? [];

					if (enable) {
						if (modelIds.length > 0) {
							const modelList = {
								object: 'list',
								data: modelIds.map((modelId) => ({
									id: modelId,
									name: modelId,
									owned_by: 'openai',
									openai: { id: modelId },
									urlIdx: idx
								}))
							};

							requests.push(
								(async () => {
									return modelList;
								})()
							);
						} else {
							requests.push(
								(async () => {
									return await getOpenAIModelsDirect(url, OPENAI_API_KEYS[idx])
										.then((res) => {
											return res;
										})
										.catch((err) => {
											return {
												object: 'list',
												data: [],
												urlIdx: idx
											};
										});
								})()
							);
						}
					} else {
						requests.push(
							(async () => {
								return {
									object: 'list',
									data: [],
									urlIdx: idx
								};
							})()
						);
					}
				}
			}

			const responses = await Promise.all(requests);

			for (const idx in responses) {
				const response = responses[idx];
				const apiConfig = OPENAI_API_CONFIGS[idx.toString()] ?? {};

				let models = Array.isArray(response) ? response : (response?.data ?? []);
				models = models.map((model) => ({ ...model, openai: { id: model.id }, urlIdx: idx }));

				const prefixId = apiConfig.prefix_id;
				if (prefixId) {
					for (const model of models) {
						model.id = `${prefixId}.${model.id}`;
					}
				}

				const tags = apiConfig.tags;
				if (tags) {
					for (const model of models) {
						model.tags = tags;
					}
				}

				localModels = localModels.concat(models);
			}
		}

		models = models.concat(
			localModels.map((model) => ({
				...model,
				name: model?.name ?? model?.id,
				direct: true
			}))
		);

		// Remove duplicates
		const modelsMap = {};
		for (const model of models) {
			modelsMap[model.id] = model;
		}

		models = Object.values(modelsMap);
	}

	return models;
};

type ChatCompletedForm = {
	model: string;
	messages: string[];
	chat_id: string;
	session_id: string;
};

export const chatCompleted = async (body: ChatCompletedForm) =>
	api(`${WEBUI_BASE_URL}/api/chat/completed`, 'POST', body, 'chatCompleted');

type ChatActionForm = {
	model: string;
	messages: string[];
	chat_id: string;
};

export const chatAction = async (action_id: string, body: ChatActionForm) =>
	api(`${WEBUI_BASE_URL}/api/chat/actions/${action_id}`, 'POST', body, `chatAction(${action_id})`);

export const stopTask = async (id: string) =>
	api(`${WEBUI_BASE_URL}/api/tasks/stop/${id}`, 'POST', null, `stopTask(${id})`);

export const getTaskIdsByChatId = async (chat_id: string) =>
	api(`${WEBUI_BASE_URL}/api/tasks/chat/${chat_id}`, 'GET', null, `getTaskIdsByChatId(${chat_id})`);

export const getToolServerData = async (url: string) => {
	let error = null;

	const res = await fetch(`${url}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
		}
	})
		.then(async (res) => {
			// Check if URL ends with .yaml or .yml to determine format
			if (url.toLowerCase().endsWith('.yaml') || url.toLowerCase().endsWith('.yml')) {
				if (!res.ok) throw await res.text();
				const text = await res.text();
				return parse(text);
			} else {
				if (!res.ok) throw await res.json();
				return res.json();
			}
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	const data = {
		openapi: res,
		info: res.info,
		specs: convertOpenApiToToolPayload(res)
	};

	console.log(data);
	return data;
};

export const getToolServersData = async (i18n: any, servers: any[]) => {
	return (
		await Promise.all(
			servers
				.filter((server) => server?.config?.enable)
				.map(async (server) => {
					const data = await getToolServerData(
						(server?.path ?? '').includes('://')
							? server?.path
							: `${server?.url}${(server?.path ?? '').startsWith('/') ? '' : '/'}${server?.path}`
					).catch((err) => {
						toast.error(
							i18n.t(`Failed to connect to {{URL}} OpenAPI tool server`, {
								URL: (server?.path ?? '').includes('://')
									? server?.path
									: `${server?.url}${(server?.path ?? '').startsWith('/') ? '' : '/'}${server?.path}`
							})
						);
						return null;
					});

					if (data) {
						const { openapi, info, specs } = data;
						return {
							url: server?.url,
							openapi: openapi,
							info: info,
							specs: specs
						};
					}
				})
		)
	).filter((server) => server);
};

export const executeToolServer = async (
	token: string,
	url: string,
	name: string,
	params: Record<string, any>,
	serverData?: { openapi: any; info: any; specs: any }
) => {
	let error = null;

	try {
		if (!serverData) {
			throw new Error('Tool server data not provided');
		}

		// Find the matching operationId in the OpenAPI spec
		const matchingRoute = Object.entries(serverData.openapi.paths).find(([_, methods]) =>
			Object.entries(methods as any).some(([__, operation]: any) => operation.operationId === name)
		);

		if (!matchingRoute) {
			throw new Error(`No matching route found for operationId: ${name}`);
		}

		const [routePath, methods] = matchingRoute;

		const methodEntry = Object.entries(methods as any).find(
			([_, operation]: any) => operation.operationId === name
		);

		if (!methodEntry) {
			throw new Error(`No matching method found for operationId: ${name}`);
		}

		const [httpMethod, operation]: [string, any] = methodEntry;

		// Split parameters by type
		const pathParams: Record<string, any> = {};
		const queryParams: Record<string, any> = {};
		let bodyParams: any = {};

		if (operation.parameters) {
			operation.parameters.forEach((param: any) => {
				const paramName = param.name;
				const paramIn = param.in;
				if (params.hasOwnProperty(paramName)) {
					if (paramIn === 'path') {
						pathParams[paramName] = params[paramName];
					} else if (paramIn === 'query') {
						queryParams[paramName] = params[paramName];
					}
				}
			});
		}

		let finalUrl = `${url}${routePath}`;

		// Replace path parameters (`{param}`)
		Object.entries(pathParams).forEach(([key, value]) => {
			finalUrl = finalUrl.replace(new RegExp(`{${key}}`, 'g'), encodeURIComponent(value));
		});

		// Append query parameters to URL if any
		if (Object.keys(queryParams).length > 0) {
			const queryString = new URLSearchParams(
				Object.entries(queryParams).map(([k, v]) => [k, String(v)])
			).toString();
			finalUrl += `?${queryString}`;
		}

		// Handle requestBody composite
		if (operation.requestBody && operation.requestBody.content) {
			const contentType = Object.keys(operation.requestBody.content)[0];
			if (params !== undefined) {
				bodyParams = params;
			} else {
				// Optional: Fallback or explicit error if body is expected but not provided
				throw new Error(`Request body expected for operation '${name}' but none found.`);
			}
		}

		// Prepare headers and request options
		const headers: Record<string, string> = {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		};

		let requestOptions: RequestInit = {
			method: httpMethod.toUpperCase(),
			headers
		};

		if (['post', 'put', 'patch'].includes(httpMethod.toLowerCase()) && operation.requestBody) {
			requestOptions.body = JSON.stringify(bodyParams);
		}

		const res = await fetch(finalUrl, requestOptions);
		if (!res.ok) {
			const resText = await res.text();
			throw new Error(`HTTP error! Status: ${res.status}. Message: ${resText}`);
		}

		return await res.json();
	} catch (err: any) {
		error = err.message;
		console.error('API Request Error:', error);
		return { error };
	}
};

export const getTaskConfig = async () =>
	api(`${WEBUI_BASE_URL}/api/v1/tasks/config`, 'GET', null, 'getTaskConfig');

export const updateTaskConfig = async (config: object) =>
	api(`${WEBUI_BASE_URL}/api/v1/tasks/config/update`, 'POST', config, 'updateTaskConfig');

export const generateTitle = async (
	model: string,
	messages: object[],
	chat_id?: string
) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/title/completions`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			model: model,
			messages: messages,
			...(chat_id && { chat_id: chat_id })
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	try {
		// Step 1: Safely extract the response string
		const response = res?.choices[0]?.message?.content ?? '';

		// Step 2: Attempt to fix common JSON format issues like single quotes
		const sanitizedResponse = response.replace(/['‘’`]/g, '"'); // Convert single quotes to double quotes for valid JSON

		// Step 3: Find the relevant JSON block within the response
		const jsonStartIndex = sanitizedResponse.indexOf('{');
		const jsonEndIndex = sanitizedResponse.lastIndexOf('}');

		// Step 4: Check if we found a valid JSON block (with both `{` and `}`)
		if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
			const jsonResponse = sanitizedResponse.substring(jsonStartIndex, jsonEndIndex + 1);

			// Step 5: Parse the JSON block
			const parsed = JSON.parse(jsonResponse);

			// Step 6: If there's a "tags" key, return the tags array; otherwise, return an empty array
			if (parsed && parsed.title) {
				return parsed.title;
			} else {
				return null;
			}
		}

		// If no valid JSON block found, return an empty array
		return null;
	} catch (e) {
		// Catch and safely return empty array on any parsing errors
		console.error('Failed to parse response: ', e);
		return null;
	}
};

export const generateFollowUps = async (
	model: string,
	messages: string,
	chat_id?: string
) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/follow_ups/completions`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			model: model,
			messages: messages,
			...(chat_id && { chat_id: chat_id })
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	try {
		// Step 1: Safely extract the response string
		const response = res?.choices[0]?.message?.content ?? '';

		// Step 2: Attempt to fix common JSON format issues like single quotes
		const sanitizedResponse = response.replace(/['‘’`]/g, '"'); // Convert single quotes to double quotes for valid JSON

		// Step 3: Find the relevant JSON block within the response
		const jsonStartIndex = sanitizedResponse.indexOf('{');
		const jsonEndIndex = sanitizedResponse.lastIndexOf('}');

		// Step 4: Check if we found a valid JSON block (with both `{` and `}`)
		if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
			const jsonResponse = sanitizedResponse.substring(jsonStartIndex, jsonEndIndex + 1);

			// Step 5: Parse the JSON block
			const parsed = JSON.parse(jsonResponse);

			// Step 6: If there's a "follow_ups" key, return the follow_ups array; otherwise, return an empty array
			if (parsed && parsed.follow_ups) {
				return Array.isArray(parsed.follow_ups) ? parsed.follow_ups : [];
			} else {
				return [];
			}
		}

		// If no valid JSON block found, return an empty array
		return [];
	} catch (e) {
		// Catch and safely return empty array on any parsing errors
		console.error('Failed to parse response: ', e);
		return [];
	}
};

export const generateTags = async (
	model: string,
	messages: string,
	chat_id?: string
) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/tags/completions`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			model: model,
			messages: messages,
			...(chat_id && { chat_id: chat_id })
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	try {
		// Step 1: Safely extract the response string
		const response = res?.choices[0]?.message?.content ?? '';

		// Step 2: Attempt to fix common JSON format issues like single quotes
		const sanitizedResponse = response.replace(/['‘’`]/g, '"'); // Convert single quotes to double quotes for valid JSON

		// Step 3: Find the relevant JSON block within the response
		const jsonStartIndex = sanitizedResponse.indexOf('{');
		const jsonEndIndex = sanitizedResponse.lastIndexOf('}');

		// Step 4: Check if we found a valid JSON block (with both `{` and `}`)
		if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
			const jsonResponse = sanitizedResponse.substring(jsonStartIndex, jsonEndIndex + 1);

			// Step 5: Parse the JSON block
			const parsed = JSON.parse(jsonResponse);

			// Step 6: If there's a "tags" key, return the tags array; otherwise, return an empty array
			if (parsed && parsed.tags) {
				return Array.isArray(parsed.tags) ? parsed.tags : [];
			} else {
				return [];
			}
		}

		// If no valid JSON block found, return an empty array
		return [];
	} catch (e) {
		// Catch and safely return empty array on any parsing errors
		console.error('Failed to parse response: ', e);
		return [];
	}
};

export const generateEmoji = async (
	model: string,
	prompt: string,
	chat_id?: string
) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/emoji/completions`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			model: model,
			prompt: prompt,
			...(chat_id && { chat_id: chat_id })
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	const response = res?.choices[0]?.message?.content.replace(/["']/g, '') ?? null;

	if (response) {
		if (/\p{Extended_Pictographic}/u.test(response)) {
			return response.match(/\p{Extended_Pictographic}/gu)[0];
		}
	}

	return null;
};

export const generateQueries = async (
	model: string,
	messages: object[],
	prompt: string,
	type: string = 'web_search'
) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/queries/completions`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			model: model,
			messages: messages,
			prompt: prompt,
			type: type
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	// Step 1: Safely extract the response string
	const response = res?.choices[0]?.message?.content ?? '';

	try {
		const jsonStartIndex = response.indexOf('{');
		const jsonEndIndex = response.lastIndexOf('}');

		if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
			const jsonResponse = response.substring(jsonStartIndex, jsonEndIndex + 1);

			// Step 5: Parse the JSON block
			const parsed = JSON.parse(jsonResponse);

			// Step 6: If there's a "queries" key, return the queries array; otherwise, return an empty array
			if (parsed && parsed.queries) {
				return Array.isArray(parsed.queries) ? parsed.queries : [];
			} else {
				return [];
			}
		}

		// If no valid JSON block found, return response as is
		return [response];
	} catch (e) {
		// Catch and safely return empty array on any parsing errors
		console.error('Failed to parse response: ', e);
		return [response];
	}
};

export const generateAutoCompletion = async (
	model: string,
	prompt: string,
	messages?: object[],
	type: string = 'search query'
) => {
	const controller = new AbortController();
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/auto/completions`, {
		signal: controller.signal,
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			model: model,
			prompt: prompt,
			...(messages && { messages: messages }),
			type: type,
			stream: false
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	const response = res?.choices[0]?.message?.content ?? '';

	try {
		const jsonStartIndex = response.indexOf('{');
		const jsonEndIndex = response.lastIndexOf('}');

		if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
			const jsonResponse = response.substring(jsonStartIndex, jsonEndIndex + 1);

			// Step 5: Parse the JSON block
			const parsed = JSON.parse(jsonResponse);

			// Step 6: If there's a "queries" key, return the queries array; otherwise, return an empty array
			if (parsed && parsed.text) {
				return parsed.text;
			} else {
				return '';
			}
		}

		// If no valid JSON block found, return response as is
		return response;
	} catch (e) {
		// Catch and safely return empty array on any parsing errors
		console.error('Failed to parse response: ', e);
		return response;
	}
};

export const generateMoACompletion = async (
	token: string = '',
	model: string,
	prompt: string,
	responses: string[]
) => {
	const controller = new AbortController();

	try {
		const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/moa/completions`, {
			signal: controller.signal,
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ model, prompt, responses, stream: true })
		});

		return [res, controller];
	} catch (err: any) {
		console.error('[Main API] generateMoACompletion:', err);
		throw err;
	}
};

export const getPipelinesList = async (token: string = '') => {
	const res = await api('/api/v1/pipelines/list', 'GET', null, 'getPipelinesList');
	return res?.data ?? [];
};

export const uploadPipeline = async (token: string, file: File, urlIdx: string) => {
	try {
		const formData = new FormData();
		formData.append('file', file);
		formData.append('urlIdx', urlIdx);

		const res = await fetch(`${WEBUI_BASE_URL}/api/v1/pipelines/upload`, {
			method: 'POST',
			headers: { ...(token && { authorization: `Bearer ${token}` }) },
			body: formData
		});

		if (!res.ok) throw await res.json();
		return res.json();
	} catch (err: any) {
		console.error('[Main API] uploadPipeline:', err);
		throw err.detail || err;
	}
};

export const downloadPipeline = async (token: string, url: string, urlIdx: string) =>
	api(`${WEBUI_BASE_URL}/api/v1/pipelines/add`, 'POST', { url, urlIdx }, `downloadPipeline(${url})`);

export const deletePipeline = async (token: string, id: string, urlIdx: string) =>
	api(`${WEBUI_BASE_URL}/api/v1/pipelines/delete`, 'DELETE', { id, urlIdx }, `deletePipeline(${id})`);

export const getPipelines = async (token: string, urlIdx?: string) => {
	const searchParams = new URLSearchParams();
	if (urlIdx !== undefined) {
		searchParams.append('urlIdx', urlIdx);
	}

	const res = await api(`/api/v1/pipelines/?${searchParams.toString()}`, 'GET', null, 'getPipelines');
	return res?.data ?? [];
};

export const getPipelineValves = async (token: string, pipeline_id: string, urlIdx: string) => {
	const searchParams = new URLSearchParams();
	if (urlIdx !== undefined) {
		searchParams.append('urlIdx', urlIdx);
	}

	return await api(`/api/v1/pipelines/${pipeline_id}/valves?${searchParams.toString()}`, 'GET', null, 'getPipelineValves');
};

export const getPipelineValvesSpec = async (token: string, pipeline_id: string, urlIdx: string) => {
	const searchParams = new URLSearchParams();
	if (urlIdx !== undefined) {
		searchParams.append('urlIdx', urlIdx);
	}

	return await api(`/api/v1/pipelines/${pipeline_id}/valves/spec?${searchParams.toString()}`, 'GET', null, 'getPipelineValvesSpec');
};

export const updatePipelineValves = async (
	token: string = '',
	pipeline_id: string,
	valves: object,
	urlIdx: string
) => {
	const searchParams = new URLSearchParams();
	if (urlIdx !== undefined) {
		searchParams.append('urlIdx', urlIdx);
	}

	return await api(
		`${WEBUI_BASE_URL}/api/v1/pipelines/${pipeline_id}/valves/update?${searchParams.toString()}`,
		'POST',
		valves,
		`updatePipelineValves(${pipeline_id})`
	);
};

export const getUsage = async (token: string = '') =>
	api(`${WEBUI_BASE_URL}/api/usage`, 'GET', null, 'getUsage');

export const getBackendConfig = async (fetch: any = globalThis.fetch) => {
	try {
		const res = await fetch(`${WEBUI_BASE_URL}/api/config`, {
			method: 'GET',
			credentials: 'include',
			headers: { 'Content-Type': 'application/json' }
		});

		if (!res.ok) throw await res.json();
		return res.json();
	} catch (err: any) {
		console.error('[Main API] getBackendConfig:', err);
		throw err;
	}
};

export const updateBackendConfig = async (config: object) =>
    api(`${WEBUI_BASE_URL}/api/config`, 'POST', config, 'updateBackendConfig');

export const getChangelog = async () =>
	api(`${WEBUI_BASE_URL}/api/changelog`, 'GET', null, 'getChangelog');

export const getVersionUpdates = async (token: string) =>
	api(`${WEBUI_BASE_URL}/api/version/updates`, 'GET', null, 'getVersionUpdates');

export const getModelFilterConfig = async (token: string) =>
	api(`${WEBUI_BASE_URL}/api/config/model/filter`, 'GET', null, 'getModelFilterConfig');

export const updateModelFilterConfig = async (
	token: string,
	enabled: boolean,
	models: string[]
) =>
	api(`${WEBUI_BASE_URL}/api/config/model/filter`, 'POST', { enabled, models }, 'updateModelFilterConfig');

export const getWebhookUrl = async (token: string) => {
	const res = await api(`${WEBUI_BASE_URL}/api/webhook`, 'GET', null, 'getWebhookUrl');
	return res.url;
};

export const updateWebhookUrl = async (token: string, url: string) => {
	const res = await api(`${WEBUI_BASE_URL}/api/webhook`, 'POST', { url }, 'updateWebhookUrl');
	return res.url;
};

export const getCommunitySharingEnabledStatus = async (token: string) =>
	api(`${WEBUI_BASE_URL}/api/community_sharing`, 'GET', null, 'getCommunitySharingEnabledStatus');

export const toggleCommunitySharingEnabledStatus = async (token: string) =>
	api(`${WEBUI_BASE_URL}/api/community_sharing/toggle`, 'GET', null, 'toggleCommunitySharingEnabledStatus');

export const getModelConfig = async (token: string): Promise<GlobalModelConfig> => {
	const res = await api(`${WEBUI_BASE_URL}/api/config/models`, 'GET', null, 'getModelConfig');
	return res.models;
};

export interface ModelConfig {
	id: string;
	name: string;
	meta: ModelMeta;
	base_model_id?: string;
	params: ModelParams;
}

export interface ModelMeta {
	toolIds: never[];
	description?: string;
	capabilities?: object;
	profile_image_url?: string;
}

export interface ModelParams { }

export type GlobalModelConfig = ModelConfig[];

export const updateModelConfig = async (token: string, config: GlobalModelConfig) =>
	api(`${WEBUI_BASE_URL}/api/config/models`, 'POST', { models: config }, 'updateModelConfig');
