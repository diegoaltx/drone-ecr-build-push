import docker
import boto3
import os
import sys
import base64
from datetime import datetime, timezone

def get_docker_client():
  return docker.from_env()

def get_ecr_clients(settings):
  clients = []
  
  for region in settings['regions']:
    clients.append(boto3.client('ecr',
      aws_access_key_id=settings['access_key_id'],
      aws_secret_access_key=settings['secret_access_key'],
      region_name=region
    ))

  return clients

def get_sts_client(settings):
  return boto3.client('sts', 
    aws_access_key_id=settings['access_key_id'],
    aws_secret_access_key=settings['secret_access_key']
  )

def exit_with_error(message, *args):
  print('Something went wrong:', message.format(*args), file=sys.stderr)
  sys.exit(1)

def get_aws_account_id(sts_client):
  return sts_client.get_caller_identity().get('Account')

def get_regions(env):
  regions = env.get('PLUGIN_REGION')

  if not regions:
    return None
  
  return regions.split(',')

def get_repo(env):
  return env.get('PLUGIN_REPO', env.get('DRONE_REPO_NAME'))

def get_dockerfile(env):
  return env.get('PLUGIN_DOCKERFILE', './Dockerfile')

def get_tags(env):
  user_tags = env.get('PLUGIN_TAGS')
  tags = [tag for tag in user_tags.split(',')]
  
  return tags

def get_settings(env):
  return {
    'access_key_id': env.get('PLUGIN_ACCESS_KEY_ID'),
    'secret_access_key': env.get('PLUGIN_SECRET_ACCESS_KEY'),
    'regions': get_regions(env),
    'repo': get_repo(env),
    'dockerfile': get_dockerfile(env),
    'commit': env.get('DRONE_COMMIT'),
    'repo_link': env.get('DRONE_REPO_LINK'),
    'tags': get_tags(env)
  }

def get_ecr_login(ecr_client, registry_id):
  response = ecr_client.get_authorization_token(registryIds=[registry_id])
  registry = response['authorizationData'][0]['proxyEndpoint']
  token = response['authorizationData'][0]['authorizationToken']
  username, password = base64.b64decode(token).decode().split(':')

  return {
    'username': username,
    'password': password,
    'registry': registry
  }

def get_repos(settings, ecr_clients, aws_account_id):
  repos = []

  for client in ecr_clients:
    response = client.describe_repositories(
      registryId=aws_account_id,
      repositoryNames=[settings['repo']]
    )
    repo = response['repositories'][0]
    repos.append({
      'registry_id': repo['registryId'],
      'name': repo['repositoryName'],
      'uri': repo['repositoryUri'],
      'login': get_ecr_login(client, repo['registryId'])
    })

  return repos

def login_to_registries(docker_client, repos):
  for repo in repos:
    login = repo['login']
    
    docker_client.login(
      login['username'], 
      login['password'], 
      registry=login['registry']
    )

def build_image(docker_client, settings):
  build_tag = ':'.join((settings['repo'], settings['tags'][0]))
  build_date = datetime.now(timezone.utc).astimezone().isoformat()

  image, *_ = docker_client.images.build(
    path="./",
    tag=build_tag,
    dockerfile=settings['dockerfile'],
    rm=True,
    pull=True,
    forcerm=True,
    buildargs={
      'CI_BUILD_DATE': build_date,
      'CI_VCS_URL': settings['repo_link'],
      'CI_VCS_REF': settings['commit']
    },
    labels={
      'org.label-schema.schema-version': '1.0',
      'org.label-schema.build-date': build_date,
      'org.label-schema.vcs-url': settings['repo_link'],
      'org.label-schema.vcs-ref': settings['commit']
    }
  )

  return image

def tag_image(image, settings, repos):
  for tag in settings['tags']:
    for repo in repos:
      image.tag(
        repository=repo['uri'],
        tag=tag
      )

def push_image(docker_client, settings, repos):
  for tag in settings['tags']:
    for repo in repos:
      docker_client.images.push(
        repository=repo['uri'],
        tag=tag
      )

def build_and_push_image():
  settings = get_settings(os.environ)

  sts_client = get_sts_client(settings)
  ecr_clients = get_ecr_clients(settings)
  docker_client = get_docker_client()

  print('Finding AWS account id...')
  
  aws_account_id = get_aws_account_id(sts_client)

  print('AWS account id is {0}.'.format(aws_account_id))
  
  print('Repo name is', settings['repo'])
  
  print('Regions:')
  for region in settings['regions']:
    print('- ', region)

  print('Fetching repos info from ECR across regions...')

  repos = get_repos(settings, ecr_clients, aws_account_id)

  print('Fetched repos info.')
  
  print('Repos:')
  for repo in repos:
    print('- ', repo['uri'])

  print('Logging in to registries...')
  login_to_registries(docker_client, repos)

  print('Logged in. Building image...')
  image = build_image(docker_client, settings)

  print('Build finished.')

  print('Tags:')
  for tag in settings['tags']:
    print('- ', tag)
  
  print('Tagging image...')
  tag_image(image, settings, repos)

  print('Tagged. Pushing image tags to registries...')
  push_image(docker_client, settings, repos)

  print('Pushed. All done.')

if __name__ == '__main__':
  build_and_push_image()
 
