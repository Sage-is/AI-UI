## 🔥 Current Active Tasks (March 12, 2026)

### 🔴 Deployment Simplification & Homebrew Tap - HIGHEST PRIORITY
- [x] Delete `docker-compositions/` (6 Ollama-specific overlay files)
- [x] Delete `app/scripts/run-compose.sh` (replaced by Makefile targets)
- [x] Create simplified root `docker-compose.yaml` (single-service, Podman-compatible)
- [x] Update Makefile: `CONTAINER_RUNTIME` auto-detection (podman > docker), clean Ollama refs
- [ ] **Tag release and push to GHCR** — `make minor_release` then `make it_build_multi_arch_push_GHCR`
- [ ] **Verify image pullable** — `podman pull ghcr.io/sage-is/ai-ui:latest`
- [ ] **Push `Sage-is/homebrew-apps` repo to GitHub** — Formula + `ai-ui` CLI wrapper created locally
- [ ] **Update `sha256` in `Formula/ai-ui.rb`** after tagging v0.1.0 of homebrew-apps
- [ ] CapRover one-click template (lower priority, `captain-definition` already works)

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

### 🔴 CI/CD Security Scanning (Makefile-driven) - IN PROGRESS
- [ ] **Local security scanning via Makefile targets** (no vendor lock-in, runs on Linux/macOS/WSL)
  - [ ] `make install_dev` — install gitleaks, semgrep/opengrep, bandit, trivy, pre-commit
  - [x] `make scan` — umbrella target running all scans below
  - [x] `make scan_secrets` — gitleaks secrets detection
  - [x] `make scan_sast` — semgrep (JS/TS/Svelte) + bandit (Python) static analysis
  - [x] `make scan_deps` — trivy dependency vulnerability scanning
  - [ ] `make scan_container` — trivy container image scanning (post-build)
  - [ ] `make lint` — rollup for eslint + prettier + black
  - [ ] `.pre-commit-config.yaml` — git hooks via pre-commit framework (gitleaks, bandit, codespell)
  - [ ] `.semgrep/` local offline rules (Python, JS/TS, Svelte security patterns)
- [ ] **Staging CapRover + DAST (future TODO)**
  - [ ] Set up second CapRover instance for staging
  - [ ] Selenium-driven browser regression tests against staging
  - [ ] SikuliX visual/UI regression testing
  - [ ] OWASP ZAP as proxy during Selenium runs for DAST coverage
  - [ ] `make scan_dast` — gate production promotion on staging pass

### 🔶 Docker Build Enhancements - NOT STARTED
- [ ] **Docker multi-stage build**: Still single FROM stage, build tools ship in production image
  - [ ] Implement multi-stage build with separate builder and runtime stages
  - [ ] Further build time optimizations (currently 5m52s vs 10m+)
  - [ ] Document fast development rebuild workflow

### 🟢 Channel → Space DB Migration - LOW PRIORITY
- [ ] **Complete the "channel" → "space" rename at the database level**
  - The code-level rename is done (models, routers, socket events, frontend all use "space"). DB schema still uses the old "channel" naming. Grep for `TODO(low)` to find all affected locations.
  - [ ] Alembic migration: rename table `channel` → `space`
  - [ ] Alembic migration: rename column `message.channel_id` → `message.space_id`
  - [ ] Alembic migration: rename bridge columns `channel_id` → `space_id`, `sage_channel_id` → `sage_space_id`
  - [ ] Alembic migration: rename bridge mode value `"channel_bridge"` → `"space_bridge"` in existing rows
  - [ ] Update ORM class `Channel` → `Space` in `models/spaces.py` and `__tablename__`
  - [ ] Update all Pydantic field names from `channel_id` to `space_id`
  - [ ] Update frontend `message.channel_id` references to `message.space_id`
  - [ ] Rename `components/channel/` directory to `components/space/` and update all import paths
  - [ ] Update i18n translation keys (old "Channel Name" → "Space Name" etc.)

### 🔶 HTML Cleanup Initiative - NOT STARTED
- [ ] **Replace redundant wrapper divs with unregistered custom elements** to improve semantic clarity
  - [ ] Audit components for unnecessary wrapper `<div>` elements
  - [ ] Replace with descriptive custom elements (e.g. `<chat-header>`, `<sidebar-nav>`, `<model-card>`)
  - [ ] Establish naming convention: lowercase, hyphenated, project-scoped where needed
  - [ ] Reduce associated CSS resets caused by generic div nesting
  - [ ] Verify no layout/style regressions after replacements

### 🔶 API Documentation Enhancement - PARTIAL
- [ ] **Complete Swagger UI Configuration**: Basic setup done, enhancements remain
  - [x] Swagger UI enabled and accessible at `/docs`
  - [ ] Configure Swagger UI with custom styling and branding
  - [ ] Document how to access and use the API documentation
  - [ ] Ensure proper authentication handling in Swagger UI

---

> **Archived items**: See [`docs/completed-todos.md`](docs/completed-todos.md) for verified-completed and stale/resolved tasks.

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
  - [x] Add `Shared with me` and `Shared by me` as new sidebar categories
  - [x] Ensure both categories are linked and present filtered shared-chat views

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
