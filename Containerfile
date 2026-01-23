FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim

RUN apt-get update && \
   apt-get install -y libgl1  libglib2.0-0 build-essential curl git && \
   rm -rf /var/lib/apt/lists/*

ENV APP_HOME="/app/dapabot"
RUN  mkdir -p ${APP_HOME}
WORKDIR ${APP_HOME}
COPY . ${APP_HOME}

# L'applicazione scaricherà al primo avvio tutte le dipendenze neessarie.
# Decommentare l'istruzione seguente per creare un'immagine di circa 9GB con tutte le dipendenze già scaricate.
#RUN uv sync 

EXPOSE 8501

ENTRYPOINT ["uv", "run", "streamlit", "run", "dapabot.py", "--server.port=8501", "--server.address=0.0.0.0"]
