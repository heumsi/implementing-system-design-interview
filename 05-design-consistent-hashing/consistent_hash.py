from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import List


def _get_hash(key: str) -> int:
    return int(hashlib.new("sha1", key.encode("utf-8")).hexdigest(), 16)


@dataclass
class Node:
    id: str


@dataclass
class _Node:
    id: str
    hash: int

    @classmethod
    def from_node(cls, node: Node) -> _Node:
        return cls(id=node.id, hash=_get_hash(node.id))

    def to_node(self) -> Node:
        return Node(id=self.id)


class EmptyNodeError(Exception):
    pass


class ConsistentHash:
    def __init__(self, nodes: List[Node]) -> None:
        self.nodes = nodes

        self._nodes = [_Node.from_node(node) for node in nodes]
        self._max_hash = 2**160 - 1

    def get_node_of_key(self, key: str) -> Node:
        if not self.nodes:
            raise EmptyNodeError("There are no nodes. Please add nodes at least 1")
        hash_ = _get_hash(key)
        node_of_key = None
        min_distance = self._max_hash
        for node in self._nodes:
            distance = node.hash - hash_
            if distance < 0:
                distance = self._max_hash - distance
            if not node_of_key or distance < min_distance:
                node_of_key = node
                min_distance = distance
        return node_of_key.to_node()

    def add_node(self, node: Node) -> None:
        self._nodes.append(_Node.from_node(node))

    def remove_node(self, node: Node) -> None:
        node_ = _Node.from_node(node)
        self._nodes.remove(node_)
