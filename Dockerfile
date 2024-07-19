FROM python:3.11

WORKDIR /code/

COPY ./requirements.txt /code/

RUN apt-get update && apt-get install -y ffmpeg

RUN pip install -r requirements.txt

RUN pip install git+https://github.com/openai/whisper.git
RUN pip install git+https://github.com/pyannote/pyannote-audio.git

COPY . /code/
