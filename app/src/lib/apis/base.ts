/**
 * Centralized API Base Layer - Enhanced Error Reporting System
 * 
 * This module provides a standardized, DRY approach to API calls with comprehensive
 * error reporting, performance monitoring, and user-friendly error messages.
 * 
 * Usage:
 * import { createApiHelper } from '$lib/apis/base';
 * const api = createApiHelper('TOOLS', WEBUI_API_BASE_URL);
 * const result = await api('/endpoint', 'POST', body, token, 'operationName');
 */

export interface ApiErrorContext {
	url: string;
	method: string;
	status?: number;
	statusText?: string;
	operation?: string;
	error: any;
	requestBody?: any;
	duration: string;
	timestamp: string;
}

export interface ApiConfig {
	moduleName: string;
	baseUrl: string;
	pathPrefix?: string;
}

/**
 * Enhanced error handler with domain-specific error messages
 */
class ApiError extends Error {
	public status?: number;
	public statusText?: string;
	public context: ApiErrorContext;

	constructor(message: string, context: ApiErrorContext) {
		super(message);
		this.name = 'ApiError';
		this.status = context.status;
		this.statusText = context.statusText;
		this.context = context;
	}
}

/**
 * Creates a domain-specific API helper with enhanced error reporting
 */
export function createApiHelper(moduleName: string, baseUrl: string, pathPrefix: string = '') {
	return async function api(
		endpoint: string,
		method: string = 'GET',
		body?: any,
		token?: string,
		operationContext?: string
	) {
		const startTime = Date.now();
		const fullUrl = `${baseUrl}${pathPrefix}${endpoint}`;

		try {
			const options: RequestInit = {
				method,
				credentials: 'include',
				headers: {
					Accept: 'application/json',
					'Content-Type': 'application/json',
					// Use the header format that matches the original API patterns
					...(token && { authorization: `Bearer ${token}` })
				}
			};

			if (body) options.body = JSON.stringify(body);

			console.debug(`[${moduleName}] ${operationContext || method} ${endpoint} - Starting request`);

			const res = await fetch(fullUrl, options);
			const duration = Date.now() - startTime;

			if (!res.ok) {
				let errorData;
				try {
					errorData = await res.json();
				} catch {
					// If response isn't JSON, create a generic error object
					errorData = {
						detail: `${res.status} ${res.statusText}`,
						status: res.status,
						statusText: res.statusText
					};
				}

				const errorContext: ApiErrorContext = {
					url: fullUrl,
					method,
					status: res.status,
					statusText: res.statusText,
					operation: operationContext,
					error: errorData,
					...(body && { requestBody: body }),
					duration: `${duration}ms`,
					timestamp: new Date().toISOString()
				};

				console.error(`[${moduleName}] ${operationContext || method} ${endpoint} - HTTP ${res.status} ${res.statusText} (${duration}ms)`, errorContext);

				// Throw the error in the same format as the original APIs
				throw errorData;
			}

			console.debug(`[${moduleName}] ${operationContext || method} ${endpoint} - Success (${duration}ms)`);
			return res.json();

		} catch (err: any) {
			const duration = Date.now() - startTime;

			// If it's already an API error from above, re-throw it unchanged for backward compatibility
			if (err && typeof err === 'object' && (err.detail || err.status)) {
				throw err;
			}

			// Handle network and other errors
			const errorContext: ApiErrorContext = {
				url: fullUrl,
				method,
				operation: operationContext,
				error: err,
				...(body && { requestBody: body }),
				duration: `${duration}ms`,
				timestamp: new Date().toISOString()
			};

			console.error(`[${moduleName}] ${operationContext || method} ${endpoint} - Failed (${duration}ms)`, errorContext);

			// For network errors, throw in the same format as original APIs
			if (err.name === 'TypeError' && err.message.includes('fetch')) {
				throw {
					detail: `Network error: Unable to reach ${moduleName} API. Please check your connection and try again.`
				};
			}

			// Return original error for backward compatibility
			throw err.detail || err.message || err;
		}
	};
}

/**
 * Generates user-friendly error messages based on HTTP status codes
 */
