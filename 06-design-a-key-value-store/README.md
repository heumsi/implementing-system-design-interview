# 06-design-a-key-value-store

## Tech Spec

### Goal

Implement a distributed key-value store.

### Requirements

- Must be able to partition data using stable hashes.
- Must be able to multiplex data to N servers.
- A quorum consensus protocol must be used to ensure data consistency.
- Inconsistency must be resolved by using versioning and vector clocks.
- Must be able to deal with at least one of the following types of disabilities.
    - Must be able to detect failures using gossip protocols.
    - Temporary failures are handled by prohibiting write/read operations or by using temporary consignment techniques.
    - Handle permanent failure by implementing anti-entropy protocol using Merkle Tree.
- Must provide a write function that supports commit logs and SSTables.
- A reading function using a bloom filter must be provided.
- At least one of the techniques or protocols below must be implemented.
    - Quorum consensus protocol (ex. quorum)
    - Gossip protocol (ex. non-renewal allowed time)
    - Anti-entropy protocol (ex. number of buckets)
    - Versioning and vector clock (ex. Threshold for the number of [server:version] ordered pairs)
    - Temporary consignment technique
- Settings related to the techniques or protocols below must be able to be modified without interruption.
    - Quorum consensus protocol (ex. quorum)
    - Gossip protocol (ex. non-renewal allowed time)
    - Anti-entropy protocol (ex. number of buckets)
    - Versioning and vector clock (ex. Threshold for the number of [server:version] ordered pairs)
- The implemented algorithm must be testable by anyone, and the document on which the test was conducted must remain.

## Usage

### Installation

Pre-requisites are as follows.

- python >= 3.10
- clone this repo

Install as follows.

```bash
$ poetry install
```

### How To Use

#### 1. Deplyoment

Deploy the 3 servers, each in a different shell, as follows

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

#### 2. Add Peers

Add deployed servers as peers of each other, as follows

```bash
curl -X POST localhost:8888/peers -H "Content-Type: application/json" -d '{"peer_url":"http://0.0.0.0:7777"}'
curl -X POST localhost:8888/peers -H "Content-Type: application/json" -d '{"peer_url":"http://0.0.0.0:9999"}'
```

#### 3. Put Item

Put an item to the server

```bash
curl -X PUT 0.0.0.0:8888/items/foo -H "Content-Type: application/json" -d '{"value": "bar"}'
```

When you enter data on one server, it is also entered on the rest of your fellow servers.

### 4. Get Item

Get the item from the server where you put before.

```bash
curl 0.0.0.0:7777/items/foo
{"value":"bar"}

curl 0.0.0.0:8888/items/foo
{"value":"bar"}

curl 0.0.0.0:9999/items/foo
{"value":"bar"}
```

> For more API usage, see the server's /docs endpoint. (ex. `localhost:8888/docs`)

## System design

TBD
