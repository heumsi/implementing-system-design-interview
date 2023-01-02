from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from starlette import status
from starlette.responses import Response

from src.core.consistent_hash import Node
from src.global_vars import consistent_hash, items, peer_urls

router = APIRouter(tags=["private"])


@router.get("/_items/{key}")
def get_item(key: str):
    value = items.get(key)
    if not value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )
    return {"value": value}


class PutItemRequest(BaseModel):
    value: Any


@router.put("/_items/{key}")
def put_item(key: str, request: PutItemRequest, response: Response):
    response.status_code = status.HTTP_201_CREATED
    if items.get(key):
        response.status_code = status.HTTP_200_OK
    items[key] = request.value
    return {"key": key, "value": items[key]}


class InitializeItemsRequest(BaseModel):
    items: Dict[str, Any]


# @router.post("/_items/initialize")
# def initialize_items(request: InitializeItemsRequest):
#     # TODO: Consideration should be given to the case of large sizes.
#     global items
#     items = request.items
#     return {"message": "Items have been initialized successfully."}


class AddPeersRequest(BaseModel):
    peer_urls: List[HttpUrl]


@router.post("/_peers")
def add_peers(request: AddPeersRequest):
    for peer_url in request.peer_urls:
        peer_urls.add(peer_url)
        consistent_hash.add_node(node=Node(id=peer_url))

    return {"message": "The peers have been successfully added."}
