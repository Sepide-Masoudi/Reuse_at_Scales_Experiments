#!/bin/bash
# run_nextflow_shared_index.sh
# Runs N=2 concurrent users sharing pre-built STAR and BBSplit indexes
# Both users skip STAR_GENOMEGENERATE and BBMAP_BBSPLIT pod spawning
# Run prebuild_shared_indexes.sh first!

set -euo pipefail

NUM_USERS="${1:-2}"
NAMESPACE="nextflow"
LAUNCHER_POD="nextflow-launcher"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SHARED_DIR="/workspace/shared"
PIDS=()

mkdir -p ./logs ./metrics

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧬 Nextflow Shared Index Reuse Runner"
echo "Users      : $NUM_USERS"
echo "Shared dir : $SHARED_DIR"
echo "Timestamp  : $TIMESTAMP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ─────────────────────────────────────────
# Check launcher pod
# ─────────────────────────────────────────
POD_STATUS=$(kubectl get pod "$LAUNCHER_POD" -n "$NAMESPACE" \
  -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")

if [[ "$POD_STATUS" != "Running" ]]; then
  echo "❌ ERROR: Launcher pod is not running"
  exit 1
fi
echo "✅ Launcher pod is running"

# ─────────────────────────────────────────
# Verify shared indexes exist
# ─────────────────────────────────────────
STAR_EXISTS=$(kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  sh -c "[ -d ${SHARED_DIR}/star_index ] && echo yes || echo no")
BBSPLIT_EXISTS=$(kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  sh -c "[ -d ${SHARED_DIR}/bbsplit_index ] && echo yes || echo no")

if [[ "$STAR_EXISTS" != "yes" || "$BBSPLIT_EXISTS" != "yes" ]]; then
  echo "❌ ERROR: Shared indexes not found at $SHARED_DIR"
  echo "Run ./prebuild_shared_indexes.sh first!"
  exit 1
fi
echo "✅ Shared indexes found"
echo "   star_index   : ${SHARED_DIR}/star_index"
echo "   bbsplit_index: ${SHARED_DIR}/bbsplit_index"

# ─────────────────────────────────────────
# Clean up old failed pods
# ─────────────────────────────────────────
echo "🧹 Cleaning up old failed pods..."
kubectl delete pods -n "$NAMESPACE" \
  --field-selector=status.phase=Failed \
  --ignore-not-found=true 2>/dev/null || true
echo "✅ Cleanup done"

# ─────────────────────────────────────────
# Launch N users concurrently
# each using shared star_index and bbsplit_index
# ─────────────────────────────────────────
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_reuse_${TIMESTAMP}"
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
        [label: 'reuse', value: 'shared_index'],
        [imagePullPolicy: 'Always']
    ]
}

workDir = '${RUN_DIR}/work'
CONFIGEOF"

  echo "🚀 Launching user $i → $RUN_DIR"

  # Launch pipeline in background
  # Pass pre-built star_index and bbsplit_index
  # This skips STAR_GENOMEGENERATE and BBMAP_BBSPLIT pods entirely
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    nextflow run /workspace/.nextflow/assets/nf-core/rnaseq/main.nf \
      -profile test \
      -c "${USER_CONFIG}" \
      --outdir "${RUN_DIR}/results" \
      --star_index "${SHARED_DIR}/star_index" \
      --bbsplit_index "${SHARED_DIR}/bbsplit_index" \
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
    echo "❌ User $USER_NUM FAILED (check ./logs/user${USER_NUM}_reuse_${TIMESTAMP}.log)"
    FAILED=$((FAILED + 1))
  fi
done

# ─────────────────────────────────────────
# Copy metrics locally
# ─────────────────────────────────────────
echo ""
echo "📊 Copying metrics..."
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_reuse_${TIMESTAMP}"
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
# Cleanup per-user configs
# ─────────────────────────────────────────
echo ""
echo "🧹 Cleaning up configs..."
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_reuse_${TIMESTAMP}"
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    rm -f "/workspace/config_${RUN_ID}.config" 2>/dev/null || true
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $FAILED -eq 0 ]]; then
  echo "🎉 All $NUM_USERS users completed with shared index reuse"
  echo ""
  echo "Pods saved per user:"
  echo "  STAR_GENOMEGENERATE : ~1 pod × $NUM_USERS users = $NUM_USERS pods saved"
  echo "  BBMAP_BBSPLIT       : ~1 pod × $NUM_USERS users = $NUM_USERS pods saved"
else
  echo "⚠️  $FAILED/$NUM_USERS users failed"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit $FAILED