# 07-design-a-unique-id-generator-in-distributed-systems

## Tech Spec

### Goal

Implement a unique id generator for distributed system.

### Requirements

- ID must be unique
- ID must consist of numbers only
- ID must be a value that can be expressed in 64 bits
- IDs must be sortable by issue date
- Must be able to create 10,000 IDs per second (Optional)

### Considerations

- The generator can be in the form of a library or a web API.
- If you can consider clock synchronization, please consider it.

## Usage

### Installation

Pre-requisites are as follows.

- python >= 3.11
- clone this repo

Install as follows.

```bash
$ poetry install
```

### How To Use

```python
>>> from snowflake_id_generator import SnowflakeIdGenerator
>>> id_generator = SnowflakeIdGenerator(data_center_id=1, machine_id=1)
>>> id_generator.generate()
16242262776259678208
```

## System design

I implemented Snowflake ID.

![](https://springmicroservices.com/wp-content/uploads/2022/08/Twitter-Snowflake-ID-sections-1.png)
