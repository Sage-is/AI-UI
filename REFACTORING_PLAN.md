# Refactoring Plan: DRY & KISS Improvements

This document outlines a plan to eliminate code duplication (DRY) and simplify the codebase (KISS), focusing on the API layer and the `Chat.svelte` component.

## Goals
1.  **Centralize API Logic**: Eliminate multiple incompatible `api` helper definitions across the codebase.
2.  **Simplify Chat Component**: Reduce the complexity of `Chat.svelte` by extracting non-UI logic.

## 1. Centralize API Client

**Objective**: Create a single source of truth for making API requests that handles authentication (Cookies & Bearer Tokens) and error handling consistently.

### [NEW] `src/lib/api.ts`
Create a universal API request handler `sysApi` (or similar) that:
- Accepts a unified configuration object: `{ url, method, body, token, context }`.
- Automatically handles `credentials: 'include'` for cookie-based authentication.
- Conditionally adds `Authorization: Bearer ${token}` header if a token is provided.
- Centralizes error logging and response parsing (JSON vs Text/HTML handling).

## 2. Unify API Modules

**Objective**: Refactor existing API modules to use the central client.

### [MODIFY] `src/lib/apis/index.ts`
- Remove the local `api` function definition.
- Import the central client from `$lib/api`.
- Implement a backward-compatible adapter if necessary, or refactor all exports to use the new client key-value signature.

### [MODIFY] `src/lib/apis/chats/index.ts`
- Remove the local `api` function definition.
- Update all exported functions (`createNewChat`, `getChatList`, etc.) to use the central client.

### [MODIFY] `src/lib/apis/openai/index.ts`
- Remove the local `api` helper.
- Update `getOpenAIConfig`, `updateOpenAIConfig`, etc., to use the central client.

## 3. Cleanup Chat.svelte

**Objective**: Reduce the file size and cognitive load of `Chat.svelte` (currently ~2300 lines).

### [NEW] `src/lib/components/chat/chatUtils.ts`
Extract complex, non-UI logic into a pure TypeScript utility file. Candidates for extraction include:
- `createMessagePair`: Logic for creating user/assistant message objects.
- `addMessages`: Logic for appending messages to history.
- `generateQueries`: Helper logic for search query generation.
- `submitPrompt`: (Careful extraction required due to local state dependencies).

### [MODIFY] `src/lib/components/chat/Chat.svelte`
- Import functions from `chatUtils.ts`.
- Replace inline logic with function calls.

## Verification Checklist

### API Functionality
- [ ] **Chat List**: Verify loading the chat list works (uses Token auth).
- [ ] **Config**: Verify fetching backend config works (uses Cookie/No Token).
- [ ] **OpenAI**: Verify fetching models works.

### Chat Interaction
- [ ] **New Chat**: Create a new chat and ensure no 403 or 422 errors.
- [ ] **Messaging**: Send a message and verify the response streaming and completion.
