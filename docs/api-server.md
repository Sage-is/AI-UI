---
title: "Use AI-UI as an API server"
description: "Call AI-UI's OpenAI-compatible chat API from curl or an SDK."
date: 2026-11-25
tags:
  - api
  - docs
  - guide
---

# Use AI-UI as an API server

AI-UI speaks the OpenAI chat API, so any program or SDK that talks to OpenAI can talk to a box.

Your program sends a question to the box. The box hands it to a model, then sends the model's answer back.

You need three things: the box's address, a key, and a model id.

A key is a secret string that proves your program is allowed to use the box.

A model id is the exact name the box uses to identify a model.

## Get started

1. Get a key. Open the user menu, then Settings → Account → API keys, and click Create new secret key. The key appears in the API Key field and looks like `sk-...`. Treat it like a password. If the API keys section is missing, an admin opens Admin Panel → Settings → Auth (Beta), turns on Enable API Key, and saves.

2. Tell your shell where the box is and what the key is. Put your box's address in place of the example. The `read` command waits for you: paste the key and press Enter. Nothing shows on screen, and the key stays out of your shell history.

   ```sh
   export SAGE_URL="https://your-box.example" && read -rs SAGE_API_KEY && export SAGE_API_KEY
   ```

3. Check that the key works. This returns the account the key belongs to.

   ```sh
   curl -sS -H "Authorization: Bearer $SAGE_API_KEY" "$SAGE_URL/api/v1/auths/"
   ```

4. List the models your account may use. `jq` prints just the id of each one.

   ```sh
   curl -sS -H "Authorization: Bearer $SAGE_API_KEY" "$SAGE_URL/api/models" | jq -r '.data[].id'
   ```

   Pick one and keep it, copied exactly:

   ```sh
   export SAGE_MODEL="paste-an-id-from-the-list"
   ```

5. Ask one question and wait for the whole answer. `jq -n` builds the request with your model id filled in, and `-d @-` tells curl to send what `jq` built. The last `jq` prints only the answer text.

   ```sh
   jq -n --arg model "$SAGE_MODEL" '{model: $model, messages: [{role: "user", content: "What is 2 plus 2?"}], stream: false}' \
     | curl -sS -H "Authorization: Bearer $SAGE_API_KEY" -H "Content-Type: application/json" -d @- "$SAGE_URL/api/chat/completions" \
     | jq -r '.choices[0].message.content'
   ```

6. Ask the same question with streaming. Streaming sends the answer in small pieces while the model writes it. `-N` tells curl to show each piece as it arrives.

   ```sh
   jq -n --arg model "$SAGE_MODEL" '{model: $model, messages: [{role: "user", content: "What is 2 plus 2?"}], stream: true}' \
     | curl -sS -N -H "Authorization: Bearer $SAGE_API_KEY" -H "Content-Type: application/json" -d @- "$SAGE_URL/api/chat/completions"
   ```

   Each piece is one line that starts with `data:`. The last line is `data: [DONE]`. Shortened, they look like this:

   ```text
   data: {"object":"chat.completion.chunk","choices":[{"delta":{"content":"2 plus 2"}}]}
   data: {"object":"chat.completion.chunk","choices":[{"delta":{"content":" is 4."}}]}
   data: [DONE]
   ```

## Use an OpenAI SDK

Set `SAGE_URL`, `SAGE_API_KEY` and `SAGE_MODEL` as above. Point the SDK's base URL at `$SAGE_URL/api`. Everything else works as it does with OpenAI.

Python:

```python
import os
from openai import OpenAI

client = OpenAI(base_url=f"{os.environ['SAGE_URL']}/api", api_key=os.environ["SAGE_API_KEY"])
reply = client.chat.completions.create(model=os.environ["SAGE_MODEL"], messages=[{"role": "user", "content": "What is 2 plus 2?"}])
print(reply.choices[0].message.content)
```

JavaScript:

```javascript
import OpenAI from "openai";

const client = new OpenAI({ baseURL: `${process.env.SAGE_URL}/api`, apiKey: process.env.SAGE_API_KEY });
const reply = await client.chat.completions.create({ model: process.env.SAGE_MODEL, messages: [{ role: "user", content: "What is 2 plus 2?" }] });
console.log(reply.choices[0].message.content);
```

## Ask about your documents

The box can read your files and answer from them. It searches a file for the parts that match your question and gives those parts to the model with the question.

Upload one file. Put your file's path after the `@`. The box reads the file during this request, so the file is ready when the command returns. The command keeps the file's id in `FILE_ID`.

```sh
FILE_ID=$(curl -sS -H "Authorization: Bearer $SAGE_API_KEY" -F "file=@notes.pdf" "$SAGE_URL/api/v1/files/" | jq -r '.id') && echo "$FILE_ID"
```

