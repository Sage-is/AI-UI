## 🔥 Current Active Tasks (March 5, 2026)

### 🔴 Knowledge Base Ingestion Modes + Admin Cleanup - HIGH PRIORITY
- [ ] Simpler lost password/single sign on is needed as people forget passwords as they think their minds know how to hold them...
- [ ] **Add AI-Parsed ingestion mode and clean up admin Documents page** (see `docs/knowledge-ingestion-modes-plan.md`)
  - [ ] Admin page cleanup — fold engine-specific config with `<details>/<summary>`
  - [ ] Backend — AI Parser Service (`retrieval/processors/ai_parser.py`)
  - [ ] Backend — Config additions (`AI_PARSE_ENABLED`, model, prompt defaults)
  - [ ] Backend — Ingestion mode routing in `process_file()`
  - [ ] Backend — File upload metadata pass-through
  - [ ] Frontend — AI Parse admin section in Documents.svelte
  - [ ] Frontend — Upload flow mode selector (Plain / AI Parse) in KnowledgeBase.svelte
  - [ ] Testing all modes end-to-end

### 🔴 Codebase Audit Remediation - NEW TASK
- [>] **Address findings from March 2026 codebase audit** (see `docs/codebase-audit-2026-03.md`)

---

## 🔥 Open Tasks (carried forward)

### 🔶 Documentation & Admin Management (Aug 2025) - NOT STARTED
- [ ] **Create Startr Writing Guidelines**: Structure, modernize, and publish house style
  - [ ] Draft structured guide from legacy notes (clarity-first)
  - [ ] Add concise Do/Don't examples for each rule
  - [ ] Publish to `docs/WRITING_GUIDELINES.md`
  - [ ] Link from `README.md` and `docs/README.md`
  - [ ] Verify formatting, headings, and internal anchors
  - [ ] Note future alignment with `CONTRIBUTING.md`

### 🔶 Docker Build Enhancements - NOT STARTED
- [ ] **Docker multi-stage build**: Still single FROM stage, build tools ship in production image
  - [ ] Implement multi-stage build with separate builder and runtime stages
  - [ ] Further build time optimizations (currently 5m52s vs 10m+)
  - [ ] Document fast development rebuild workflow

### 🔶 API Documentation Enhancement - PARTIAL
- [ ] **Complete Swagger UI Configuration**: Basic setup done, enhancements remain
  - [x] Swagger UI enabled and accessible at `/docs`
  - [ ] Configure Swagger UI with custom styling and branding
  - [ ] Document how to access and use the API documentation
  - [ ] Ensure proper authentication handling in Swagger UI

---

## ✅ Verified Completed (March 2026 audit)

### ✅ API Layer Cleanup - COMPLETED
- [x] **Systematic API Refactoring**: 24/24 API files migrated to centralized `createApiHelper()`
  - [x] 0 files still using local `api()` helper — fully migrated
  - [x] `streaming/index.ts` reference implementation in place
  - [x] 5,426+ lines of repetitive code eliminated (75% average reduction)

### ✅ Workspace → Workshop Rename - COMPLETED
- [x] **Complete Workspace → Workshop Rename**: 563 replacements across 103 files
  - [x] `workshop/` component and route directories exist, `workspace/` dirs removed
  - [x] All phases (analysis, migration, content updates, testing) verified complete

### ✅ Channel → Space Rename - COMPLETED
- [x] **Complete Channel → Space Rename**: 1,097 replacements across 87 files
  - [x] `space/` route exists, `channel/` and `channels/` routes removed

### ✅ DRY Code Analysis - 3/4 COMPLETED
- [x] **Priority 1**: ShortcutsModal.svelte — 13KB → 6.1KB (53% reduction) ✅
- [x] **Priority 2**: AdvancedParams.svelte — data-driven config system ✅
- [x] **Priority 4**: Interface.svelte — data-driven config system ✅
- [~] **Priority 3**: WebSearch.svelte — file no longer exists at expected path, status unclear

### ✅ KISS/DRY License Table - COMPLETED
- [x] Simplified to inline data structure, removed async markdown loading

### ✅ Emoji Data DRY Refactoring - COMPLETED
- [x] Pure string-based emoji data, category skin tone logic, Intl.Segmenter

### ✅ Model Editor "Save & Chat" - COMPLETED
### ✅ Model Creation Flow Fix - COMPLETED
### ✅ Interface Settings Default - COMPLETED
### ✅ FloatingButtons UX Improvement - COMPLETED
### ✅ Voice Input UI Enhancement - COMPLETED

---

## ❌ Stale / Needs Re-evaluation

