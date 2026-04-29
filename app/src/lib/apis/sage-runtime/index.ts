/**
 * try.sage runtime API client.
 *
 * Wraps the six endpoints exposed by `routers/sage_runtime.py`. All routes
 * 404 when ENABLE_TRY_SAGE is False on the backend, so callers must handle
 * the not-found case rather than assume try mode is on.
 *
 * The persona magic-link URLs returned by `getPersonas` are full sign-in
 * URLs (`${WEBUI_URL}/auth#magic_token=<jwt>`). Treat them as semi-secret —
 * they are intentionally exposed in the workshop banner UX, but should
 * never be logged or persisted to client storage.
 */

import { WEBUI_API_BASE_URL } from '$lib/constants';
import { createApiHelper } from '../base';

const api = createApiHelper('SageRuntime', WEBUI_API_BASE_URL);

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type TutorialStep = {
	id: string;
	title: string;
	video_url?: string;
	dismissible?: boolean;
	description?: string;
};

export type RuntimeStatus = {
	enabled: boolean;
	reset_at: string;
	hours_until_reset: number;
	banner_text: string;
	tutorial_steps: TutorialStep[];
	// Background-install state for the trial-mode vector backend
	// (chromadb). Mirrors `app.state.MODEL_DOWNLOAD_STATUS["chromadb"]`.
	// "ready" = imported and seed bound KBs, "downloading" = first-boot
	// pip install in progress, "error" = install failed (engine_error
	// has details), "pending" = unknown / not yet attempted.
	engine_status?: 'ready' | 'downloading' | 'error' | 'pending';
	engine_error?: string | null;
};

export type Persona = {
	key: string;
	label: string;
	role: string;
	login_url: string;
};

export type RuntimeLimits = {
	allowed_models: string[];
	seat_count: number;
	reset_interval_hours: number;
};

export type LLMStatus = {
	configured: boolean;
	model_count: number;
};

export type ExtendResult = {
	reset_at: string;
	extended_by_hours: number;
};

export type ResetResult = {
	reset_at: string;
	wiped_personas: number;
};

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------

// Public when try mode is on.
export const getStatus = async (token: string): Promise<RuntimeStatus> =>
	api('/sage/runtime/status', 'GET', undefined, token, 'getStatus');

// Public when try mode is on. Returns persona magic-link URLs that the
// banner and the user-menu persona switcher both render.
export const getPersonas = async (token: string): Promise<Persona[]> =>
	api('/sage/runtime/personas', 'GET', undefined, token, 'getPersonas');

// Public when try mode is on. Used by the trial-mode admin tab to show
// the operator what the trial actually exposes.
export const getLimits = async (token: string): Promise<RuntimeLimits> =>
	api('/sage/runtime/limits', 'GET', undefined, token, 'getLimits');

// Admin-only. Diagnostic for the hidden LLM connection. Returns shape
// `{configured, model_count}` only — never the URL or key.
export const getLLMStatus = async (token: string): Promise<LLMStatus> =>
	api('/sage/runtime/llm-status', 'GET', undefined, token, 'getLLMStatus');

// Admin-only. Advances the reset deadline by TRY_SAGE_ADMIN_EXTEND_HOURS.
// Backend returns 409 if the window has already been extended once.
export const extendReset = async (token: string): Promise<ExtendResult> =>
	api('/sage/runtime/extend', 'POST', undefined, token, 'extendReset');

// Admin-only. Wipes persona chats and uploaded files immediately, then
// rolls the reset deadline forward by one full interval.
export const forceReset = async (token: string): Promise<ResetResult> =>
	api('/sage/runtime/reset', 'POST', undefined, token, 'forceReset');
