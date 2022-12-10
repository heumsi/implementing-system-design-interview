from typing import Literal

from pydantic import BaseSettings


class Config(BaseSettings):
    class Common(BaseSettings):
        forward_host: str = "127.0.0.1"
        forward_port: int = 8080
        socket_buf_size: int = 1024

    class LeakyBucket(BaseSettings):
        periodic_second: int = 1
        n_request_to_be_processed_per_periodic_second: int = 2
        request_queue_size: int = 2

    class TokenBucket(BaseSettings):
        periodic_second: int = 1
        n_tokens_to_be_added_per_periodic_second: int = 2
        token_bucket_size: int = 2

    common: Common = Common()
    rate_limit_algorithm: Literal["token bucket", "leaky bucket"] = "leaky bucket"
    leaky_bucket: LeakyBucket = LeakyBucket()
    token_bucket: TokenBucket = TokenBucket()
