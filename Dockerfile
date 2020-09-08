FROM docker

RUN apk add --update --no-cache curl py-pip

WORKDIR /usr/src/drone-plugin
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENTRYPOINT [ "python", "/usr/src/drone-plugin/ecr-build-push.py" ]