### ❌ Config Management (Sept 2025) - LIKELY MOOT
- [~] **Move config variables to .env**: Backend uses `PersistentConfig(env_name, config_key, default)` pattern natively — already reads from env vars. `.env.example` exists. The proposed dotenv migration doesn't align with the existing architecture. Consider closing or redefining scope.

### ❌ Documents Component DRY - REVERTED/LOST
- [~] **FormField.svelte**: Marked as created and deployed but `FormField.svelte` does not exist in the codebase. Work was either reverted or never committed. Needs re-evaluation.

### ❌ WebSearch Component DRY - FILE MISSING
- [~] **WebSearch.svelte**: File not found at `admin/Settings/WebSearch.svelte`. Either renamed, merged into another component, or deleted. Task is stale.

### ❌ Storage Provider Tests DRY - NOT STARTED
- [~] **Refactor Storage Provider Tests**: No storage-specific test files found, no `BaseStorageProviderTest` class exists. Task was never started. Re-evaluate if still relevant.

### ❓ Dev Mode Console Cleanup - UNCLEAR
- [~] **Fix Dev Mode 404 and CORS Issues**: Vite proxy is configured. Some fixes were applied (COEP, static files). May be resolved — needs manual testing to confirm.

### ❓ PostCSS Browser Compatibility - LIKELY RESOLVED
- [~] **PostCSS Warnings**: Config is now minimal Tailwind v4 plugin only (`@tailwindcss/postcss`). The original warnings were likely from an older PostCSS setup. Needs manual verification.

---

## 🛠️ Feature Prioritization

Features are categorized by priority levels to help focus development efforts:

- **Priority 1**: Critical features that enhance core functionality and user experience.
- **Priority 2**: Important features that improve usability and add value.
- **Priority 3**: Nice-to-have features that can be implemented later.
- **Priority 4**: Future enhancements that can be considered after core features are stable.

## 🗂️ Feature Categories
### 🚀 Quick Widgets & Home Screen Enhancements

#### **Priority 2: Dashboard Landing Page**

- [ ] **Enhanced Home Dashboard**: Create a comprehensive landing page as per our Sage.is offer
  - [ ] Recent conversations widget with quick access
  - [ ] Favorite/starred chats quick access
  - [ ] Model, Agent, and User status indicators (online/offline)
  - [ ] Quick action buttons (New Chat, Upload Document, Search)
  - [ ] Recent files/documents widget
  - [ ] Daily usage statistics
  - [ ] Integration with calendar/schedule (if available)

#### **Priority 1: Quick Access Widgets on Chat Opening**

- [ ] **Smart Prompt Suggestions**: Enhanced suggestion system
  - [ ] Context-aware prompts based on time of day
  - [ ] Role-based prompt templates (Developer, Writer, Analyst, etc.)
  - [ ] Recent successful prompts
  - [ ] Trending community prompts
  - [ ] Custom user-saved quick prompts

- [ ] **Quick Actions Panel**: Floating action buttons
  - [ ] Document upload shortcut
  - [ ] Image generation toggle
  - [ ] Code interpreter toggle
  - [ ] Web search toggle
  - [ ] Voice chat toggle
  - [ ] Share chat instantly

#### **Priority 2: Improved Sidebar Experience**

- [ ] **Home Dashboard Sidebar Shared Categories**: Nice-to-have sidebar expansion
  - [ ] Add `Shared with me` and `Shared by me` as new sidebar categories
  - [ ] Ensure both categories are linked and present filtered shared-chat views

- [ ] **Enhanced Chat Organization**: Better than current folder system
  - [x] Smart auto-categorization by topic
  - [x] Tag-based filtering and search
  - [x] Drag-and-drop organization improvements
  - [ ] Bulk operations (select multiple chats)
  - [ ] Chat templates/presets
  - [ ] Favorite chats section (beyond current pinned)

- [ ] **Workspace Switcher**: Like Sage's project organization
  - [ ] Different workspaces/folders for different projects
  - [ ] Workspace-specific model configurations
  - [ ] Shared vs private workspaces
  - [ ] Workspace templates

## 🎯 Productivity & Workflow Enhancements

### **Priority 1: Task Management Integration**
- [ ] **Built-in Task Tracking**: Inspired by Sage's project management
  - [ ] Convert chat responses to actionable tasks
  - [ ] Task due dates and reminders
  - [ ] Progress tracking for multi-step projects
  - [ ] Integration with external task systems (Trello, Asana)
  - [ ] AI-powered task suggestions from conversations

