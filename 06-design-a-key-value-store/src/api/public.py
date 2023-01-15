from typing import Any
from urllib.parse import urljoin

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from requests import get, post, put
from starlette import status

from src.api.private import AddPeersRequest
from src.core.consistent_hash import Node
from src.global_vars import config, consistent_hash, peer_urls

router = APIRouter(tags=["public"])


@router.get("/healthcheck")
def healthcheck():
    return {"message": "I'm alive"}


# TODO: 노드가 추가될 때, 기존 노드들에서 데이터가 이동해야 함.
# 두 가지 작업이 이뤄져아할거 같음.
# 1. 기존 노드에서 데이터를 새 노드로 bulk put 한다.
# 2. 기존 노드에서 데이터를 삭제한다.
# 3. peer list에 노드를 추가한다.


@router.get("/items/{key}")
def get_item(key: str):
    # Get nodes to request to put item
    nodes = consistent_hash.get_nodes_of_key(key, n_nodes=config.n_copy)

    # Get value of key from the nodes
    values = set()
    for node in nodes:
        url = node.id
        response = get(
            urljoin(str(url), url=f"/_items/{key}"),
        )
        if response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )
        if response.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Something was wrong",
            )
        value = response.json()["value"]
        values.add(value)

    # Check all values are same
    if len(values) != 1:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something was wrong",
        )

    return {"value": next(iter(values))}


class PutItemRequest(BaseModel):
    value: Any


@router.put("/items/{key}")
def put_item(key: str, request: PutItemRequest):
    # Get nodes to request to put item
    nodes = consistent_hash.get_nodes_of_key(key, n_nodes=config.n_copy)

    # Request the nodes to to put item
    # TODO: HTTP Request should be performed asynchronously.
    for node in nodes:
        url = node.id
        response = put(
            urljoin(str(url), url=f"/_items/{key}"),
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
    return {"key": key, "value": request.value}


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
    # response = post(
    #     urljoin(str(request.peer_url), url="/_items/initialize"),
    #     json=InitializeItemsRequest(items=items).dict(),
    # )
    # if response.status_code != status.HTTP_200_OK:
    #     raise HTTPException(
    #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #         detail="Something was wrong",
    #     )
    # TODO: Consideration should be given to the case of large sizes.

    # Add the peer in request into my peer list
    peer_urls.add(request.peer_url)

    # TODO: All exception handling must be considered better

    # Add the peer in request into my consistent hash
    consistent_hash.add_node(node=Node(id=request.peer_url))

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
