FROM python:3.11-slim

WORKDIR /app

# cache deps, so that we don't need to redownload each time we have a code
# change (and thus, will be rebuilding the image)
COPY requirements.txt /app
RUN set -ex \
    && pip install -r /app/requirements.txt

# ok, now that deps are cached, actually copy the module.
COPY src/wowauction /app/wowauction

# -u gives us unbuffered python, so we don't need to flush stdout in order to
# see it in the container logs
CMD ["python", "-u", "-m", "wowauction"]
