#!/bin/bash
# run_nextflow_shared_index.sh
# S2: 2 concurrent users with shared STAR + BBSplit index reuse
# IDENTICAL config to all other experiments for fair comparison

set -euo pipefail

NUM_USERS="${1:-2}"
NAMESPACE="nextflow"
LAUNCHER_POD="nextflow-launcher"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SHARED_STAR_INDEX="/workspace/shared/star_index"
SHARED_BBSPLIT_INDEX="/workspace/shared/bbsplit_index"
PIDS=()

mkdir -p ./logs ./metrics

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧬 Nextflow Shared Index Runner (S2: Index Reuse)"
echo "Users     : $NUM_USERS"
echo "Timestamp : $TIMESTAMP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

POD_STATUS=$(kubectl get pod "$LAUNCHER_POD" -n "$NAMESPACE" \
  -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
if [[ "$POD_STATUS" != "Running" ]]; then
  echo "❌ ERROR: Launcher pod is not running"; exit 1
fi
echo "✅ Launcher pod is running"

# Verify shared indexes exist
#STAR_EXISTS=$(kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
#  sh -c "[ -d ${SHARED_STAR_INDEX} ] && echo YES || echo NO")
BBSPLIT_EXISTS=$(kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  sh -c "[ -d ${SHARED_BBSPLIT_INDEX} ] && echo YES || echo NO")

#if [[ "$STAR_EXISTS" != "YES" ]] || [[ "$BBSPLIT_EXISTS" != "YES" ]]; then
if [[ "$BBSPLIT_EXISTS" != "YES" ]]; then
  echo "❌ ERROR: Shared indexes not found. Run prebuild_shared_indexes.sh first."
  echo "  STAR index:   N/A (not used)"
  echo "  BBSplit index: $BBSPLIT_EXISTS"
  exit 1
fi
echo "✅ Shared indexes found"

echo "🧹 Cleaning up old failed pods..."
kubectl delete pods -n "$NAMESPACE" \
  --field-selector=status.phase=Failed \
  --ignore-not-found=true 2>/dev/null || true
echo "✅ Cleanup done"

for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_reuse_${TIMESTAMP}"
  RUN_DIR="/workspace/runs/${RUN_ID}"
  USER_CONFIG="/workspace/config_${RUN_ID}.config"

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
        [nodeSelector: 'baremetal=true'],
        [annotation: 'prometheus.io/scrape', value: 'true'],
        [annotation: 'prometheus.io/port',   value: '9090'],
        [label: 'pipeline', value: 'rnaseq'],
        [label: 'user', value: 'user${i}'],
        [label: 'run_id', value: '${RUN_ID}'],
        [label: 'reuse', value: 'index'],
        [imagePullPolicy: 'Always']
    ]
}

workDir = '${RUN_DIR}/work'
CONFIGEOF"

  echo "🚀 Launching user $i → $RUN_DIR"
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    sh -c "cd /workspace && NXF_HOME=${RUN_DIR}/.nextflow nextflow run /workspace/.nextflow/assets/nf-core/rnaseq/main.nf \
      -profile test --input /workspace/samplesheet_extended.csv \
      -c '${USER_CONFIG}' \
      --outdir '${RUN_DIR}/results' \
      -w '${RUN_DIR}/work' \
      --bbsplit_index '${SHARED_BBSPLIT_INDEX}' \
      -with-trace    '${RUN_DIR}/results/trace.txt' \
      -with-report   '${RUN_DIR}/results/report.html' \
      -with-timeline '${RUN_DIR}/results/timeline.html'" \
      > "./logs/${RUN_ID}.log" 2>&1 &

  PIDS+=($!)
  echo "✅ User $i started (PID: ${PIDS[-1]})"
done

echo ""
echo "⏳ Waiting for all $NUM_USERS users to complete..."
FAILED=0
for i in "${!PIDS[@]}"; do
  PID="${PIDS[$i]}"
  USER_NUM=$((i + 1))
  if wait "$PID"; then
    echo "✅ User $USER_NUM finished successfully"
  else
    echo "❌ User $USER_NUM FAILED"
    FAILED=$((FAILED + 1))
  fi
done

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

echo ""
echo "🧹 Cleaning up configs..."
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_reuse_${TIMESTAMP}"
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    rm -f "/workspace/config_${RUN_ID}.config" 2>/dev/null || true
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $FAILED -eq 0 ]]; then
  echo "🎉 All $NUM_USERS users completed (S2: Index Reuse)"
else
  echo "⚠️  $FAILED/$NUM_USERS users failed"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit $FAILED