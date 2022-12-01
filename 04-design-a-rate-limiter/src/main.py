import logging
import socket
from time import sleep
import threading


LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 8000
FORWARD_HOST = "127.0.0.1"
FORWARD_PORT = 8080
BUF_SIZE = 1024
LOG_LEVEL = "DEBUG"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
MAX_REQUESTS_PER_SECOND = 2

logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(stream_handler)

available = MAX_REQUESTS_PER_SECOND  # this will be reset periodically in set_available()


def process(connection_socket, client_address):
    try:
        with socket.socket() as forward_socket:
            data = connection_socket.recv(BUF_SIZE)
            decoded_data = data.decode()
            logger.debug(f"got data from client {client_address[0]}:{client_address[1]}: {decoded_data}")
            logger.debug(f"start to connect forward server {FORWARD_HOST}:{FORWARD_PORT}")
            forward_socket.connect((FORWARD_HOST, FORWARD_PORT))
            logger.debug(f"send data to forward server {FORWARD_HOST}:{FORWARD_PORT}")
            forward_socket.send(data)
            data = forward_socket.recv(BUF_SIZE)
            decoded_data = data.decode()
            logger.debug(f"got data from forward server {FORWARD_HOST}:{FORWARD_PORT}: {decoded_data}")
        logger.debug(f"send data to client {client_address[0]}{client_address[1]}")
        connection_socket.send(data)
    finally:
        connection_socket.close()


def set_available():
    while True:
        global available
        available = MAX_REQUESTS_PER_SECOND
        sleep(5)


with socket.socket() as server_socket:
    set_available_thread = threading.Thread(target=set_available)
    set_available_thread.start()
    server_socket.bind((LISTEN_HOST, LISTEN_PORT))
    server_socket.listen()
    logger.info(f"start listening on {LISTEN_HOST}:{LISTEN_PORT}")
    while True:
        try:
            connection_socket, client_address = server_socket.accept()
            if available > 0:
                available -= 1
                process_thread = threading.Thread(target=process, args=(connection_socket, client_address))
                process_thread.start()
            else:
                try:
                    content = "Please retry after minutes"
                    header = '\n'.join([
                        "HTTP/1.1 429 Too many requests",
                        "\n".join(f"{k}: {v}" for k, v in {
                            'Content-Type': 'text/plan; encoding=utf8',
                            'Content-Length': len(content),
                            'Connection': 'close',
                        }.items())
                    ])
                    data = "\n\n".join([header, content])
                    connection_socket.send(data.encode('utf-8'))
                finally:
                    connection_socket.close()
        except KeyboardInterrupt:
            print("gracefully exit ...")
            break
print("good bye!")