### **Priority 2: Collaboration Features**
- [ ] **Team Collaboration**: Multi-user workflow improvements
  - [ ] @mention functionality in chats
  - [ ] Shared chat spaces (enhanced channels)
  - [ ] Team workspace management
  - [ ] Role-based permissions (enhanced current system)
  - [ ] Comment threads on specific messages
  - [ ] Follow/unfollow chat notifications

### **Priority 2: Knowledge Management**
- [ ] **Enhanced Knowledge Base**: Upgrade current RAG system
  - [ ] Visual knowledge graph view
  - [ ] Auto-linking related documents
  - [ ] Version control for documents
  - [ ] Document annotation and highlighting
  - [ ] Smart document recommendations
  - [ ] Cross-chat knowledge surfacing

## 🎨 Interface & User Experience

### **Priority 1: Modern UI Improvements**
- [ ] **Enhanced Chat Interface**: Beyond current chat bubble system
  - [ ] Message threading for complex discussions
  - [ ] Rich text editing improvements
  - [ ] Inline code execution results
  - [ ] Collapsible code blocks (enhance current)
  - [ ] Message reactions and ratings
  - [ ] Message bookmarking system

- [ ] **Quick Settings Panel**: Easy access configuration
  - [ ] Model switching without menu navigation
  - [ ] Temperature/parameter quick adjustments
  - [ ] Theme switching with preview
  - [ ] Quick persona/role switching
  - [ ] Language switching shortcut

### **Priority 2: Mobile Experience**
- [ ] **Mobile-First Optimizations**: Improve current responsive design
  - [ ] Swipe gestures for navigation
  - [ ] Voice input optimization
  - [ ] Mobile-specific widgets
  - [ ] Offline mode for recent chats
  - [ ] Progressive Web App enhancements

### **Priority 3: Accessibility Enhancements**
- [ ] **Universal Design**: Improve current accessibility
  - [ ] Screen reader optimizations
  - [ ] High contrast mode
  - [ ] Font size scaling
  - [ ] Keyboard navigation improvements
  - [ ] Voice navigation support

## 🔧 Technical Enhancements

### **Priority 1: Performance & Reliability**
- [ ] **Smart Caching**: Improve current system
  - [ ] Predictive model loading
  - [ ] Conversation state persistence
  - [ ] Offline conversation access
  - [ ] Progressive loading for large chats
  - [ ] Background sync optimization

### **Priority 2: AI Workflow Automation**
- [ ] **Smart Workflows**: Automated task sequences
  - [ ] Multi-step conversation templates
  - [ ] Automated follow-up questions
  - [ ] Workflow branching based on responses
  - [ ] Integration with external APIs
  - [ ] Custom automation rules

### **Priority 2: Advanced Search & Discovery**
- [ ] **Enhanced Search**: Upgrade current search
  - [ ] Semantic search across all chats
  - [ ] Search within documents and files
  - [ ] Advanced filtering options
  - [ ] Search result snippets with context
  - [ ] Saved search queries
  - [ ] Search history and analytics

## 📊 Analytics & Insights

### **Priority 2: Usage Analytics**
- [ ] **Personal Analytics Dashboard**: User insights
  - [ ] Chat frequency and patterns
  - [ ] Most used models and features
  - [ ] Productivity metrics
  - [ ] Learning progress tracking
  - [ ] Export analytics data

### **Priority 3: AI Insights**
- [ ] **Smart Recommendations**: AI-powered suggestions
  - [ ] Suggest relevant past conversations
  - [ ] Recommend optimal models for tasks
  - [ ] Suggest workflow improvements
  - [ ] Predict user needs based on patterns
  - [ ] Content discovery recommendations

## 🔐 Security & Privacy

### **Priority 2: Enhanced Privacy Controls**
- [ ] **Granular Privacy Settings**: Beyond current user roles
  - [ ] Chat-level privacy settings
  - [ ] Data retention controls
  - [ ] Export/delete personal data
  - [ ] Anonymous usage modes
  - [ ] Audit logs for sensitive operations

## 🎭 Personalization & Customization

### **Priority 1: User Personalization**
- [ ] **Advanced Personalization**: Beyond current themes
  - [ ] Custom dashboard layouts
  - [ ] Personalized quick actions
  - [ ] Custom keyboard shortcuts
  - [ ] Personalized suggestion algorithms
  - [ ] Custom chat templates
  - [ ] User-specific model configurations

### **Priority 2: Theming & Branding**
- [ ] **Enhanced Theming**: Improve current theme system
  - [ ] Custom color schemes
  - [ ] Layout customization
  - [ ] Company/team branding options
  - [ ] Custom fonts and typography
  - [ ] Animation preferences

