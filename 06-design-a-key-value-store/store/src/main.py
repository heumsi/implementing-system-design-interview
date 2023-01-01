from argparse import ArgumentParser
from typing import Any, List
from urllib.parse import urljoin

import uvicorn
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, HttpUrl
from requests import post
from src.config import Config

parser = ArgumentParser()
parser.add_argument("-c", "--config", help="config file (.yaml) path")
args, unknown = parser.parse_known_args()
if args.config:
    config = Config.from_yaml(args.config)
else:
    config = Config()


app = FastAPI()

data = {}
peer_urls = set()


@app.get("/healthcheck")
def healthcheck():
    return {"message": "I'm alive"}


@app.get("/items/{key}")
def get_item(key: str):
    value = data.get(key)
    if not value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )
    return {"value": value}


class PutItemRequest(BaseModel):
    value: Any


@app.put("/items/{key}")
def put_item(key: str, request: PutItemRequest, response: Response):
    response.status_code = status.HTTP_201_CREATED
    if data.get(key):
        response.status_code = status.HTTP_200_OK
    data[key] = request.value
    return {"value": data[key]}


class AddPeersByInternalRequest(BaseModel):
    peer_urls: List[HttpUrl]


@app.post("/_peers")
def add_peers_by_internal(request: AddPeersByInternalRequest):
    for peer_url in request.peer_urls:
        peer_urls.add(peer_url)

    return {"message": "The peers have been successfully added."}


class AddPeerByExternalRequest(BaseModel):
    peer_url: HttpUrl


@app.post("/peers")
def add_peer_by_external(request: AddPeerByExternalRequest):
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
        json=AddPeersByInternalRequest(
            peer_urls=[config.http_url] + list(peer_urls)
        ).dict(),
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
            json=AddPeersByInternalRequest(peer_urls=[request.peer_url]).dict(),
        )
        if response.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Something was wrong",
            )
    # TODO: All exception handling must be considered better

    # Add the peer in request into my peer list
    peer_urls.add(request.peer_url)

    return {"message": "The peer has been successfully added."}


@app.get("/peers")
def get_peers():
    return {"peers": list(peer_urls)}


if __name__ == "__main__":
    uvicorn.run(app, host=config.host, port=config.port)
