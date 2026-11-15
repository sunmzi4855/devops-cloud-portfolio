# Docker Hub — Publish Project 01

This repository contains a working Dockerfile and automated tests. The manual publish workflow builds a Linux/amd64 image and uploads it to your Docker Hub namespace.

**Status:** Workflow prepared; publishing requires your own Docker Hub account, a destination repository and a GitHub secret. No registry image is claimed as published until the workflow succeeds.

## 1. Create your Docker Hub repository

Visit https://hub.docker.com/ and sign up or sign in. Create a **public** repository named `cloud-devops-demo` in your own Docker namespace. Docker usernames may differ from GitHub usernames.

Suggested description: "Python health-check API demonstrating Docker containerization and GitHub Actions CI/CD."

## 2. Create a Docker Hub personal access token

In Docker Hub, open Account settings → Personal access tokens → Generate new token.

- Description: `github-devops-portfolio`
- Repository permission: **Read & Write** (not Delete), when offered
- Choose a reasonable expiration and rotate the token as needed
- Copy the token privately; **never paste it into a chat or commit it to GitHub**

## 3. Configure your GitHub repository

Go to https://github.com/sunmzi4855/devops-cloud-portfolio/settings/variables/actions and add a repository variable:

- Name: `DOCKERHUB_USERNAME`
- Value: your Docker Hub username (not your email)

Then go to https://github.com/sunmzi4855/devops-cloud-portfolio/settings/secrets/actions and add a repository secret:

- Name: `DOCKERHUB_TOKEN`
- Value: your Docker Hub access token

## 4. Publish

Go to https://github.com/sunmzi4855/devops-cloud-portfolio/actions/workflows/dockerhub-publish.yml, choose **Run workflow**, select `main`, and run it.

The workflow runs tests, signs in to Docker Hub, and builds and publishes `<your-docker-username>/cloud-devops-demo:latest` and a commit-tagged image.

## 5. Confirm

On Docker Hub, open your public `cloud-devops-demo` repository. Confirm that its **Tags** section shows `latest`.

To run the image:

```bash
docker pull YOUR_DOCKER_USERNAME/cloud-devops-demo:latest
docker run --rm -p 8080:8080 YOUR_DOCKER_USERNAME/cloud-devops-demo:latest
```

Visit http://localhost:8080/health to confirm it responds with healthy JSON.

## Security and release note

The publish workflow runs **manually**, avoiding automatic pushes during configuration. GitHub Actions permissions are read-only; registry credentials are supplied through the GitHub Actions secret store. This example intentionally does not deploy any paid cloud resources.