function getUserFriendlyErrorMessage(status: number, moduleName: string): string {
	const module = moduleName.toLowerCase();

	switch (status) {
		case 400:
			return `Invalid request: Please check your input and try again.`;
		case 401:
			return `Authentication failed: Please log in again to access ${module} features.`;
		case 403:
			return `Access denied: You don't have permission to perform this ${module} operation.`;
		case 404:
			return `Resource not found: The requested ${module} resource may have been deleted or doesn't exist.`;
		case 409:
			return `Conflict: This ${module} resource already exists or is currently in use.`;
		case 413:
			return `Request too large: The file or data exceeds the maximum size limit.`;
		case 422:
			return `Invalid format: The data format is not supported or couldn't be processed.`;
		case 429:
			return `Rate limit exceeded: Too many requests. Please wait a moment and try again.`;
		case 500:
			return `Server error: The ${moduleName} API encountered an internal error. Please try again later.`;
		case 502:
			return `Bad gateway: The ${moduleName} service is temporarily unavailable.`;
		case 503:
			return `Service unavailable: The ${moduleName} API is temporarily down for maintenance.`;
		case 504:
			return `Gateway timeout: The ${moduleName} request timed out. Please try again.`;
		default:
			return `${moduleName} API error (HTTP ${status}): Please try again or contact support if the problem persists.`;
	}
}

/**
 * Specialized helper for blob responses (files, downloads, etc.)
 */
export function createApiBlobHelper(moduleName: string, baseUrl: string, pathPrefix: string = '') {
	return async function apiBlob(
		endpoint: string,
		method: string = 'GET',
		body?: any,
		token?: string,
		operationContext?: string
	): Promise<Blob> {
		const startTime = Date.now();
		const fullUrl = `${baseUrl}${pathPrefix}${endpoint}`;

		try {
			const options: RequestInit = {
				method,
				credentials: 'include',
				headers: {
					'Content-Type': 'application/json',
					...(token && { authorization: `Bearer ${token}` })
				}
			};

			if (body) options.body = JSON.stringify(body);

			console.debug(`[${moduleName}] ${operationContext || method} ${endpoint} - Starting blob request`);

			const res = await fetch(fullUrl, options);
			const duration = Date.now() - startTime;

			if (!res.ok) {
				let errorData;
				try {
					errorData = await res.json();
				} catch {
					errorData = {
						detail: `${res.status} ${res.statusText}`,
						status: res.status,
						statusText: res.statusText
					};
				}

				console.error(`[${moduleName}] ${operationContext || method} ${endpoint} - HTTP ${res.status} ${res.statusText} (${duration}ms)`, {
					url: fullUrl,
					method,
					status: res.status,
					statusText: res.statusText,
					operation: operationContext,
					error: errorData,
					duration: `${duration}ms`,
					timestamp: new Date().toISOString()
				});

				throw errorData;
			}

			console.debug(`[${moduleName}] ${operationContext || method} ${endpoint} - Blob success (${duration}ms)`);
			return res.blob();

		} catch (err: any) {
			// If it's already an API error, re-throw unchanged
			if (err && typeof err === 'object' && (err.detail || err.status)) {
				throw err;
			}

			const duration = Date.now() - startTime;
			console.error(`[${moduleName}] ${operationContext || method} ${endpoint} - Blob failed (${duration}ms)`, err);

			throw {
				detail: `Failed to download from ${moduleName} API: ${err.message || err}`
			};
		}
	};
}

/**
 * Helper for file download operations with DOM manipulation
 */
export function createDownloadHelper(moduleName: string, baseUrl: string, pathPrefix: string = '') {
	const apiBlob = createApiBlobHelper(moduleName, baseUrl, pathPrefix);

	return async function downloadFile(
		endpoint: string,
		filename: string,
		token: string,
		operationContext?: string
	): Promise<void> {
		try {
			const blob = await apiBlob(endpoint, 'GET', undefined, token, operationContext || `downloadFile(${filename})`);

			const url = window.URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = filename;
			document.body.appendChild(a);
			a.click();
			window.URL.revokeObjectURL(url);
			document.body.removeChild(a);

			console.debug(`[${moduleName}] Successfully downloaded ${filename}`);
		} catch (err: any) {
			console.error(`[${moduleName}] Download failed for ${filename}:`, err);
			throw err;
		}
	};
}

export default createApiHelper;
