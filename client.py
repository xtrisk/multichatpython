import socket
import threading
import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.shortcuts import print_formatted_text
from colorama import init, Fore, Style

init(autoreset=True)


# Applies color to a message based on its prefix type
def colorize(message: str) -> str:
    if message.startswith("[CLIENT]"):
        return Fore.CYAN + message + Style.RESET_ALL
    if message.startswith("[SERVER]"):
        return Fore.YELLOW + message + Style.RESET_ALL
    if message.startswith("[PM from"):
        return Fore.MAGENTA + message + Style.RESET_ALL
    if message.startswith("[PM to"):
        return Fore.RED + message + Style.RESET_ALL
    if message.startswith("[#"):
        bracket_end = message.index("]") + 1
        return Fore.GREEN + message[:bracket_end] + Style.RESET_ALL + message[bracket_end:]
    return message


# Listens for incoming messages from the server and prints them to the terminal
def receive_messages(sock):
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                print_formatted_text(ANSI(colorize("[CLIENT] Server closed the connection.")))
                break
            for line in data.decode("utf-8").splitlines(keepends=True):
                print_formatted_text(ANSI(colorize(line.rstrip("\n"))))
        except Exception:
            print_formatted_text(ANSI(colorize("[CLIENT] Disconnected from server.")))
            break


# Connects to the server, handles login, then enters the interactive message loop
def main():
    if len(sys.argv) < 2:
        host = input(Fore.CYAN + "Server IP [127.0.0.1]: " + Style.RESET_ALL).strip() or "127.0.0.1"
    else:
        host = sys.argv[1]

    port = int(sys.argv[2]) if len(sys.argv) > 2 else 7777

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
    except Exception as e:
        print(colorize(f"[CLIENT] Could not connect to {host}:{port} — {e}"))
        return

    # Handles the nickname prompt exchange before entering the chat
    while True:
        try:
            data = sock.recv(4096).decode("utf-8")
        except Exception:
            print(colorize("[CLIENT] Disconnected during login."))
            sock.close()
            return
        print(Fore.CYAN + data + Style.RESET_ALL, end="", flush=True)
        if data.rstrip().endswith(":"):
            try:
                nickname = input().strip()
            except KeyboardInterrupt:
                sock.close()
                sys.exit(0)
            if not nickname:
                nickname = "Anonymous"
            sock.sendall(nickname.encode("utf-8"))
        else:
            break

    t = threading.Thread(target=receive_messages, args=(sock,), daemon=True)
    t.start()

    # Starts the interactive prompt and sends user input to the server
    session = PromptSession()
    try:
        with patch_stdout():
            while True:
                try:
                    msg = session.prompt(ANSI(Fore.GREEN + "> " + Style.RESET_ALL))
                except (EOFError, KeyboardInterrupt):
                    sock.close()
                    sys.exit(0)
                if not msg:
                    continue
                if msg.lower() in ("/quit", "/exit"):
                    sock.sendall(msg.encode("utf-8"))
                    break
                sock.sendall(msg.encode("utf-8"))
    finally:
        sock.close()
        print(colorize("[CLIENT] Disconnected."))


if __name__ == "__main__":
    main()