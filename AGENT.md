**Dependency Management with uv**: use `uv sync` to install dependencies and `uv run` to execute *all* Python commands in the virtual environment

**Testing the server**: A Django server is already running locally at 127.0.0.1:8000. You can use `curl` command to issue GET and POST requests to test the server functionality. You can review the server log at funhanzi/django.log to find any errors. Before you issue another request, you can use `> funhanzi/django.log` command to truncate the log.

**Running locally**: 
```
. .env
uv run src/manage.py runserver
```

**Podman**: 
```
podman build -t funhanzi .
podman run -p 8000:8000 --env-file ./.env funhanzi
```

# Development Best Practices

## Gemini API Usage

When interacting with the Gemini API, please use the `google.genai` library. This is the preferred and modern library for this project. The older `google.generativeai` library is deprecated and should not be used.

### Example

Here is an example of the correct way to use the `google.genai` library in this project:

```python
from google import genai

# Get the client
client = genai.Client()

# Generate content
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Translate the following Chinese words to English: '你好世界'.",
)

print(response.text)
```
