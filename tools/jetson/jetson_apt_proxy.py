"""Small HTTP/HTTPS CONNECT proxy for Jetson APT over a Windows PdaNet link.

The server binds only to the Windows side of the Jetson USB network and accepts
connections only from the Jetson address.  It is intentionally minimal: enough
for APT's HTTP downloads and HTTPS CONNECT tunnels.
"""

import asyncio
import contextlib
from urllib.parse import urlsplit, urlunsplit


LISTEN_HOST = "192.168.137.1"
LISTEN_PORT = 3128
ALLOWED_CLIENTS = {"192.168.137.2", "127.0.0.1"}
HEADER_LIMIT = 64 * 1024


async def send_error(writer, status, message):
    body = (message + "\n").encode("utf-8", "replace")
    writer.write(
        f"HTTP/1.1 {status}\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n\r\n".encode("ascii")
        + body
    )
    with contextlib.suppress(Exception):
        await writer.drain()


def split_host_port(value, default_port):
    parsed = urlsplit("//" + value)
    if not parsed.hostname:
        raise ValueError("host is missing")
    return parsed.hostname, parsed.port or default_port


async def copy_stream(reader, writer):
    try:
        while True:
            data = await reader.read(64 * 1024)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass


async def relay(client_reader, client_writer, remote_reader, remote_writer):
    tasks = {
        asyncio.create_task(copy_stream(client_reader, remote_writer)),
        asyncio.create_task(copy_stream(remote_reader, client_writer)),
    }
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    for task in done | pending:
        with contextlib.suppress(Exception, asyncio.CancelledError):
            await task


async def handle_client(client_reader, client_writer):
    peer = client_writer.get_extra_info("peername")
    client_ip = peer[0] if peer else "unknown"

    if client_ip not in ALLOWED_CLIENTS:
        print(f"Reddedildi: {client_ip}")
        client_writer.close()
        with contextlib.suppress(Exception):
            await client_writer.wait_closed()
        return

    remote_writer = None
    try:
        raw_header = await asyncio.wait_for(
            client_reader.readuntil(b"\r\n\r\n"), timeout=30
        )
        if len(raw_header) > HEADER_LIMIT:
            raise ValueError("request header is too large")

        header_text = raw_header.decode("iso-8859-1")
        lines = header_text.split("\r\n")
        method, target, version = lines[0].split(" ", 2)

        if method.upper() == "CONNECT":
            host, port = split_host_port(target, 443)
            print(f"{client_ip} CONNECT {host}:{port}")
            remote_reader, remote_writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=20
            )
            client_writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await client_writer.drain()
            await relay(
                client_reader, client_writer, remote_reader, remote_writer
            )
            return

        headers = []
        host_header = None
        for line in lines[1:]:
            if not line:
                continue
            name, separator, value = line.partition(":")
            if not separator:
                continue
            lowered = name.strip().lower()
            if lowered == "host":
                host_header = value.strip()
            if lowered in {"proxy-connection", "connection"}:
                continue
            headers.append((name.strip(), value.lstrip()))

        parsed_target = urlsplit(target)
        if parsed_target.scheme:
            if parsed_target.scheme.lower() != "http":
                raise ValueError("non-CONNECT requests must use HTTP")
            if not parsed_target.hostname:
                raise ValueError("target host is missing")
            host = parsed_target.hostname
            port = parsed_target.port or 80
            path = urlunsplit(
                ("", "", parsed_target.path or "/", parsed_target.query, "")
            )
        else:
            if not host_header:
                raise ValueError("Host header is missing")
            host, port = split_host_port(host_header, 80)
            path = target

        print(f"{client_ip} {method} http://{host}:{port}{path}")
        remote_reader, remote_writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=20
        )

        outbound = [f"{method} {path} {version}"]
        outbound.extend(f"{name}: {value}" for name, value in headers)
        outbound.append("Connection: close")
        outbound.append("")
        outbound.append("")
        remote_writer.write("\r\n".join(outbound).encode("iso-8859-1"))
        await remote_writer.drain()
        await relay(client_reader, client_writer, remote_reader, remote_writer)

    except asyncio.IncompleteReadError:
        pass
    except Exception as exc:
        print(f"Hata ({client_ip}): {exc}")
        with contextlib.suppress(Exception):
            await send_error(client_writer, "502 Bad Gateway", str(exc))
    finally:
        if remote_writer is not None:
            remote_writer.close()
            with contextlib.suppress(Exception):
                await remote_writer.wait_closed()
        client_writer.close()
        with contextlib.suppress(Exception):
            await client_writer.wait_closed()


async def main():
    server = await asyncio.start_server(
        handle_client,
        LISTEN_HOST,
        LISTEN_PORT,
        limit=HEADER_LIMIT,
    )
    sockets = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"Jetson APT proxy hazir: {sockets}")
    print("Durdurmak icin Ctrl+C basin.")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProxy durduruldu.")
