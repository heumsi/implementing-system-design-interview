from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, HttpUrl
from src.global_vars import peer_urls
from starlette import status
from starlette.responses import Response

router = APIRouter(tags=["private"])


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


@router.post("/_items/initialize")
def initialize_items(request: InitializeItemsRequest):
    # TODO: Consideration should be given to the case of large sizes.
    global items
    items = request.items
    return {"message": "Items have been initialized successfully."}


class AddPeersRequest(BaseModel):
    peer_urls: List[HttpUrl]


@router.post("/_peers")
def add_peers(request: AddPeersRequest):
    for peer_url in request.peer_urls:
        peer_urls.add(peer_url)

    return {"message": "The peers have been successfully added."}