Ask about the file. The `files` list attaches it to the question.

```sh
jq -n --arg model "$SAGE_MODEL" --arg file "$FILE_ID" '{model: $model, messages: [{role: "user", content: "What does this file say?"}], files: [{type: "file", id: $file}]}' \
  | curl -sS -H "Authorization: Bearer $SAGE_API_KEY" -H "Content-Type: application/json" -d @- "$SAGE_URL/api/chat/completions" \
  | jq -r '.choices[0].message.content'
```

A knowledge base is a named group of files. Attach it once and the box searches all of its files. Create one and keep its id in `KNOWLEDGE_ID`:

```sh
KNOWLEDGE_ID=$(curl -sS -H "Authorization: Bearer $SAGE_API_KEY" -H "Content-Type: application/json" -d '{"name":"Project notes","description":"Notes for this project"}' "$SAGE_URL/api/v1/knowledge/create" | jq -r '.id') && echo "$KNOWLEDGE_ID"
```

Add an uploaded file to it. Upload and add once for each file.

```sh
jq -n --arg file "$FILE_ID" '{file_id: $file}' \
  | curl -sS -H "Authorization: Bearer $SAGE_API_KEY" -H "Content-Type: application/json" -d @- "$SAGE_URL/api/v1/knowledge/$KNOWLEDGE_ID/file/add"
```

Ask with the knowledge base attached. Its type is `collection`.

```sh
jq -n --arg model "$SAGE_MODEL" --arg kb "$KNOWLEDGE_ID" '{model: $model, messages: [{role: "user", content: "What do these files say about the project?"}], files: [{type: "collection", id: $kb}]}' \
  | curl -sS -H "Authorization: Bearer $SAGE_API_KEY" -H "Content-Type: application/json" -d @- "$SAGE_URL/api/chat/completions" \
  | jq -r '.choices[0].message.content'
```

To send a file's whole text instead of the matching parts, add `context: "full"` to its item: `{type: "file", id: $file, context: "full"}`.

## Before you ship

- A key has its owner's role and model permissions. It does not grant extra access. A person has one key, and creating a replacement key replaces the old one.
- An admin can limit a key to listed routes. A route matches itself or a path below it. An empty allowed-route list allows nothing.
- Use `POST /api/chat/completions` for chat. There is no `/api/v1/chat/completions` route.
- Use the model id exactly as listed by `/api/models`. A connection prefix can be part of the id, and non-admins see only models they can use.
- The chat route runs the privacy filter. Before a message leaves for a hosted model, the filter swaps names and other private values for stand-ins. It puts the real values back in the answer. The filter is on by default for external connections, and admins set it at `/pages/admin/privacy`.
- To hide a value the filter does not know, name it in the request: `"privacy": {"known": [{"kind": "surname", "value": "Silva"}]}`.
- **Warning:** the raw `/openai/...` and `/ollama/...` routes skip the privacy filter. Send every chat through `/api/chat/completions`.
- Leave out `chat_id`, `id`, and `session_id`. If you send all three, the reply holds only a task id, and the answer goes to the web UI instead of your program. Without them, you get a plain OpenAI reply, and nothing is saved to chat history.
- When the box finds matching parts in your files, a streamed answer starts with a `sources` event that has no `choices`. Skip any chunk without `choices`. A non-streamed reply puts `sources` at the top level.
- The knowledge routes return 503 when the vector-chroma Sprig is not installed. An admin can install it from Admin → Sprigs. Non-admins also need the workshop knowledge permission, which is off by default.
- A file-processing problem can return status 200 with an `error` field. There is no status endpoint to poll.
- The box sets no rate limits of its own. The model provider behind it may.

## Errors

| Status | What it means | What to do |
| --- | --- | --- |
| 403 `Not authenticated` | The request carried no key. | Send `Authorization: Bearer $SAGE_API_KEY`. |
| 403 `Use of API key is not enabled in the environment.` | An admin has turned API keys off. | Ask an admin to turn on Enable API Key. |
| 403 on a chat | Your account may not use that model. | Pick an id from your own `/api/models` list. |
| 401 | The box does not know the key. | Copy your current key. A new key replaces the old one. |
| 400 | The model id is not known. | Copy the id exactly from `/api/models`. |
| 503 | Knowledge-base routes are not ready because the vector-chroma Sprig is missing. | Ask an admin to install the vector-chroma Sprig. |
| 200 with an `error` field | File processing failed even though the HTTP request succeeded. | Read the error in the reply and correct the file or request. |

## See every route

Open `$SAGE_URL/docs` in a browser. It lists every route with its fields, and you can try each one there. `/openapi.json` holds the same list for code generators. Account → API keys links to it too.
