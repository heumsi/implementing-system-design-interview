FROM python:3.10.6-slim-buster

COPY ./requirements.txt /code/requirements.txt
COPY ./src /code/src

ENV PYTHONPATH=/code
WORKDIR /code

RUN pip install -r requirements.txt
ENV PORT=80

CMD python src/main.py
