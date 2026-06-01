#!/bin/bash
# phase1_baseline_sequential.sh
# Runs baseline sequentially - one user at a time
# Usage: ./phase1_baseline_sequential.sh <NUM_USERS>

set -euo pipefail

NUM_USERS="${1:-2}"
NAMESPACE="nextflow"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FULL_SAMPLESHEET="/workspace/samplesheet_extended.csv"
NXF_HOME="/workspace/.nextflow_shared_home"

mkdir -p /workspace/logs /workspace/metrics

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧬 PHASE 1 — Sequential Baseline"
echo "Users     : $NUM_USERS"
echo "Timestamp : $TIMESTAMP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "${TIMESTAMP}:${NUM_USERS}" > /workspace/last_run_timestamp.txt

kubectl delete pods -n "$NAMESPACE" \
  --field-selector=status.phase=Failed \
  --ignore-not-found=true 2>/dev/null || true

mkdir -p "$NXF_HOME"
cp -r /workspace/.nextflow_shared/plugins "$NXF_HOME/" 2>/dev/null || true
cp -r /workspace/.nextflow_shared/framework "$NXF_HOME/" 2>/dev/null || true
mkdir -p "$NXF_HOME/assets" && cp -r /workspace/.nextflow_shared/assets/.repos "$NXF_HOME/assets/" 2>/dev/null || true

FAILED=0
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_baseline_${TIMESTAMP}"
  RUN_DIR="/workspace/runs/${RUN_ID}"

  mkdir -p "${RUN_DIR}/results" "${RUN_DIR}/work"
  chmod -R 777 "${RUN_DIR}"

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
        [label: 'reuse', value: 'baseline'],
        [imagePullPolicy: 'IfNotPresent']
    ]
}
workDir = '${RUN_DIR}/work'
CONFIGEOF

  echo "🚀 Running user $i (sequential baseline)..."
  (cd "${RUN_DIR}" && export NXF_HOME="$NXF_HOME"; \
  NXF_OPTS="-Dnxf.disable.histlock=true -Dnextflow.k8s.poll.interval=30s" \
  nextflow run nf-core/rnaseq -r 3.26.0 \
    -profile test \
    --input "$FULL_SAMPLESHEET" \
    -c "/workspace/config_${RUN_ID}.config" \
    -c "/workspace/local_refs.config" \
    --outdir "${RUN_DIR}/results" \
    -w "${RUN_DIR}/work" \
    -with-trace    "${RUN_DIR}/results/trace.txt" \
    -with-report   "${RUN_DIR}/results/report.html" \
    -with-timeline "${RUN_DIR}/results/timeline.html" \
    > "/workspace/logs/${RUN_ID}.log" 2>&1)

  if [[ $? -eq 0 ]]; then
    echo "✅ User $i completed"
    grep 'Succeeded\|Duration\|CPU hours' "/workspace/logs/${RUN_ID}.log" | tail -3
  else
    echo "❌ User $i FAILED"
    tail -5 "/workspace/logs/${RUN_ID}.log"
    FAILED=$((FAILED + 1))
  fi

  rm -f "/workspace/config_${RUN_ID}.config"
done

echo ""
echo "📊 Copying metrics..."
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_baseline_${TIMESTAMP}"
  RUN_DIR="/workspace/runs/${RUN_ID}"
  LOCAL_METRICS="/workspace/metrics/${RUN_ID}"
  mkdir -p "$LOCAL_METRICS"
  cp "${RUN_DIR}/results/trace.txt" "${LOCAL_METRICS}/trace.txt" 2>/dev/null || true
  cp "${RUN_DIR}/results/report.html" "${LOCAL_METRICS}/report.html" 2>/dev/null || true
  echo "✅ Metrics saved: $LOCAL_METRICS"
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $FAILED -eq 0 ]]; then
  echo "🎉 Sequential baseline complete: ${NUM_USERS} users"
  echo "   Timestamp: ${TIMESTAMP}"
else
  echo "⚠️  $FAILED/${NUM_USERS} users failed"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit $FAILED