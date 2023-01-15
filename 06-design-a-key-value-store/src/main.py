import uvicorn
from fastapi import FastAPI

from src.api import private, public
from src.global_vars import config

# parser = ArgumentParser()
# parser.add_argument("-c", "--config", help="config file (.yaml) path")
# args, unknown = parser.parse_known_args()
# if args.config:
#     config = Config.from_yaml(args.config)
# else:
#     config = Config()


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(private.router)
    app.include_router(public.router)
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("main:app", host=config.host, port=config.port, workers=1)
