import { RETRIEVAL_API_BASE_URL } from '$lib/constants';
import { createApiHelper } from '../base';

// Create standardized API helper for retrieval with enhanced error reporting
const api = createApiHelper('RETRIEVAL', RETRIEVAL_API_BASE_URL);

export const getRAGConfig = async (token: string) => 
	api('/config', 'GET', undefined, token, 'getRAGConfig');

type ChunkConfigForm = {
	chunk_size: number;
	chunk_overlap: number;
};

type DocumentIntelligenceConfigForm = {
	key: string;
	endpoint: string;
};

type ContentExtractConfigForm = {
	engine: string;
	tika_server_url: string | null;
	document_intelligence_config: DocumentIntelligenceConfigForm | null;
};

type YoutubeConfigForm = {
	language: string[];
	translation?: string | null;
	proxy_url: string;
};

type RAGConfigForm = {
	PDF_EXTRACT_IMAGES?: boolean;
	ENABLE_GOOGLE_DRIVE_INTEGRATION?: boolean;
	ENABLE_ONEDRIVE_INTEGRATION?: boolean;
	chunk?: ChunkConfigForm;
	content_extraction?: ContentExtractConfigForm;
	web_loader_ssl_verification?: boolean;
	youtube?: YoutubeConfigForm;
};

export const updateRAGConfig = async (token: string, payload: RAGConfigForm) => 
	api('/config/update', 'POST', payload, token, 'updateRAGConfig');

export const getQuerySettings = async (token: string) => 
	api('/query/settings', 'GET', undefined, token, 'getQuerySettings');

type QuerySettings = {
	k: number | null;
	r: number | null;
	template: string | null;
};

export const updateQuerySettings = async (token: string, settings: QuerySettings) => 
	api('/query/settings/update', 'POST', settings, token, 'updateQuerySettings');

export const getEmbeddingConfig = async (token: string) => 
	api('/embedding', 'GET', undefined, token, 'getEmbeddingConfig');

type OpenAIConfigForm = {
	key: string;
	url: string;
};

type AzureOpenAIConfigForm = {
	key: string;
	url: string;
	version: string;
};

type EmbeddingModelUpdateForm = {
	openai_config?: OpenAIConfigForm;
	azure_openai_config?: AzureOpenAIConfigForm;
	embedding_engine: string;
	embedding_model: string;
	embedding_batch_size?: number;
};

export const updateEmbeddingConfig = async (token: string, payload: EmbeddingModelUpdateForm) => 
	api('/embedding/update', 'POST', payload, token);

export const getRerankingConfig = async (token: string) => 
	api('/reranking', 'GET', undefined, token);

type RerankingModelUpdateForm = {
	reranking_model: string;
};

export const updateRerankingConfig = async (token: string, payload: RerankingModelUpdateForm) => 
	api('/reranking/update', 'POST', payload, token);

export interface SearchDocument {
	status: boolean;
	collection_name: string;
	filenames: string[];
}

export const processFile = async (
	token: string,
	file_id: string,
	collection_name: string | null = null
) => api('/process/file', 'POST', {
	file_id,
	...(collection_name && { collection_name })
}, token, `processFile(${file_id}${collection_name ? `, collection: ${collection_name}` : ''})`);

export const processYoutubeVideo = async (token: string, url: string) => 
	api('/process/youtube', 'POST', { url }, token, `processYoutubeVideo(${url})`);

export const processWeb = async (token: string, collection_name: string, url: string) => 
	api('/process/web', 'POST', { url, collection_name }, token, `processWeb(${url}, collection: ${collection_name})`);

export const processWebSearch = async (
	token: string,
	query: string,
	collection_name?: string
): Promise<SearchDocument | null> => 
	api('/process/web/search', 'POST', {
		query,
		collection_name: collection_name ?? ''
	}, token, `processWebSearch("${query}"${collection_name ? `, collection: ${collection_name}` : ''})`);

export const queryDoc = async (
	token: string,
	collection_name: string,
	query: string,
	k: number | null = null
) => api('/query/doc', 'POST', {
	collection_name,
	query,
	...(k && { k })
}, token, `queryDoc("${query}", collection: ${collection_name}${k ? `, k: ${k}` : ''})`);

export const queryCollection = async (
	token: string,
	collection_names: string,
	query: string,
	k: number | null = null
) => api('/query/collection', 'POST', {
	collection_names,
	query,
	...(k && { k })
}, token, `queryCollection("${query}", collections: ${collection_names}${k ? `, k: ${k}` : ''})`);

export const resetUploadDir = async (token: string) => 
	api('/reset/uploads', 'POST', undefined, token, 'resetUploadDir');

export const resetVectorDB = async (token: string) => 
	api('/reset/db', 'POST', undefined, token, 'resetVectorDB');
