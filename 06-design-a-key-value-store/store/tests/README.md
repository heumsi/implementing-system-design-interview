# Tests

Tests that are difficult to write in test code will be written in this document.

## Add peers

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

## Healthcheck peers

### Given

Same as given and when of "Add peers" test.

### When

```bash
curl localhost:8888/peers/healthcheck
```

### Then

```bash
{"http://0.0.0.0:9999":"success","http://0.0.0.0:7777":"success"}
```

## Put item

### Given

Same as given and when of "Add peers" test.

### When

```
curl -X PUT 0.0.0.0:8888/items -H "Content-Type: application/json" -d '{"key":"foo", "value": "bar"}'
```

### Then

```
{"key", "foo", value":"bar"}
```

```
curl 0.0.0.0:8888/items/foo
{"value":"bar"}

curl 0.0.0.0:7777/items/foo
{"value":"bar"}

curl 0.0.0.0:9999/items/foo
{"value":"bar"}
```
