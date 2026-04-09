import socket
import threading
import sys
import urllib.request
from colorama import init, Fore, Style

init(autoreset=True)

HOST = "0.0.0.0"
PORT = 7777

HEADER = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════╗
║           ABXYZ  —  Multi Chatting Portal            ║
║                    TCP Chat Server                   ║
╚══════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""

lock = threading.Lock()
clients = {}
channels = {}


# Colored logging helpers for different severity levels
def log_info(msg):
    print(Fore.CYAN + f"[SERVER] {msg}" + Style.RESET_ALL)

def log_success(msg):
    print(Fore.GREEN + f"[SERVER] {msg}" + Style.RESET_ALL)

def log_warn(msg):
    print(Fore.YELLOW + f"[SERVER] {msg}" + Style.RESET_ALL)

def log_error(msg):
    print(Fore.RED + f"[SERVER] {msg}" + Style.RESET_ALL)

def log_event(msg):
    print(Fore.MAGENTA + f"[SERVER] {msg}" + Style.RESET_ALL)


# Sends a message to all clients in a channel, skipping the excluded connection
def broadcast(channel, message, exclude=None):
    with lock:
        targets = list(channels.get(channel, []))
    for conn in targets:
        if conn is not exclude:
            try:
                conn.sendall(message.encode("utf-8"))
            except Exception:
                remove_client(conn)


# Sends a message to a single client, removes them if the send fails
def send_to(conn, message):
    try:
        conn.sendall(message.encode("utf-8"))
    except Exception:
        remove_client(conn)


# Removes a client from the server, notifies their channel, and closes the socket
def remove_client(conn):
    with lock:
        info = clients.pop(conn, None)
        if info:
            ch = info["channel"]
            if ch in channels:
                channels[ch].discard(conn)
                if not channels[ch]:
                    del channels[ch]
    if info:
        log_warn(f"{info['nick']} disconnected.")
        broadcast(info["channel"], f"[SERVER] {info['nick']} has left the channel.\n")
    try:
        conn.close()
    except Exception:
        pass


# Moves a client to a new channel and notifies both the old and new channel
def join_channel(conn, new_channel):
    with lock:
        info = clients.get(conn)
        if info is None:
            return
        old_channel = info["channel"]
        if old_channel in channels:
            channels[old_channel].discard(conn)
            if not channels[old_channel]:
                del channels[old_channel]
        info["channel"] = new_channel
        channels.setdefault(new_channel, set()).add(conn)
        nick = info["nick"]

    if old_channel != new_channel:
        broadcast(old_channel, f"[SERVER] {nick} has left the channel.\n")
    broadcast(new_channel, f"[SERVER] {nick} has joined #{new_channel}.\n")
    send_to(conn, f"[SERVER] You are now in #{new_channel}.\n")
    log_info(f"{nick} moved from #{old_channel} to #{new_channel}")


