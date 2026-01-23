FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim

RUN apt-get update && \
   apt-get install -y libgl1  libglib2.0-0 build-essential curl git && \
   rm -rf /var/lib/apt/lists/*

ENV APP_HOME="/app/dapabot"
RUN  mkdir -p ${APP_HOME}
WORKDIR ${APP_HOME}
COPY . ${APP_HOME}

RUN uv sync 

EXPOSE 8501

ENTRYPOINT ["uv", "run", "streamlit", "run", "dapabot.py", "--server.port=8501", "--server.address=0.0.0.0"]
