# Product Stack Diagram

The diagram below illustrates client → frontend → backend flows, data stores, AI providers, and infra.

```mermaid
graph TD
  subgraph Client
    UA[User Browser]
  end

  subgraph Frontend["SvelteKit WebUI"]
    UI[Svelte + Tailwind]
    SSE[SSE + Fetch]
    WS[Socket.IO Client]
  end

  UA --> UI

  subgraph Backend["FastAPI Open WebUI"]
    API[REST API + SSE]
    WSS[Socket.IO Server]
    Auth[Auth: JWT/OAuth]
    RAG[RAG + Tools/Functions]
  end

  UI -->| REST/SSE | API
  WS <--> | WebSocket | WSS

  subgraph Data["Data Stores"]
    DB[(SQLite/Postgres via Peewee)]
    Redis[(Redis: cache + websockets)]
    Vector[(Vector DB: Chroma / Qdrant / Milvus)]
    Blob[(Blob Storage: Local / GCS / Azure)]
    ModelCache[(Model Cache: embeddings / whisper / tiktoken)]
  end

  API -->| JWT/OAuth | Auth
  WSS -->| session/pubsub | Redis
  API -->| cache | Redis
  API -->| ORM | DB
  API -->| vectors | Vector
  API -->| files | Blob
  API -->| init/use | ModelCache

  subgraph AI["AI + Media"]
    Emb[Embeddings: SentenceTransformers]
    STT[faster-whisper (STT)]
    TTS[TTS: Kokoro.js / Web Speech / OpenAI]
    LLMs{LLM Providers}
  end

  API -->| embeddings | Emb
  API -->| speech → text | STT
  API -->| text → speech | TTS
  API -->| LLM calls | LLMs

  subgraph Providers["External Providers"]
    Ollama[Ollama]
    OpenAI[OpenAI]
    Anthropic[Anthropic]
    Groq[Groq]
    Bing[Bing]
    SerpAPI[SerpAPI]
    Firecrawl[Firecrawl]
    ExtSearch[External Search API]
  end

  LLMs --> Ollama
  LLMs --> OpenAI
  LLMs --> Anthropic
  LLMs --> Groq

  API -->| web search | Bing
  API --> SerpAPI
  API --> Firecrawl
  API --> ExtSearch

  subgraph Infra["Infra"]
    Compose[Docker Compose]
    Proxy[Reverse Proxy: Apache/Nginx]
    OTel[OpenTelemetry Instrumentation]
  end

  Compose -. deploy .-> UI
  Compose -. deploy .-> API
  Proxy -. TLS/WS/SSE .-> UI

```
