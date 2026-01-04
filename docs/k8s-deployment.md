# Deploying PandoraLM on Kubernetes

This guide describes how to deploy the PandoraLM Enterprise Stack on a Kubernetes cluster.

## Architecture

The stack is deployed via the `pandora-os` Helm chart and includes:

- **Core**: Node.js API Gateway & UI
- **Cortex**: Python Reasoning Engine & GraphRAG
- **Databases**: Postgres, Neo4j, Redis (StatefulSets)
- **Object Storage**: MinIO (S3-compatible) for Vector storage
- **Workers**: Celery workers with KEDA autoscaling

## Prerequisites

- Docker
- Kind (Kubernetes in Docker)
- Helm
- Kubectl

## Local Deployment (Quick Start)

We provide a bootstrap script that sets up a local Kind cluster with NGINX Ingress and KEDA.

1. Run the bootstrap script:

   ```bash
   ./infra/k8s/bootstrap.sh
   ```

2. Add local DNS entries:
   Add the following line to your `/etc/hosts` file (macOS/Linux) or hosts file (Windows):

   ```
   127.0.0.1 pandora.local api.pandora.local vector-admin.pandora.local traefik.pandora.local
   ```

3. Verify Deployment:

   ```bash
   kubectl get pods -n pandora
   ```

   Wait for all pods to be `Running` (or Ready).

4. Access the UI:
   Open [http://pandora.local](http://pandora.local).

## Production Deployment

1. **Secrets**: DO NOT leave the default passwords in `secrets.yaml`. Use ExternalSecrets or seal your secrets.
2. **Persistence**: In `values.yaml`, configure `storageClass` for your cloud provider (e.g., `gp2` for AWS, `standard` for GKE).
3. **Ingress**: Configure `ingress.className` and cert-manager annotations for real SSL certificates.

## Autoscaling

KEDA is configured to scale the `pandora-celery-worker` deployment based on the length of the Redis list `celery`.

- Min Replicas: 1
- Max Replicas: 10
- Threshold: 10 pending items

To verify:

```bash
kubectl get scaledobject -n pandora
```
