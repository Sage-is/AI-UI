# Sage.Education AI API Tutorial

Welcome to the Sage.Education AI API tutorial! This guide will help you interact with the Sage.Education AI API efficiently. 

## Getting Started

You’ll need an API token for authentication. Follow these steps to get your token.

### Step 1: Authentication

Use the following `curl` command to authenticate and retrieve your token.

Script to store your email and pass as varables for bash scripts. This script asks for your email and password and stores them in variables for use in other scripts.
```bash
read -p "Enter your email: " email &&\
read -sp "Enter your password: " password &&\
echo "export SAGE_EMAIL=$email" > ~/.sage &&\
echo "export SAGE_PASSWORD=$password" >> ~/.sage &&\
export SAGE_EMAIL=$email &&\
export SAGE_PASSWORD=$password 
```

```bash
AUTH_RESPONSE=$(curl -X POST https://sage.startr.cloud/api/v1/auths/signin \
-H 'Content-Type: application/json' \
-d '{
    "email": "$SAGE_EMAIL",
    "password": "$SAGE_PASSWORD"
}')
TOKEN=$(echo $AUTH_RESPONSE | jq -r '.token')
echo "Your token is: $TOKEN"
```
```bash
echo $TOKEN
```

The server will respond with your API token. Save it for later use.

## Step 2: List Available Models

To see all available models, run this command:

```bash
curl -X GET https://sage.startr.cloud/api/models \
-H "Authorization: Bearer $TOKEN"
```


This will show you a list of models accessible via the API.

## Step 3: Create a Chat

Initiate a new chat session with the command below:

```bash
CHAT_RESPONSE=$(curl -X POST https://sage.startr.cloudapi/v1/chats/new \
-H "Authorization: Bearer $TOKEN" \
-H 'Content-Type: application/json' \
-d '{
    "chat": {
        "title": "My New Chat",
        "description": "Starting a conversation about interesting topics."
    }
}')
CHAT_ID=$(echo $CHAT_RESPONSE | jq -r '.id')
```


## Step 4: Send a Message

To send a message through the chat, use:

```bash
curl -X POST https://sage.startr.cloudapi/v1/chats/$CHAT_ID/messages \
-H "Authorization: Bearer $TOKEN" \
-H 'Content-Type: application/json' \
-d '{
    "content": "Why is the sky blue?"
}'
```




## Step 5: Process and Upload Files

Upload a document using this command:

```bash
curl -X POST https://sage.startr.cloud/api/v1/files/ \
-H "Authorization: Bearer your_token" \
-H 'Content-Type: multipart/form-data' \
-F 'file=@/path/to/your/file.txt'
```

### Step 6: Process Document into Vector DB

After uploading documents, process them:

```bash
curl -X POST https://sage.startr.cloud/rag/api/v1/process/doc \
-H "Authorization: Bearer your_token" \
-H 'Content-Type: application/json' \
-d '{
    "file_id": "your_uploaded_file_id",
    "user_id": "your_user_id",
    "collection_name": "your_collection_name"
}'
```

### Using the API in Python

You can also use Python to interact with the API. Here's a quick example for authentication and messaging:

```python
import requests

# Authenticate the user
auth_url = "https://sage.startr.cloud/api/v1/auths/signin"
payload = {
    "email": "your-email@example.com",
    "password": "your_password"
}
response = requests.post(auth_url, json=payload)
token = response.json().get("token")

# Send a message
chat_url = "https://sage.startr.cloud/ollama/api/chat"
message_data = {
    "model": "your_model_name",
    "messages": [{
        "role": "user",
        "content": "Why is the sky blue?"
    }]
}
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(chat_url, json=message_data, headers=headers)
print(response.json())
```

## Conclusion

You now have a solid foundation for using the Sage.Education AI API. Experiment with different endpoints and discover what’s possible. Enjoy building with Sage.Education AI!