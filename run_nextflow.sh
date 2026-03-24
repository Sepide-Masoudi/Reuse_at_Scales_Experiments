#!/bin/bash
# run_nextflow_concurrent.sh
# Runs N=2 concurrent independent pipeline instances with per-user pod labels
# For Baseline experimetn (No reuse)

set -euo pipefail

NUM_USERS="${1:-2}"
NAMESPACE="nextflow"
LAUNCHER_POD="nextflow-launcher"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PIDS=()

mkdir -p ./logs ./metrics

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧬 Nextflow Concurrent Runner"
echo "Users     : $NUM_USERS"
echo "Timestamp : $TIMESTAMP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ─────────────────────────────────────────
# Check launcher pod
# ─────────────────────────────────────────
POD_STATUS=$(kubectl get pod "$LAUNCHER_POD" -n "$NAMESPACE" \
  -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")

if [[ "$POD_STATUS" != "Running" ]]; then
  echo "❌ ERROR: Launcher pod is not running"
  echo "Recreate it with: kubectl apply -f nextflow-launcher.yaml"
  exit 1
fi
echo "✅ Launcher pod is running"

# ─────────────────────────────────────────
# Clean up old failed pods
# ─────────────────────────────────────────
echo "🧹 Cleaning up old failed pods..."
kubectl delete pods -n "$NAMESPACE" \
  --field-selector=status.phase=Failed \
  --ignore-not-found=true 2>/dev/null || true
echo "✅ Cleanup done"

# ─────────────────────────────────────────
# Create per-user configs and launch
# ─────────────────────────────────────────
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_${TIMESTAMP}"
  RUN_DIR="/workspace/runs/${RUN_ID}"
  USER_CONFIG="/workspace/config_user${i}_${TIMESTAMP}.config"

  echo "📁 Creating directories for user $i..."
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    sh -c "mkdir -p ${RUN_DIR}/work ${RUN_DIR}/results && chmod -R 777 ${RUN_DIR}"

  echo "⚙️  Creating config for user $i..."
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- sh -c "cat > ${USER_CONFIG} << 'CONFIGEOF'
process {
    executor = 'k8s'
    memory   = '4 GB'
    cpus     = 2
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
        [imagePullPolicy: 'Always']
    ]
}

workDir = '${RUN_DIR}/work'
CONFIGEOF"

  echo "🚀 Launching user $i → $RUN_DIR"

  # Launch pipeline in background
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    nextflow run nf-core/rnaseq \
      -revision 3.23.0 \
      -profile test \
      -c "${USER_CONFIG}" \
      --outdir "${RUN_DIR}/results" \
      -w "${RUN_DIR}/work" \
      -with-trace    "${RUN_DIR}/results/trace.txt" \
      -with-report   "${RUN_DIR}/results/report.html" \
      -with-timeline "${RUN_DIR}/results/timeline.html" \
      > "./logs/${RUN_ID}.log" 2>&1 &

  PIDS+=($!)
  echo "✅ User $i started (PID: ${PIDS[-1]})"
done

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
    echo "❌ User $USER_NUM FAILED (check ./logs/user${USER_NUM}_${TIMESTAMP}.log)"
    FAILED=$((FAILED + 1))
  fi
done

# ─────────────────────────────────────────
# Copy metrics locally
# ─────────────────────────────────────────
echo ""
echo "📊 Copying metrics..."
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_${TIMESTAMP}"
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
# Cleanup per-user configs from PVC
# ─────────────────────────────────────────
echo ""
echo "🧹 Cleaning up per-user configs..."
for i in $(seq 1 "$NUM_USERS"); do
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    rm -f "/workspace/config_user${i}_${TIMESTAMP}.config" 2>/dev/null || true
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $FAILED -eq 0 ]]; then
  echo "🎉 All $NUM_USERS users completed successfully"
else
  echo "⚠️  $FAILED/$NUM_USERS users failed"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit $FAILED