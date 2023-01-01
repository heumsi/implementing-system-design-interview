# Tests

Tests that are difficult to write in test code will be written in this document.

## 1. When a peer is added to a node, the peer is also added to the peers of that node.

### Given

```bash
export PYTHONPATH=.
export PORT=7777
python src/main.py
```

```bash
export PYTHONPATH=.
export PORT=8888
python src/main.py
```

```bash
export PYTHONPATH=.
export PORT=9999
python src/main.py
```

### When

```bash
curl -X POST localhost:8888/peers -H "Content-Type: application/json" -d '{"peer_url":"http://0.0.0.0:7777"}'
curl -X POST localhost:8888/peers -H "Content-Type: application/json" -d '{"peer_url":"http://0.0.0.0:9999"}'
```

### Then

```bash
curl localhost:7777/peers
{"peers":["http://0.0.0.0:9999","http://0.0.0.0:8888"]}

curl localhost:8888/peers
{"peers":["http://0.0.0.0:7777","http://0.0.0.0:9999"]}

 curl localhost:9999/peers
{"peers":["http://0.0.0.0:8888","http://0.0.0.0:7777"]}
```

## 2. Healthcheck peers

### Given

Same as given and when of first test.

### When

```bash
curl localhost:8888/peers/healthcheck
```

### Then

```bash
{"http://0.0.0.0:9999":"success","http://0.0.0.0:7777":"success"}
```

## 3. When you add an item to a node, it is also added to that node's peers.

### Given

Same as given and when of first test.

### When

```bash
curl -X PUT 0.0.0.0:8888/items -H "Content-Type: application/json" -d '{"key":"foo", "value": "bar"}'
```

### Then

```bash
{"key", "foo", value":"bar"}
```

```bash
curl 0.0.0.0:8888/items/foo
{"value":"bar"}

curl 0.0.0.0:7777/items/foo
{"value":"bar"}

curl 0.0.0.0:9999/items/foo
{"value":"bar"}
```

## 4. When a peer is added to a node, the peer's items are initialized with the node's items.

### Given

Same as given and when of third test.
And add the following situation.

```bash
export PYTHONPATH=.
export PORT=6666
python src/main.py
```

### When

```bash
curl -X POST localhost:8888/peers -H "Content-Type: application/json" -d '{"peer_url":"http://0.0.0.0:6666"}'
```

### Then

```bash
{"message":"The peer has been successfully added."}
```

```bash
curl 0.0.0.0:6666/items/foo
{"value":"bar"}
```