## 🚀 Implementation Strategy

### Phase 1 (Immediate - 2-4 weeks)
1. Enhanced Home Dashboard
2. Quick Access Widgets
3. Smart Prompt Suggestions
4. Quick Settings Panel

### Phase 2 (Short Term - 1-2 months)
1. Task Management Integration
2. Enhanced Chat Interface
3. Workspace Switcher
4. Performance Optimizations

### Phase 3 (Medium Term - 2-4 months)
1. Collaboration Features
2. Advanced Search & Discovery
3. Mobile Experience Enhancements
4. Analytics Dashboard

### Phase 4 (Long Term - 4-6 months)
1. AI Workflow Automation
2. Advanced Analytics
3. Enhanced Privacy Controls
4. Full Customization System

## 📝 Notes

- Each feature should be implemented incrementally with user feedback
- Maintain backward compatibility with existing configurations
- Focus on features that provide the highest user value first
- Consider performance impact of each enhancement
- Ensure all features work well in both single-user and multi-user environments
- Test extensively with different user roles and permissions

---

---

## ✅ Completed Work Summary

### Recent Major Achievements (August 1, 2025)

#### 🏆 Development Environment Fixes - COMPLETED
- **COEP Policy Fix**: Disabled Cross-Origin-Embedder-Policy for localhost development
  - Modified vite.config.ts to conditionally set COEP headers only for production
  - Kept COOP (Cross-Origin-Opener-Policy) for security but removed COEP in dev
  - Eliminated COEP-related errors in development environment
  - Production builds still maintain proper security headers
- **Audio File Error Handling**: Fixed Audio NotSupportedError in +layout.svelte
  - Added error handling for audio.play() calls to prevent uncaught exceptions
  - Ensured audio files are accessible in development mode
  - Added fallback behavior when audio files are missing
- **Authentication Error Cleanup**: Fixed Token Warning in +layout.svelte
  - Changed console.warn to console.log for better UX during initial auth
  - Ensured proper token handling without alarming users
  - Verified socket connection handling is appropriate
- **Static File 404 Fix**: Resolved favicon.png, logo.png returning 404 in container
  - Fixed manifest.json 404 errors with proper proxy config
  - Resolved favicon CORS blocking with CORS_ALLOW_ORIGIN
  - Configured proper dev server static file handling with vite proxies

#### 🏆 Docker Build Optimization (July 29-30, 2025) - COMPLETED
- **MAJOR SUCCESS**: Achieved 50% build time improvement (5m52s vs 10m+)
- **Runtime Model Loading**: Successfully moved expensive model downloads from build to runtime
  - PyTorch installation: ~120s moved to runtime
  - SentenceTransformer downloads: ~148s moved to runtime
  - Whisper model downloads: ~10s moved to runtime
  - Tiktoken encoding: ~5s moved to runtime
- **Smart Caching System**: Created `init_models.sh` with intelligent model persistence
- **Volume Mounts**: Model cache directories properly mounted for persistence
- **Development Workflow**: Fast rebuild process documented and working

#### 🏆 Massive API Layer Cleanup (July 27-29, 2025) - COMPLETED
- **Campaign Results**: 24/24 API files processed (100% complete)
- **Lines Eliminated**: 5,426+ lines of repetitive code removed
- **Average Reduction**: 75% code reduction across all files
- **Highest Achievement**: 88% reduction in functions/index.ts (545→67 lines)
- **Pattern**: Identified and eliminated systematic commit padding across entire codebase
- **Enhanced Error Reporting**: Implemented comprehensive error context system

#### 🏆 API Documentation (July 29, 2025) - COMPLETED
- **Swagger UI Enabled**: Configured FastAPI to serve interactive API docs at `/docs`
- **ReDoc Added**: Additional documentation option available
- **Testing Complete**: Verified Swagger UI accessibility and functionality

#### 🏆 Audio Settings Bug Fix (July 28, 2025) - COMPLETED
- **Kokoro.js TTS Fix**: Personal settings now properly respected over global config
- **Testing Complete**: Verified all dtype configurations (fp32, fp16, q8, q4)
- **Documentation**: Created comprehensive fix documentation

### Development Workflow Improvements
- **Enhanced Error Reporting**: Detailed logging for API endpoint failures
- **Code Quality**: Systematic elimination of code bloat and repetitive patterns
- **Documentation**: Comprehensive troubleshooting guides and fix documentation
- **Testing**: Thorough validation of all fixes and improvements

---

*This section contains work completed in current and previous weeks.*
