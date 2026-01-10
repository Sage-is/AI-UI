# Sage WebUI

## v1.1.1 *our first public release*

**Sage.is an AI interface that puts you in control.**

[![GitHub stars](https://img.shields.io/github/stars/Startr/WEB-AI-Sage-WebUI?style=social)](https://github.com/Sage-is/AI-UI)
[![License](https://img.shields.io/github/license/Startr/WEB-AI-Sage-WebUI)](LICENSE)
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
cd WEB-AI-Sage-WebUI
make it_run
```

Open [http://localhost:8080](http://localhost:8080) and create your admin account.

### Docker Compose

```bash
git clone https://github.com/Sage-is/AI-UI.git
cd WEB-AI-Sage-WebUI
docker compose -f docker-compositions/docker-compose.yaml up -d
```

### Docker (Manual)

```bash
docker run -d -p 3000:8080 \
  -v sage-webui:/app/backend/data \
  --name sage-webui \
  --restart always \
  ghcr.io/startr/sage-webui:latest
```

## Available Make Commands

- `make it_run` — Start Sage WebUI with Docker
- `make it_stop` — Stop running containers
- `make it_build` — Build Docker images
- `make it_clean` — Clean up containers and images
- `make help` — Show all available commands

## Core Features

- **Multi-Model Chat** — Switch between different AI models in the same conversation
- **Document RAG** — Upload PDFs, docs, and websites directly into your chats
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


## Documentation

- [Installation Guide](./docs/INSTALLATION.md)
- [Configuration Options](./docs/README.md)
- [API Reference](./API/examples.md)
- [Development Workflow](./docs/DEVELOPMENT_WORKFLOW.md)
- [API Refactoring Plan](./docs/API_REFACTORING_PLAN.md)
- [Contributing](./docs/CONTRIBUTING.md)
- [Bug Fixes & Improvements](./docs/) — Historical documentation of major fixes
  - [Kokoro.js TTS Fix (July 28, 2025)](./docs/KOKORO_TTS_FIX_2025-07-28.md)

## Community

- **Discord:** [Join our community](https://discord.gg/5rJgdTnV4s)
- **Model Hub:** [Sage.Education](https://sage.education/models) — Download custom models and prompts
- **Issues:** [Report bugs](https://github.com/Sage-is/AI-UI/issues)

## License

[Apache 2.0 License](LICENSE)

---

Built by [Startr](https://startr.cloud/) and contributors worldwide.
