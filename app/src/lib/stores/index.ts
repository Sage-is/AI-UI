import { APP_NAME } from '$lib/constants';
import { type Writable, writable } from 'svelte/store';
import type { ModelConfig } from '$lib/apis';
import type { Banner } from '$lib/types';
import type { Socket } from 'socket.io-client';

import emojiShortCodes from '$lib/emoji-shortcodes.json';

// Backend
export const WEBUI_NAME = writable(APP_NAME);
export const config: Writable<Config | undefined> = writable(undefined);
export const user: Writable<SessionUser | undefined> = writable(undefined);

// try.sage personas. Banner and user-menu persona switcher both render
// from this store. Hydrated by `loadPersonas()` from
// `$lib/utils/sage-runtime`; `null` means "not yet fetched". Reset to
// `null` after admin extend/reset to force re-fetch and pick up rotated
// magic-link URLs.
export const tryPersonas: Writable<
	Array<{ key: string; label: string; role: string; login_url: string }> | null
> = writable(null);

// try.sage tutorial replay trigger. The TrialMode admin panel increments
// this counter to ask <TrySageTutorial> to re-open after the operator
// clicks "Replay tutorial". A counter (not a boolean) so consecutive
// replays each fire a fresh subscription event.
export const tutorialReopen: Writable<number> = writable(0);

// Electron App
export const isApp = writable(false);
export const appInfo = writable(null);
export const appData = writable(null);

// Frontend
export const MODEL_DOWNLOAD_POOL = writable({});

export const mobile = writable(false);

export const socket: Writable<null | Socket> = writable(null);
export const activeUserIds: Writable<null | string[]> = writable(null);
export const USAGE_POOL: Writable<null | string[]> = writable(null);

export const theme = writable('system');

export const shortCodesToEmojis = writable(
	Object.entries(emojiShortCodes).reduce((acc, [key, value]) => {
		if (typeof value === 'string') {
			acc[value] = key;
		} else {
			for (const v of value) {
				acc[v] = key;
			}
		}

		return acc;
	}, {})
);

export const TTSWorker = writable(null);

export const chatId = writable('');
export const chatTitle = writable('');

export const spaces = writable([]);
export const chats = writable(null);
export const pinnedChats = writable([]);
export const tags = writable([]);

export const selectedFolder = writable(null);

export const sharedWithMeChats = writable([]);
export const sharedByMeChats = writable([]);

export const models: Writable<Model[]> = writable([]);

export const prompts: Writable<null | Prompt[]> = writable(null);
export const knowledge: Writable<null | Document[]> = writable(null);
export const tools = writable(null);
export const functions = writable(null);

export const toolServers: Writable<any[]> = writable([]);

export const banners: Writable<Banner[]> = writable([]);


export const settings: Writable<Settings> = writable({});

export const showSidebar = writable(false);
export const showSearch = writable(false);
export const searchQuery = writable('');
export const showSettings = writable(false);
export const showShortcuts = writable(false);
export const showArchivedChats = writable(false);
export const showChangesAndSetup = writable(false);
export const showDevMissionReminder = writable(false);

export type SetupTriggerReason = {
	hasChangelog: boolean;
	needsModels: boolean;
	needsUsers: boolean;
	manualTrigger: boolean;
};
export const setupTriggerReason: Writable<SetupTriggerReason> = writable({
	hasChangelog: false,
	needsModels: false,
	needsUsers: false,
	manualTrigger: false
});

export const showControls = writable(false);
export const showOverview = writable(false);
export const showArtifacts = writable(false);
export const showCallOverlay = writable(false);

export const artifactCode = writable(null);

export const temporaryChatEnabled = writable(false);
export const scrollPaginationEnabled = writable(false);
export const currentChatPage = writable(1);

export const folderCollapseAllTrigger = writable(0);

export const isLastActiveTab = writable(true);
export const playingNotificationSound = writable(false);

export type Model = OpenAIModel | OllamaModel;

type BaseModel = {
	id: string;
	name: string;
	info?: ModelConfig;
	owned_by: 'ollama' | 'openai' | 'arena';
	preset?: boolean;
};

export interface OpenAIModel extends BaseModel {
	owned_by: 'openai';
	external: boolean;
	source?: string;
}

export interface OllamaModel extends BaseModel {
	owned_by: 'ollama';
	details: OllamaModelDetails;
	size: number;
	description: string;
	model: string;
	modified_at: string;
	digest: string;
	ollama?: {
		name?: string;
		model?: string;
		modified_at: string;
		size?: number;
		digest?: string;
		details?: {
			parent_model?: string;
			format?: string;
			family?: string;
			families?: string[];
			parameter_size?: string;
			quantization_level?: string;
		};
		urls?: number[];
	};
}

type OllamaModelDetails = {
	parent_model: string;
	format: string;
	family: string;
	families: string[] | null;
	parameter_size: string;
	quantization_level: string;
};

