from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel

app = FastAPI()

data = {}


@app.get("/healthcheck")
def healthcheck():
    return {"message": "I'm alive"}


@app.get("/items/{key}")
def get_item(key: str):
    value = data.get(key)
    if not value:
        raise HTTPException(status_code=404, detail="Item not found")
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
