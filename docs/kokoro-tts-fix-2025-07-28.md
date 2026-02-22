---
title: "Kokoro.js TTS Engine Fix"
description: "Fix for personal audio settings not respecting Kokoro.js TTS engine selection over global config."
date: 2025-11-28
tags:
  - bugfix
  - tts
  - audio
  - kokoro
---

# Kokoro.js TTS Engine Fix - July 28, 2025

## Issue Summary
Personal audio settings were selecting Kokoro.js as the TTS engine with specified dtype settings, but the application was still using the Web API for text-to-speech output instead of the configured Kokoro.js engine.

## Root Cause Analysis
The decision logic in `ResponseMessage.svelte` and `CallOverlay.svelte` had incorrect condition precedence:

1. **Original Logic Flow**:
   - First checked: `$config.audio.tts.engine === ''` → used Web API
   - Only then checked: `$settings.audio?.tts?.engine === 'browser-kokoro'` → used Kokoro.js
   - This meant global config took precedence over personal settings

2. **Problem**: Even when users configured Kokoro.js in personal settings, if the global admin config was empty, it would fallback to Web API instead of respecting the personal choice.

## Solution Implementation

### Files Modified
1. `app/src/lib/components/chat/Messages/ResponseMessage.svelte`
2. `app/src/lib/components/chat/MessageInput/CallOverlay.svelte`
3. `submodules/open-webui/src/lib/components/chat/Messages/ResponseMessage.svelte`
4. `submodules/open-webui/src/lib/components/chat/MessageInput/CallOverlay.svelte`

### Key Changes

#### ResponseMessage.svelte Logic Fix
```typescript
// BEFORE: Global config checked first
if ($config.audio.tts.engine === '') {
    // Use Web API
} else {
    // Check for Kokoro.js...
}

// AFTER: Personal settings prioritized
const useWebAPI = ($settings?.audio?.tts?.engine ?? $config.audio.tts.engine) === '';

if (useWebAPI) {
    // Use Web API
} else {
    // Use configured engine (Kokoro.js or OpenAI)
}
```

#### CallOverlay.svelte Logic Fix
```typescript
// BEFORE: Inconsistent condition checking
} else if ($config.audio.tts.engine !== '') {

// AFTER: Consistent personal-first checking
} else if (($settings?.audio?.tts?.engine ?? $config.audio.tts.engine) !== '') {
```

## Technical Details

### Decision Tree (Fixed)
1. **Check Personal Settings First**: `$settings?.audio?.tts?.engine`
2. **Fallback to Global Config**: `$config.audio.tts.engine`
3. **Route to Appropriate Engine**:
   - If result is `'browser-kokoro'` → Use Kokoro.js Worker
   - If result is non-empty string → Use OpenAI Compatible API
   - If result is empty/undefined → Use Web API (speechSynthesis)

### Kokoro.js Engine Features Confirmed Working
- Dtype selection (fp32, fp16, q8, q4)
- Voice selection from Kokoro.js voice models
- Audio quality and playback rate settings
- Proper fallback logic when Kokoro.js fails
- Worker-based processing for performance

## Testing Results
- Personal Kokoro.js settings now properly override global config
- Voice selection works correctly with Kokoro.js models
- Different dtype settings (fp32, fp16, q8, q4) all functional
- Audio output quality confirmed working
- Fallback logic maintains system stability

## Impact
- **User Experience**: Personal audio preferences now work as expected
- **Configuration Flow**: Proper precedence of personal over global settings
- **Audio Quality**: Users can now leverage Kokoro.js high-quality TTS
- **Performance**: Worker-based Kokoro.js processing doesn't block UI

## Follow-up Considerations
- Monitor for any edge cases in voice model loading
- Consider adding user feedback for model loading progress
- Document the proper configuration flow for end users

## Files Documentation Updated
- Added task completion to `TODO.md`
- Archived completed work in this dated documentation file
- Maintained development workflow compliance

---
**Resolution Status**: **COMPLETED**
**Date**: July 28, 2025
**Developer**: GitHub Copilot
**Verified By**: User confirmation of working Kokoro.js TTS
