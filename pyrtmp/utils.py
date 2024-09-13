import socket


def net_addr_to_string(family, addr):
    if s.family == socket.AF_INET:
        return f"{addr[0]}:{addr[1]}"

    elif s.family == socket.AF_INET6:
        return f"[{addr[0]}]:{addr[1]}"

    return str(addr)

