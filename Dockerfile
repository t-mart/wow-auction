FROM python:3.11-slim

# rich's log output defaults to super small 80 otherwise
ENV COLUMNS=200

WORKDIR /app

# cache deps
COPY requirements.txt /app
RUN set -ex \
    && pip install -r /app/requirements.txt

# ok, now that deps are cached, actually copy the module.
COPY src/wowauction /app/wowauction

# -u gives us unbuffered python, so we don't need to flush stdout in order to
# see it in the container logs
CMD ["python", "-u", "-m", "wowauction"]
