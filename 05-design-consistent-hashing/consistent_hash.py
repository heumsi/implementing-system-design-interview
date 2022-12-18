from dataclasses import dataclass
from typing import List


@dataclass
class Node:
    id: int


class ConsistentHash:
    def __init__(self, hash_algorithm: str, nodes: List[Node]) -> None:
        self.hash_algorithm = hash_algorithm
        self.nodes = nodes

    def get_node_of_key(self, key: str) -> Node:
        ...

    def add_node(self, node: Node) -> None:
        self.nodes.append(node)

    def remove_node(self, node: Node) -> None:
        self.nodes.remove(node)
