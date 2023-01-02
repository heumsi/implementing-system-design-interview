from src.config import Config
from src.core.consistent_hash import ConsistentHash, Node

# TODO: all global vars should be stored in database (ex. sqlite) for multi web workers and persistence
items = {}
peer_urls = set()
config = Config()
consistent_hash = ConsistentHash(nodes=[Node(id=config.http_url)])
