FROM docker

RUN apk add --no-cache python3 && \
    ln -sf python3 /usr/bin/python && \
    ln -sf pip3 /usr/bin/pip

WORKDIR /usr/src/drone-plugin
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENTRYPOINT [ "python", "/usr/src/drone-plugin/ecr-build-push.py" ]