# Handles the full lifecycle of a connected client — nickname setup and command loop
def handle_client(conn, addr):
    log_info(f"New connection from {addr}")
    send_to(conn, "Welcome! Enter your nickname: ")

    while True:
        try:
            nick = conn.recv(4096).decode("utf-8").strip()
            if not nick:
                nick = f"User{addr[1]}"
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return

        with lock:
            taken = any(info["nick"] == nick for info in clients.values())

        if not taken:
            break

        log_warn(f"{addr} tried nickname '{nick}' — already in use.")
        send_to(conn, f"[SERVER] Nickname '{nick}' is already in use. Try another: ")

    default_channel = "general"
    with lock:
        clients[conn] = {"nick": nick, "channel": default_channel, "addr": addr}
        channels.setdefault(default_channel, set()).add(conn)

    log_success(f"{nick} joined from {addr}")
    broadcast(default_channel, f"[SERVER] {nick} has joined #{default_channel}.\n", exclude=conn)
    send_to(conn, f"[SERVER] Hello {nick}! You are in #{default_channel}.\n")
    send_to(conn, "[SERVER] Commands: /nick <name> | /join <channel> | /msg <nick> <text> | /list | /who | /quit\n")

    while True:
        try:
            data = conn.recv(4096)
            if not data:
                break
            message = data.decode("utf-8").strip()
            if not message:
                continue
        except Exception:
            break

        if message.startswith("/nick "):
            new_nick = message[6:].strip()
            if not new_nick:
                send_to(conn, "[SERVER] Usage: /nick <name>\n")
            else:
                with lock:
                    taken = any(
                        info["nick"] == new_nick
                        for c, info in clients.items()
                        if c is not conn
                    )
                if taken:
                    send_to(conn, f"[SERVER] Nickname '{new_nick}' is already in use.\n")
                else:
                    with lock:
                        old_nick = clients[conn]["nick"]
                        clients[conn]["nick"] = new_nick
                        ch = clients[conn]["channel"]
                    nick = new_nick
                    log_info(f"{old_nick} renamed to {new_nick}")
                    broadcast(ch, f"[SERVER] {old_nick} is now known as {new_nick}.\n")

        elif message.startswith("/join "):
            new_ch = message[6:].strip()
            if new_ch:
                join_channel(conn, new_ch)
            else:
                send_to(conn, "[SERVER] Usage: /join <channel>\n")

        elif message.startswith("/msg "):
            parts = message[5:].strip().split(" ", 1)
            if len(parts) < 2:
                send_to(conn, "[SERVER] Usage: /msg <nick> <message>\n")
            else:
                target_nick, pm_text = parts
                with lock:
                    target_conn = next(
                        (c for c, info in clients.items() if info["nick"] == target_nick),
                        None
                    )
                if target_conn:
                    send_to(target_conn, f"[PM from {nick}] {pm_text}\n")
                    send_to(conn, f"[PM to {target_nick}] {pm_text}\n")
                else:
                    send_to(conn, f"[SERVER] User '{target_nick}' not found.\n")

        elif message == "/list":
            with lock:
                ch_list = ", ".join(f"#{c}({len(members)})" for c, members in channels.items())
            send_to(conn, f"[SERVER] Channels: {ch_list}\n")

        elif message == "/who":
            with lock:
                ch = clients[conn]["channel"]
                members = [clients[c]["nick"] for c in channels.get(ch, [])]
            send_to(conn, f"[SERVER] Users in #{ch}: {', '.join(members)}\n")

        elif message in ("/quit", "/exit"):
            send_to(conn, "[SERVER] Goodbye!\n")
            break

        else:
            with lock:
                ch = clients[conn]["channel"]
            broadcast(ch, f"[#{ch}] {nick}: {message}\n", exclude=conn)

    remove_client(conn)


# Notifies all clients of shutdown and closes every open connection
def shutdown_all_clients():
    with lock:
        conns = list(clients.keys())
    for conn in conns:
        try:
            conn.sendall("[SERVER] Server is shutting down. Goodbye!\n".encode("utf-8"))
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
    with lock:
        clients.clear()
        channels.clear()


# Fetches the server's public IP using ipify for display on startup
def get_public_ip():
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as res:
            return res.read().decode("utf-8").strip()
    except Exception:
        return "unavailable"


# Sets up the TCP socket, then accepts and dispatches clients to threads
def main():
    print(HEADER)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    local_ip = get_public_ip()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, port))
    server.listen()
    server.settimeout(1.0)

    log_success(f"Listening on {HOST}:{port}")
    log_info(f"Public IP : {local_ip}:{port}")
    log_info("Press Ctrl+C to stop.")

    try:
        while True:
            try:
                conn, addr = server.accept()
            except socket.timeout:
                continue
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        log_event("\nShutting down — disconnecting all clients...")
        shutdown_all_clients()
        log_success("Done.")
    finally:
        server.close()


if __name__ == "__main__":
    main()