#!/bin/bash
# phase3_pod_service_concurrent.sh
# Concurrent pipeline runs using persistent featureCounts and StringTie service pods
# Usage: ./phase3_pod_service_concurrent.sh <NUM_USERS>

set -euo pipefail

NUM_USERS="${1:-2}"
NAMESPACE="nextflow"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FULL_SAMPLESHEET="/workspace/samplesheet_extended.csv"
PIPELINE_DIR="/workspace/rnaseq-podservice"
NXF_HOME="/workspace/.nextflow_shared_home"
PIDS=()

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧬 PHASE 3 — Pod Service Reuse (Concurrent)"
echo "Users     : $NUM_USERS"
echo "Timestamp : $TIMESTAMP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

mkdir -p /workspace/logs /workspace/metrics

FC_STATUS=$(kubectl get pod featurecounts-service -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
ST_STATUS=$(kubectl get pod stringtie-service -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")

if [[ "$FC_STATUS" != "Running" ]]; then
  echo "❌ ERROR: featurecounts-service not running"; exit 1
fi
if [[ "$ST_STATUS" != "Running" ]]; then
  echo "❌ ERROR: stringtie-service not running"; exit 1
fi
echo "✅ featurecounts-service: Running"
echo "✅ stringtie-service: Running"

kubectl delete pods -n "$NAMESPACE" \
  --field-selector=status.phase=Failed \
  --ignore-not-found=true 2>/dev/null || true

mkdir -p "$NXF_HOME"
cp -r /workspace/.nextflow_shared/plugins "$NXF_HOME/" 2>/dev/null || true
cp -r /workspace/.nextflow_shared/framework "$NXF_HOME/" 2>/dev/null || true
mkdir -p "$NXF_HOME/assets" && cp -r /workspace/.nextflow_shared/assets/.repos "$NXF_HOME/assets/" 2>/dev/null || true

echo ""
echo "════════════════════════════════════════"
echo "🚀 Starting $NUM_USERS users concurrently"
echo "   SMA IS MEASURING NOW"
echo "════════════════════════════════════════"

PIDS=()
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_podservice_concurrent_${TIMESTAMP}"
  RUN_DIR="/workspace/runs/${RUN_ID}"
  USER_NXF_HOME="/workspace/.nextflow_user${i}_${TIMESTAMP}"

  mkdir -p "${RUN_DIR}/results" "${RUN_DIR}/work"
  chmod -R 777 "${RUN_DIR}"
  mkdir -p "$USER_NXF_HOME"
  cp -r /workspace/.nextflow_shared/plugins "$USER_NXF_HOME/" 2>/dev/null || true
  cp -r /workspace/.nextflow_shared/framework "$USER_NXF_HOME/" 2>/dev/null || true
  mkdir -p "$USER_NXF_HOME/assets" && cp -r /workspace/.nextflow_shared/assets/.repos "$USER_NXF_HOME/assets/" 2>/dev/null || true

  cat > "/workspace/config_${RUN_ID}.config" << CONFIGEOF
process {
    executor = 'k8s'
    memory   = '4.GB'
    cpus     = 2
}
executor {
    queueSize = 4
}
k8s {
    namespace        = 'nextflow'
    serviceAccount   = 'nextflow-sa'
    storageClaimName = 'nextflow-pvc'
    storageMountPath = '/workspace'
    computeResourceType = 'Job'
    pod = [
        [nodeSelector: 'role=sut'],
        [label: 'pipeline', value: 'rnaseq'],
        [label: 'user', value: 'user${i}'],
        [label: 'run_id', value: '${RUN_ID}'],
        [label: 'reuse', value: 'pod-service-concurrent'],
        [imagePullPolicy: 'IfNotPresent']
    ]
}
workDir = '${RUN_DIR}/work'
CONFIGEOF

  echo "🚀 Starting user $i..."
  USER_NXF_HOME_FIXED="$USER_NXF_HOME"
  (cd "${RUN_DIR}" && export NXF_HOME="$USER_NXF_HOME_FIXED"; \
  NXF_OPTS="-Dnxf.disable.histlock=true -Dnextflow.k8s.poll.interval=30s" \
  nextflow run "$PIPELINE_DIR" \
    -profile test \
    --input "$FULL_SAMPLESHEET" \
    -c "/workspace/config_${RUN_ID}.config" \
    -c "/workspace/local_refs.config" \
    --outdir "${RUN_DIR}/results" \
    -w "${RUN_DIR}/work" \
    -with-trace    "${RUN_DIR}/results/trace.txt" \
    -with-report   "${RUN_DIR}/results/report.html" \
    -with-timeline "${RUN_DIR}/results/timeline.html" \
    > "/workspace/logs/${RUN_ID}.log" 2>&1) &

  PIDS+=($!)
  echo "✅ User $i started (PID: ${PIDS[-1]})"
  sleep 30
done

echo ""
echo "⏳ Waiting for all users to complete..."
FAILED=0
for i in "${!PIDS[@]}"; do
  PID="${PIDS[$i]}"
  USER_NUM=$((i + 1))
  RUN_ID="user${USER_NUM}_podservice_concurrent_${TIMESTAMP}"
  if wait "$PID"; then
    echo "✅ User $USER_NUM completed"
    grep 'Succeeded\|Duration\|CPU hours' "/workspace/logs/${RUN_ID}.log" | tail -3
  else
    echo "❌ User $USER_NUM FAILED"
    tail -5 "/workspace/logs/${RUN_ID}.log"
    FAILED=$((FAILED + 1))
  fi
done

echo ""
echo "📊 Copying metrics..."
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_podservice_concurrent_${TIMESTAMP}"
  RUN_DIR="/workspace/runs/${RUN_ID}"
  LOCAL_METRICS="/workspace/metrics/${RUN_ID}"
  mkdir -p "$LOCAL_METRICS"
  cp "${RUN_DIR}/results/trace.txt" "${LOCAL_METRICS}/trace.txt" 2>/dev/null || true
  cp "${RUN_DIR}/results/report.html" "${LOCAL_METRICS}/report.html" 2>/dev/null || true
  echo "✅ Metrics saved: $LOCAL_METRICS"
done

echo "🧹 Cleaning..."
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_podservice_concurrent_${TIMESTAMP}"
  rm -f "/workspace/config_${RUN_ID}.config" 2>/dev/null || true
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $FAILED -eq 0 ]]; then
  echo "🎉 Concurrent pod service complete: ${NUM_USERS} users | ${TIMESTAMP}"
else
  echo "⚠️  $FAILED/${NUM_USERS} users failed"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit $FAILED