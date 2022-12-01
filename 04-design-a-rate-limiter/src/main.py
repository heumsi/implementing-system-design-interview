import logging
import socket
from concurrent.futures import ThreadPoolExecutor

LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 8000
FORWARD_HOST = "127.0.0.1"
FORWARD_PORT = 8080
BUF_SIZE = 1024
LOG_LEVEL = "DEBUG"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
MAX_WORKERS = 10

logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(stream_handler)


def process(connection_socket, client_address):
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
    logger.debug(f"send data to client {client_address[0]}:{client_address[1]}")
    connection_socket.send(data)


with socket.socket() as server_socket:
    server_socket.bind((LISTEN_HOST, LISTEN_PORT))
    server_socket.listen()
    logger.info(f"start listening on {LISTEN_HOST}:{LISTEN_PORT}")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while True:
            try:
                connection_socket, client_address = server_socket.accept()
                executor.submit(process, connection_socket, client_address)
            except KeyboardInterrupt:
                print("gracefully exit ...")
                break
        print("good bye!")
