---
title: "Codebase Audit Report"
description: "Audit findings on component structure, state management, and code redundancy from December 2025."
date: 2025-12-16
tags:
  - audit
  - architecture
  - technical-debt
  - review
---

# Codebase Audit Report

## Executive Summary
The codebase exhibits significant complexity and potential redundancy, with a heavy reliance on client-side state management and large monolithic components. There are clear signs of "reinventing the wheel" where standard libraries or server-side rendering could simplify the architecture.

## 1. Component Structure Analysis (`src/lib/components`)
- **Monolithic Components**: key components like `Chat.svelte` (60KB+) and `MessageInput.svelte` (65KB+) are excessively large. This suggests a lack of separation of concerns and makes maintenance difficult.
- **Deep Nesting**: The `chat` directory alone has 81 items, including deeply nested subdirectories like `Messages`, `Settings`, `Placeholder`.
- **Reinvention**: Custom implementations for standard UI elements like `Tooltip.svelte`, `Switch.svelte`, `Modal.svelte` (3KB+), `Dropdown.svelte` are present. While common in component libraries, maintaining these locally adds significant technical debt compared to using a headless UI library efficiently.

## 2. State Management Analysis (`src/lib/stores`)
- **Centralized Monolith**: `src/lib/stores/index.ts` is a single file exporting over 40 writable stores.
- **Global State Overuse**: Heavily relies on global functionality for everything from `WEBUI_NAME` to `playingNotificationSound`. This makes tracking data flow extremely difficult and contributes to the "spaghetti code" feel.
- **Tangled Dependencies**: Stores mix backend config, specific UI state (`showSearch`, `showSidebar`), and volatile chat data (`models`, `prompts`, `messages`).

## 3. Utilities & APIs (`src/lib/utils`, `src/lib/apis`)
- **API Sprawl**: The `apis` directory contains ~23 subdirectories and a 27KB `index.ts`, suggesting excessive boilerplate or leaked business logic.
- **Utils Bloat**: `src/lib/utils/index.ts` is a massive 44KB file. This is a strong indicator of "utils drawer" syndrome, where unrelated logic is dumped into a single bucket instead of being modularized.

## 4. "Padding" & Redundancy Findings
- **Custom implementing what exists**: The project implements its own versions of complex interactions like `RichTextInput.svelte` (35KB) and `CodeEditor.svelte` (7KB) on top of libraries, effectively creating a "wrapper hell".
- **Chat Logic**: `Chat.svelte` seems to handle too much responsibility: routing, socket events, UI rendering, and state updates.

## Recommendations
1.  **Server-Side Rendering (SSR)**: Move data fetching and initial state population to SvelteKit `load` functions in `+page.server.ts` to reduce client-side complexity.
2.  **Refactor Monoliths**: Break down `Chat.svelte` and `MessageInput.svelte` into smaller, functional extractable components.
3.  **Standardize UI**: Audit `common/` components and replace custom maintainable code with a standard library (like `bits-ui` or `shadcn-svelte`) to reduce "owned" code volume.
4.  **Simplify Stores**: Group stores by feature/domain rather than a global dump. Use Svelte 5's fine-grained reactivity (Runes) to eliminate the need for many of these stores.
