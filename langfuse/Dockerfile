FROM docker:28.3.0-dind-alpine3.22

RUN apk add --no-cache docker-compose

ENV LANGFUSE_VERSION=3.146.0

RUN apk add --no-cache git
RUN git clone https://github.com/langfuse/langfuse.git

WORKDIR /langfuse
RUN git checkout v${LANGFUSE_VERSION}

COPY docker-compose.override.yaml docker-compose.override.yaml

CMD docker-compose up
