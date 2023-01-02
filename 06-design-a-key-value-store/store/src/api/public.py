from typing import Any
from urllib.parse import urljoin

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from requests import get, post, put
from src.api.private import AddPeersRequest, InitializeItemsRequest
from src.global_vars import config, items, peer_urls
from starlette import status
from starlette.responses import Response

router = APIRouter(tags=["public"])


@router.get("/healthcheck")
def healthcheck():
    return {"message": "I'm alive"}


@router.get("/items/{key}")
def get_item(key: str):
    value = items.get(key)
    if not value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )
    return {"value": value}


class PutItemRequest(BaseModel):
    value: Any


@router.put("/items/{key}")
def put_item(key: str, request: PutItemRequest, response: Response):
    response.status_code = status.HTTP_201_CREATED
    if items.get(key):
        response.status_code = status.HTTP_200_OK
    items[key] = request.value
    for peer_url in peer_urls:
        response = put(
            urljoin(str(peer_url), url=f"/_items/{key}"),
            json=PutItemRequest(
                value=request.value,
            ).dict(),
        )
        if response.status_code not in (status.HTTP_200_OK, status.HTTP_201_CREATED):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Something was wrong",
            )
        # TODO: All exception handling must be considered better
    return {"key": key, "value": items[key]}


class AddPeerRequest(BaseModel):
    peer_url: HttpUrl


@router.post("/peers")
def add_peer(request: AddPeerRequest):
    if request.peer_url == config.http_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot add yourself as a peer",
        )
    if request.peer_url in peer_urls:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This peer has already been added",
        )

    # Request adding me and my peers to the peer in request
    response = post(
        urljoin(str(request.peer_url), url="/_peers"),
        json=AddPeersRequest(peer_urls=[config.http_url] + list(peer_urls)).dict(),
    )
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something was wrong",
        )

    # Request adding the peer in request to my peers
    for peer_url in peer_urls:
        response = post(
            urljoin(peer_url, "/_peers"),
            json=AddPeersRequest(peer_urls=[request.peer_url]).dict(),
        )
        if response.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Something was wrong",
            )

    # Request initialization items to the peer in request
    response = post(
        urljoin(str(request.peer_url), url="/_items/initialize"),
        json=InitializeItemsRequest(items=items).dict(),
    )
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something was wrong",
        )
    # TODO: Consideration should be given to the case of large sizes.

    # Add the peer in request into my peer list
    peer_urls.add(request.peer_url)

    # TODO: All exception handling must be considered better

    return {"message": "The peer has been successfully added."}


@router.get("/peers")
def get_peers():
    return {"peers": list(peer_urls)}


@router.get("/peers/healthcheck")
def healthcheck_peers():
    peer_url_to_result = {}
    for peer_url in peer_urls:
        response = get(
            urljoin(peer_url, "/healthcheck"),
        )
        if response.status_code == status.HTTP_200_OK:
            peer_url_to_result[peer_url] = "success"
        else:
            peer_url_to_result[peer_url] = "failure"
    return peer_url_to_result
