#!/bin/bash
# run_nextflow_podservice.sh
# Runs N=2 concurrent users using persistent featureCounts and StringTie service pods
# Service pods are started LATE (after genome preparation) to minimize idle energy
# and stopped IMMEDIATELY after pipeline finishes

set -euo pipefail

NUM_USERS="${1:-2}"
NAMESPACE="nextflow"
LAUNCHER_POD="nextflow-launcher"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PIPELINE_DIR="/workspace/rnaseq-reuse-full"
SERVICE_STARTUP_DELAY=1200  # 20 minutes - time until featureCounts/StringTie tasks start
PIDS=()

mkdir -p ./logs ./metrics

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧬 Nextflow Pod-Service Reuse Runner"
echo "Users         : $NUM_USERS"
echo "Pipeline      : $PIPELINE_DIR"
echo "Service delay : ${SERVICE_STARTUP_DELAY}s"
echo "Timestamp     : $TIMESTAMP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

POD_STATUS=$(kubectl get pod "$LAUNCHER_POD" -n "$NAMESPACE" \
  -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
if [[ "$POD_STATUS" != "Running" ]]; then
  echo "❌ ERROR: Launcher pod is not running"; exit 1
fi
echo "✅ Launcher pod is running"

# ─────────────────────────────────────────
# Make sure service pods are NOT running at start
# to avoid counting idle energy before pipeline
# ─────────────────────────────────────────
echo "🛑 Ensuring service pods are stopped before pipeline starts..."
kubectl delete pod featurecounts-service stringtie-service \
  -n "$NAMESPACE" --ignore-not-found=true 2>/dev/null || true
echo "✅ Service pods stopped"

echo "🧹 Cleaning up old failed pods..."
kubectl delete pods -n "$NAMESPACE" \
  --field-selector=status.phase=Failed \
  --ignore-not-found=true 2>/dev/null || true
echo "✅ Cleanup done"

# ─────────────────────────────────────────
# Launch pipeline users FIRST (no service pods yet)
# ─────────────────────────────────────────
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_podservice_${TIMESTAMP}"
  RUN_DIR="/workspace/runs/${RUN_ID}"
  USER_CONFIG="/workspace/config_${RUN_ID}.config"

  echo ""
  echo "📁 Creating directories for user $i..."
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    sh -c "mkdir -p ${RUN_DIR}/work ${RUN_DIR}/results && chmod -R 777 ${RUN_DIR}"

  echo "⚙️  Creating config for user $i..."
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- sh -c "cat > ${USER_CONFIG} << 'CONFIGEOF'
process {
    executor = 'k8s'
    memory   = '2 GB'
    cpus     = 1
}

executor {
    queueSize = 2
}

k8s {
    namespace        = 'nextflow'
    serviceAccount   = 'nextflow-sa'
    storageClaimName = 'nextflow-pvc'
    storageMountPath = '/workspace'
    computeResourceType = 'Job'
    pod = [
        [nodeSelector: 'kubernetes.io/hostname=gisele'],
        [annotation: 'prometheus.io/scrape', value: 'true'],
        [annotation: 'prometheus.io/port',   value: '9090'],
        [label: 'pipeline', value: 'rnaseq'],
        [label: 'user', value: 'user${i}'],
        [label: 'run_id', value: '${RUN_ID}'],
        [label: 'reuse', value: 'pod-service'],
        [imagePullPolicy: 'Always']
    ]
}

workDir = '${RUN_DIR}/work'
CONFIGEOF"

  echo "🚀 Launching user $i → $RUN_DIR"
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    sh -c "cd /workspace && nextflow run ${PIPELINE_DIR}/main.nf \
      -profile test --input /workspace/samplesheet_extended.csv \
      -c '${USER_CONFIG}' \
      --outdir '${RUN_DIR}/results' \
      -w '${RUN_DIR}/work' \
      -with-trace    '${RUN_DIR}/results/trace.txt' \
      -with-report   '${RUN_DIR}/results/report.html' \
      -with-timeline '${RUN_DIR}/results/timeline.html'" \
      > "./logs/${RUN_ID}.log" 2>&1 &

  PIDS+=($!)
  echo "✅ User $i started (PID: ${PIDS[-1]})"
done

# ─────────────────────────────────────────
# Start service pods AFTER delay
# (genome prep takes ~20 min, services not needed until then)
# ─────────────────────────────────────────
echo ""
echo "⏱  Waiting ${SERVICE_STARTUP_DELAY}s before starting service pods..."
echo "   (Pipeline is running genome preparation steps)"
sleep "$SERVICE_STARTUP_DELAY"

echo "🚀 Starting service pods now (featureCounts/StringTie tasks about to begin)..."
kubectl apply -f ~/experiments/pipeline/nextflow/reusable-services/featurecounts-service.yaml
kubectl apply -f ~/experiments/pipeline/nextflow/reusable-services/stringtie-service.yaml

# Wait for service pods to be ready
echo "⏳ Waiting for service pods to be ready..."
kubectl wait --for=condition=Ready pod/featurecounts-service pod/stringtie-service \
  -n "$NAMESPACE" --timeout=120s
echo "✅ Service pods ready"

# Health check
FC_HEALTH=$(kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  sh -c "curl -sf http://featurecounts-service.nextflow.svc.cluster.local:8080/health" 2>/dev/null || echo "FAILED")
ST_HEALTH=$(kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  sh -c "curl -sf http://stringtie-service.nextflow.svc.cluster.local:8081/health" 2>/dev/null || echo "FAILED")

if [[ "$FC_HEALTH" == *"ok"* ]]; then echo "✅ featurecounts-service healthy"
else echo "⚠️  featurecounts-service health check failed: $FC_HEALTH"; fi
if [[ "$ST_HEALTH" == *"ok"* ]]; then echo "✅ stringtie-service healthy"
else echo "⚠️  stringtie-service health check failed: $ST_HEALTH"; fi

# ─────────────────────────────────────────
# Wait for all users to finish
# ─────────────────────────────────────────
echo ""
echo "⏳ Waiting for all $NUM_USERS users to complete..."
FAILED=0

for i in "${!PIDS[@]}"; do
  PID="${PIDS[$i]}"
  USER_NUM=$((i + 1))
  if wait "$PID"; then
    echo "✅ User $USER_NUM finished successfully"
  else
    echo "❌ User $USER_NUM FAILED (check ./logs/user${USER_NUM}_podservice_${TIMESTAMP}.log)"
    FAILED=$((FAILED + 1))
  fi
done

# ─────────────────────────────────────────
# Stop service pods IMMEDIATELY after pipeline finishes
# ─────────────────────────────────────────
echo ""
echo "🛑 Stopping service pods immediately to avoid idle energy accumulation..."
kubectl delete pod featurecounts-service stringtie-service \
  -n "$NAMESPACE" --ignore-not-found=true 2>/dev/null || true
echo "✅ Service pods stopped"

# ─────────────────────────────────────────
# Copy metrics locally
# ─────────────────────────────────────────
echo ""
echo "📊 Copying metrics..."
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_podservice_${TIMESTAMP}"
  RUN_DIR="/workspace/runs/${RUN_ID}"
  LOCAL_METRICS="./metrics/${RUN_ID}"
  mkdir -p "$LOCAL_METRICS"
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    cat "${RUN_DIR}/results/trace.txt" > "${LOCAL_METRICS}/trace.txt" 2>/dev/null || true
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    cat "${RUN_DIR}/results/report.html" > "${LOCAL_METRICS}/report.html" 2>/dev/null || true
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    cat "${RUN_DIR}/results/timeline.html" > "${LOCAL_METRICS}/timeline.html" 2>/dev/null || true
  echo "✅ Metrics saved to: $LOCAL_METRICS"
done

# ─────────────────────────────────────────
# Cleanup configs
# ─────────────────────────────────────────
echo ""
echo "🧹 Cleaning up configs..."
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_podservice_${TIMESTAMP}"
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    rm -f "/workspace/config_${RUN_ID}.config" 2>/dev/null || true
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $FAILED -eq 0 ]]; then
  echo "🎉 All $NUM_USERS users completed with pod-service reuse"
  echo "   Service pods ran only during featureCounts/StringTie steps"
else
  echo "⚠️  $FAILED/$NUM_USERS users failed"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit $FAILED