type Settings = {
	version?: string;
	pinnedModels?: any[];
	toolServers?: any[];
	detectArtifacts?: boolean;
	showUpdateToast?: boolean;
	showChangelog?: boolean;
	showEmojiInCall?: boolean;
	voiceInterruption?: boolean;
	collapseCodeBlocks?: boolean;
	expandDetails?: boolean;
	notificationSound?: boolean;
	notificationSoundAlways?: boolean;
	stylizedPdfExport?: boolean;
	notifications?: any;

	imageCompression?: boolean;
	imageCompressionSize?: any;
	widescreenMode?: null;
	largeTextAsFile?: boolean;
	promptAutocomplete?: boolean;
	hapticFeedback?: boolean;
	responseAutoCopy?: any;
	richTextInput?: boolean;
	params?: any;
	userLocation?: any;
	webSearch?: boolean;
	memory?: boolean;
	autoTags?: boolean;
	autoFollowUps?: boolean;
	splitLargeChunks?(body: any, splitLargeChunks: any): unknown;
	backgroundImageUrl?: null;
	landingPageMode?: string;
	iframeSandboxAllowForms?: boolean;
	iframeSandboxAllowSameOrigin?: boolean;
	scrollOnBranchChange?: boolean;
	directConnections?: any;
	chatBubble?: boolean;
	copyFormatted?: boolean;
	workingAlone?: boolean;
	setupCompleted?: boolean;
	devMissionSignup?: boolean;

	models?: string[];
	conversationMode?: boolean;
	speechAutoSend?: boolean;
	responseAutoPlayback?: boolean;
	audio?: AudioSettings;
	showUsername?: boolean;
	notificationEnabled?: boolean;
	highContrastMode?: boolean;
	title?: TitleSettings;
	splitLargeDeltas?: boolean;
	chatDirection?: 'LTR' | 'RTL' | 'auto';
	ctrlEnterToSend?: boolean;

	system?: string;
	seed?: number;
	temperature?: string;

	repeat_penalty?: string;
	top_k?: string;
	top_p?: string;
	num_ctx?: string;
	num_batch?: string;
	num_keep?: string;
	options?: ModelOptions;
};

type ModelOptions = {
	stop?: boolean;
};

type AudioSettings = {
	stt: any;
	tts: any;
	STTEngine?: string;
	TTSEngine?: string;
	speaker?: string;
	model?: string;
	nonLocalVoices?: boolean;
};

type TitleSettings = {
	auto?: boolean;
	model?: string;
	modelExternal?: string;
	prompt?: string;
};

type Prompt = {
	command: string;
	user_id: string;
	title: string;
	content: string;
	timestamp: number;
};

type Document = {
	collection_name: string;
	filename: string;
	name: string;
	title: string;
};

type Config = {
	license_metadata: any;
	status: boolean;
	name: string;
	version: string;
	dev_mode?: boolean;
	default_locale: string;
	default_models: string;
	default_prompt_suggestions: PromptSuggestion[];
	default_model_selector_filter?: string;
	features: {
		auth: boolean;
		auth_trusted_header: boolean;
		enable_api_key: boolean;
		enable_signup: boolean;
		enable_login_form: boolean;
		enable_web_search?: boolean;
		enable_google_drive_integration: boolean;
		enable_onedrive_integration: boolean;
		enable_image_generation: boolean;
		enable_admin_export: boolean;
		enable_admin_chat_access: boolean;
		enable_community_sharing: boolean;
		enable_autocomplete_generation: boolean;
		enable_direct_connections: boolean;
		enable_version_update_check: boolean;
		enable_websocket?: boolean;
		enable_notes?: boolean;
		// Trial-mode flag. Backend exposes this to anonymous users so the
		// banner mounts on /auth and /join routes before login. Detailed
		// trial state (countdown, seat count, tutorial steps) lives in
		// the gated `try_sage` block below — that one only populates for
		// authenticated users.
		enable_try_sage?: boolean;
	};
	oauth: {
		providers: {

			[key: string]: string;
		};
	};
	ui?: {
		pending_user_overlay_title?: string;
		pending_user_overlay_description?: string;
		theme?: string;
		custom_css?: string;
	};
	// try.sage trial state. Populated only for authenticated users when
	// ENABLE_TRY_SAGE is on; anonymous users see {enabled: false} and use
	// `features.enable_try_sage` to decide whether to mount the banner.
	try_sage?: {
		enabled: boolean;
		reset_at?: string;
		reset_interval_hours?: number;
		admin_extend_hours?: number;
		seat_count?: number;
		banner_text?: string;
		// Tutorial steps come through as a JSON-encoded string so admins
		// can edit them via the config UI without restarting. Frontend
		// parses on first read (see TrySageTutorial.svelte).
		tutorial_steps_json?: string;
	};
	// Analytics shim. Each provider is enabled by populating its config
	// block; multiple providers can run side-by-side. Empty values mean
	// "not enabled" — no script tag injected, no events sent.
	analytics?: {
		matomo?: { url?: string; site_id?: string };
		ga?: { measurement_id?: string };
		plausible?: { domain?: string; script_url?: string };
	};
};

type PromptSuggestion = {
	content: string;
	title: [string, string];
};

type SessionUser = {
	permissions: any;
	id: string;
	email: string;
	name: string;
	role: string;
	profile_image_url: string;
	expires_at?: number;
	info?: Record<string, any>;
};

