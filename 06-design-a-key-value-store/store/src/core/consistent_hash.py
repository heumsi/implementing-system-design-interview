from __future__ import annotations

import hashlib
import itertools
from dataclasses import dataclass
from typing import List


def _get_hash(key: str) -> int:
    return int(hashlib.new("sha1", key.encode("utf-8")).hexdigest(), 16)


@dataclass
class Node:
    id: str


@dataclass
class _VNode:
    id: int
    node: _Node


@dataclass
class _Node:
    id: str
    n_vnodes: int

    @classmethod
    def from_node(cls, node: Node, n_vnodes: int) -> _Node:
        return cls(id=node.id, n_vnodes=n_vnodes)

    def to_node(self) -> Node:
        return Node(id=self.id)

    @property
    def vnodes(self) -> List[_VNode]:
        return [
            _VNode(id=_get_hash(f"{self.id}.{i}"), node=self)
            for i in range(self.n_vnodes)
        ]


class EmptyNodeError(Exception):
    pass


class ConsistentHash:
    def __init__(self, nodes: List[Node], n_vnodes_per_node: int = 200) -> None:
        self.n_virtual_nodes_per_node = n_vnodes_per_node

        self._nodes = [_Node.from_node(node, n_vnodes_per_node) for node in nodes]
        self._sorted_vnodes = self._get_sorted_vnodes()

    @property
    def nodes(self) -> List[Node]:
        return [_node.to_node() for _node in self._nodes]

    def get_node_of_key(self, key: str) -> Node:
        if not self.nodes:
            raise EmptyNodeError("There are no nodes. Please add nodes at least 1")
        hash_ = _get_hash(key)
        for vnode in self._sorted_vnodes:
            if vnode.id >= hash_:
                return vnode.node.to_node()
        return self._sorted_vnodes[0].node.to_node()

    def get_nodes_of_key(self, key: str, n_nodes: int) -> List[Node]:
        if not self.nodes:
            raise EmptyNodeError("There are no nodes. Please add nodes at least 1")
        hash_ = _get_hash(key)

        _nodes = []
        for vnode in self._sorted_vnodes:
            if vnode.id >= hash_ and vnode.node not in _nodes:
                _nodes.append(vnode.node)
                if len(_nodes) == min(n_nodes, len(self.nodes)):
                    break
        return [_node.to_node() for _node in _nodes]

    def add_node(self, node: Node) -> None:
        node_ = _Node.from_node(node, self.n_virtual_nodes_per_node)
        self._nodes.append(node_)
        self._sorted_vnodes = self._get_sorted_vnodes()

    def remove_node(self, node: Node) -> None:
        node_ = _Node.from_node(node, self.n_virtual_nodes_per_node)
        self._nodes.remove(node_)
        self._sorted_vnodes = self._get_sorted_vnodes()

    def _get_sorted_vnodes(self) -> List[_VNode]:
        return sorted(
            list(itertools.chain(*[node.vnodes for node in self._nodes])),
            key=lambda vnode: vnode.id,
        )
