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
