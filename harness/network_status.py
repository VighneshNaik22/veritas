import socket


FORCE_OFFLINE = False


def is_online(host="8.8.8.8", port=53, timeout=1.5):
    if FORCE_OFFLINE:
        return False
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
