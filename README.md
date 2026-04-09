
# ABXYZ Multi Chatting Portal

This project provides a basic TCP chat server and client system, where multiple users can join channels, send direct messages, and interact in a live chat environment.

## Table of Contents
- [Requirements](#requirements)
- [How to Run](#how-to-run)
  - [Running the Server](#running-the-server)
  - [Running the Client](#running-the-client)
- [Commands](#commands)

## Requirements
- Python 3.6 or higher
- `colorama` and `prompt_toolkit` libraries. You can install them using the following command:
  ```bash
  pip install colorama prompt_toolkit
  ```

## How to Run

### Running the Server
To start the server, run the `server.py` script. You can specify a port for the server, or it will default to `7777`.

```bash
python server.py [PORT]
```

- The default port is `7777`, but you can specify a different port by providing it as an argument (e.g., `python server.py 8080`).
- Once started, the server will listen for incoming client connections.

### Running the Client
To connect to the server, run the `client.py` script. You can specify the server's IP address and port, or it will default to `127.0.0.1:7777`.

```bash
python client.py [SERVER_IP] [PORT]
```

- The default server IP is `127.0.0.1` and the default port is `7777`. 
- Once connected, you will be prompted to enter a nickname and can start chatting with other users.

## Commands

Once connected to the server, users can use the following commands within the chat:

- `/nick <name>`: Change your nickname.
- `/join <channel>`: Join a new chat channel.
- `/msg <nick> <message>`: Send a private message to another user.
- `/list`: List all available chat channels.
- `/who`: List all users in the current channel.
- `/quit` or `/exit`: Exit the chat.

