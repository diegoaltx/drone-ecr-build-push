# drone-ecr-build-push
A Drone plugin for building a Docker image and push it to Amazon ECR.

This plugin is built to suit only a specific workflow which meets some assumptions:

- Docker images are always tagged with commit-[commit hash] on ECR.
- Images are pushed only to ECR repositories on your on account. 

It supports replication across ECR registries on multiple AWS regions.

# Usage

```
steps:
  - name: "Build and push Docker image"
    image: diegoaltx/drone-ecr-build-push:1
    settings:
      regions:
        - us-east-1
        - sa-east-1
      repo: microservice-example
      dockerfile: ./Dockerfile
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    when:
      ref:
        - refs/heads/feature/*
        - refs/heads/bugfix/*
        - refs/heads/hotfix/*
```

## Settings

| Key                              | Description                                  |
|----------------------------------|----------------------------------------------|
| **regions** *required*           | ECR registries regions.                      |
| **repo** *optional*              | ECR repo name. Defaults to git repo name.    |
| **dockerfile** *optional*        | Dockerfile path. Defaults to `./Dockerfile`. |
| **access_key_id** *optional*     | AWS access key id.                           |
| **secret_access_key** *optional* | AWS secret access key.                       |
