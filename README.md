# Sage WebUI

## v1.1.1 *our first public release*

**Sage.is an AI interface that puts you in control.**

[![GitHub stars](https://img.shields.io/github/stars/Sage-is/AI-UI?style=social)](https://github.com/Sage-is/AI-UI)
[![License](https://img.shields.io/badge/License-AGPL_v3%2B-blue)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Community-blue?logo=discord&logoColor=white)](https://discord.gg/3BtwHkXS)

Sage WebUI transforms how you interact with AI. Built for privacy and flexibility, it runs entirely on your infrastructure while supporting the latest AI models from Ollama, OpenAI, and beyond.

![Demo](./demo.gif)

## Why Sage WebUI?

**Privacy First** — Your conversations never leave your server. Complete data sovereignty.

**Universal Compatibility** — Works with Ollama, OpenAI, Anthropic, and any OpenAI-compatible API.

**Built for Teams** — Granular permissions, user groups, and role-based access control.

**Extensible** — Plugin architecture, custom functions, and RAG integration out of the box.

## Quick Start

### Using Make (Recommended)

```bash
git clone https://github.com/Sage-is/AI-UI.git
cd AI-UI
make it_build_n_run
```


Now open [http://localhost:8080](http://localhost:8080) and create your admin account.

If you want to do front end dev and see changes to svelte files live, go instead to [http://localhost:5173/](http://localhost:5173/) as this will update on file change.


## Available Make Commands

- `make it_run` — Start Sage WebUI with Docker
- `make it_stop` — Stop running containers
- `make it_build` — Build Docker images
- `make it_clean` — Clean up containers and images
- `make waha_start` — Start WAHA (WhatsApp bridge) locally
- `make waha_stop` — Stop WAHA container
- `make help` — Show all available commands

## Core Features

- **Multi-Model Chat** — Switch between different AI models in the same chat or even talk to multiple AI models at the same time
- **Knowledge Bases** — Create RAG-powered AIs by uploading PDFs, docs, and websites directly into your chats or into Workshop Knoweldge
- **Messaging Bridges** — Connect external platforms like WhatsApp directly to Sage AI for chat or channel mirroring ([docs](./docs/bridges.md))
- **Code Execution** — Built-in Python environment with custom function support
- **Voice & Video** — Hands-free conversations with speech-to-text and text-to-speech
- **Image Generation** — Integrate DALL-E, ComfyUI, or AUTOMATIC1111
- **Progressive Web App** — Works offline, installs like a native app
- **Enterprise Ready** — SSO, LDAP, detailed audit logs

## Configuration

Sage WebUI works out of the box, but you can customize it:

**Environment Variables:**
- `OPENAI_API_KEY` — Connect to OpenAI models
- `ANTHROPIC_API_KEY` — Enable Claude models  
- `OLLAMA_BASE_URL` — Point to your Ollama instance
- `ENABLE_RAG` — Enable document processing (default: true)


## Styling

Sage WebUI uses [Startr.Style](https://startr.style) — a utility-complete CSS framework under 50KB (8KB gzipped). Instead of class-based utilities, Startr.Style uses inline CSS custom properties for full access to the CSS spec with zero compilation:

```html
<div style="--d:flex; --ai:center; --g:1rem; --p:1rem; --br:0.5rem">
  <button style="--bg:var(--color-sky-500); --c:white; --hvr-bg:var(--color-sky-600)">
    Click me
  </button>
</div>
```

See [Startr.Style docs](https://startr.style) for the full property reference, responsive suffixes (`-sm`, `-md`, `-lg`, `-xl`), dark mode (`--dark-*`), and hover states (`--hvr-*`).

## Documentation


- [Configuration Options](./docs/README.md)
- [Messaging Bridges (WhatsApp, etc.)](./docs/bridges.md)
- [API Reference](./API/examples.md)
- [Development Workflow](./docs/DEVELOPMENT_WORKFLOW.md)
- [API Refactoring Plan](./docs/api-refactoring-plan.md)
- [Contributing](./docs/CONTRIBUTING.md)
- [Bug Fixes & Improvements](./docs/) — Historical documentation of major fixes
  - [Kokoro.js TTS Fix (July 28, 2025)](./docs/kokoro-tts-fix-2025-07-28.md)

## Community

- **Discord:** [Join our community](https://discord.gg/#TODO)
- **Issues:** [Report bugs](https://github.com/Sage-is/AI-UI/issues)

## License

[GNU Affero General Public License v3](LICENSE)

The GNU Affero General Public License (AGPL) v3 is used here because this project (Sage WebUI) is a web-based AI interface that runs as a network service, and AGPL ensures that any modifications or derivative works—especially those deployed online—must also be open-sourced under the same license. This prevents proprietary exploitation of the codebase while allowing free use and modification.

It protects developers by:

- Enforcing copyleft: Any changes or extensions to the software must be shared back with the community, preserving the open-source nature and preventing companies from taking the code private without contributing improvements.
- Safeguarding against SaaS loopholes: Unlike GPL, AGPL closes the "SaaS loophole" by requiring source code availability for network-accessible versions, ensuring users can access and modify the software even when it's hosted as a service.
- Promoting collaboration: It encourages contributions by guaranteeing that enhancements benefit everyone, reducing the risk of forks diverging into incompatible proprietary versions.
- Legal clarity: It provides strong protections against patent claims and ensures freedom to run, study, share, and modify the code, with no warranties but clear liability limits.

This aligns with the project's privacy-first ethos, as it keeps AI interfaces open and accountable. If you meant a different license or aspect, clarify.

---

Built with [Startr.Style](https://startr.style) by [Sage.is](https://sage.is) (*part of [Startr](https://startr.cloud/)*) and contributors worldwide.
