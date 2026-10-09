---
title: "Troubleshooting Guide"
description: "Common issues and solutions for Sage.is AI-UI deployment and configuration."
date: 2025-11-28
tags:
  - troubleshooting
  - deployment
  - docker
  - ollama
---

# Sage.is AI-UI Troubleshooting Guide

## Understanding the Sage.is AI-UI Architecture

The Sage.is AI-UI system is designed to streamline interactions between the client (your browser) and the Ollama API. At the heart of this design is a backend reverse proxy, enhancing security and resolving CORS issues.

- **How it Works**: The Sage.is AI-UI is designed to interact with the Ollama API through a specific route. When a request is made from the WebUI to Ollama, it is not directly sent to the Ollama API. Initially, the request is sent to the Sage.is AI-UI backend via `/ollama` route. From there, the backend is responsible for forwarding the request to the Ollama API. This forwarding is accomplished by using the route specified in the `OLLAMA_BASE_URL` environment variable. Therefore, a request made to `/ollama` in the WebUI is effectively the same as making a request to `OLLAMA_BASE_URL` in the backend. For instance, a request to `/ollama/api/tags` in the WebUI is equivalent to `OLLAMA_BASE_URL/api/tags` in the backend.

- **Security Benefits**: This design prevents direct exposure of the Ollama API to the frontend, safeguarding against potential CORS (Cross-Origin Resource Sharing) issues and unauthorized access. Requiring authentication to access the Ollama API further enhances this security layer.

## Sage.is AI-UI: Server Connection Error

Inside a container, `127.0.0.1` is the container itself, not your computer. Ollama listens on your computer at port 11434, so the container reaches it at `http://host.docker.internal:11434`.

On a Mac, Colima is the default runtime (a krunkit VM on Apple Silicon), and Docker Desktop and OrbStack are supported too: pick one with `ai-ui start --runtime` or `sage-runtime use`. All three resolve `host.docker.internal` to your Mac. Linux does not, so pass `--add-host=host.docker.internal:host-gateway` there. The flag does no harm on a Mac:

```bash
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v sage-ai-data:/app/backend/data -e OLLAMA_BASE_URL=http://host.docker.internal:11434 --name sage-ai --restart always ghcr.io/sage-is/ai-ui:latest
```

On Linux, Ollama listens only on `127.0.0.1` by default. A container's request arrives from the docker bridge, so Ollama refuses it. Make it listen beyond loopback: set `OLLAMA_HOST=0.0.0.0` (for the systemd service, `sudo systemctl edit ollama`, then restart it). That opens Ollama to your network too, so keep a firewall in front of port 11434.

On Linux only, `--network=host` works too. The container then shares the host's network, so `OLLAMA_BASE_URL=http://127.0.0.1:11434` reaches Ollama, and the app answers at `http://localhost:8080` instead of port 3000. On a Mac, containers run inside a VM, so host networking reaches the VM, not the Mac.

### Error on Slow Responses for Ollama

Sage.is AI-UI has a default timeout of 5 minutes for Ollama to finish generating the response. If needed, this can be adjusted via the environment variable AIOHTTP_CLIENT_TIMEOUT, which sets the timeout in seconds.

### General Connection Errors

**Ensure Ollama Version is Up-to-Date**: Always start by checking that you have the latest version of Ollama. Visit [Ollama's official site](https://ollama.com/) for the latest updates.

**Troubleshooting Steps**:

1. **Verify Ollama URL Format**:
   - When running the Web UI container, ensure the `OLLAMA_BASE_URL` is correctly set. (e.g., `http://192.168.1.1:11434` for different host setups).
   - In the Sage.is AI-UI, navigate to "Settings" > "General".
   - Confirm that the Ollama Server URL is correctly set to `[OLLAMA URL]` (e.g., `http://host.docker.internal:11434 `).

By following these enhanced troubleshooting steps, connection issues should be effectively resolved. For further assistance or queries, feel free to reach out to us on our community Discord.
