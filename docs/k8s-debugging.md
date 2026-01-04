# Debugging PandoraLM on Kubernetes (Observability Guide)

This guide explains how to use the "Glass Box" features (Prometheus, Grafana, Tempo) to debug issues.

## Accessing the Dashboards

Since we are using `Kind` or a private cluster, services are not exposed publicly by default. Use port-forwarding:

### 1. Grafana (Metrics & Dashboards)

```bash
# Forward port 3000 to local
kubectl port-forward svc/pandora-grafana 3000:80 -n pandora
```

- Open [http://localhost:3000](http://localhost:3000)
- Login: `admin` / `prom-operator` (default)
- Navigate to **Dashboards > PandoraLM Overview**

### 2. Tempo (Distributed Tracing)

Usually accessed via Grafana ("Explore" tab), but can be queried directly via API.

- In Grafana Explore: Select "Tempo" datasource.
- Enter a Trace ID to visualize the request flow.

## Common Debugging Scenarios

### "The AI is slow"

1. Check **RAG Latency** panel in Grafana.
2. If high, copy a Trace ID from the logs (if logged) or find a slow request in "Search" (Tempo).
3. Inspect the waterfall view:
   - Is `vector_search` taking time? -> Check MinIO/LanceDB.
   - Is `generation` taking time? -> LLM Provider is slow.

### "Ingestion Stuck"

1. Check **Celery Queue Depth** panel.
2. If > 0 and flat: Workers might be dead or stuck.
3. Check Worker logs:

   ```bash
   kubectl logs -l app.kubernetes.io/name=pandora-os-worker -n pandora
   ```

## Prometheus Alerts (Default)

The stack comes with default alerts. Check "Alerting" in Grafana for:

- `KubePodCrashLooping`
- `HighCPUUsage`
- `TargetDown` (critical for Cortex/Core)
