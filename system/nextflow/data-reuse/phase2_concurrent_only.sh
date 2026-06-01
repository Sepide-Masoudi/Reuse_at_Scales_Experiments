#!/bin/bash
# phase2_concurrent_only.sh
# Runs concurrent reuse (cache already seeded)
# Each user gets isolated work directory copy + fresh NXF_HOME
#
# Usage: ./phase2_concurrent_only.sh <NUM_USERS> <REUSE_PCT> <BASELINE_TIMESTAMP>

set -euo pipefail

NUM_USERS="${1:-2}"
REUSE_PCT="${2:-10}"
BASELINE_TIMESTAMP="${3:-}"
FULL_SAMPLESHEET="/workspace/samplesheet_extended.csv"
PIDS=()

if [[ -z "$BASELINE_TIMESTAMP" ]]; then
  echo "❌ ERROR: Must provide baseline timestamp"; exit 1
fi

TIMESTAMP="$BASELINE_TIMESTAMP"
REUSE_TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 CONCURRENT REUSE (${REUSE_PCT}%)"
echo "Users: $NUM_USERS | Baseline: $TIMESTAMP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

mkdir -p /workspace/logs /workspace/metrics

echo "📋 Preparing isolated work directories..."
for i in $(seq 1 "$NUM_USERS"); do
  BASELINE_RUN_DIR="/workspace/runs/user${i}_baseline_${TIMESTAMP}"
  REUSE_RUN_ID="user${i}_reuse${REUSE_PCT}pct_${REUSE_TIMESTAMP}"
  REUSE_RUN_DIR="/workspace/runs/${REUSE_RUN_ID}"
  REUSE_WORK_DIR="${REUSE_RUN_DIR}/work"

  if [[ ! -d "${BASELINE_RUN_DIR}/work" ]]; then
    echo "❌ ERROR: Baseline work dir not found for user $i"; exit 1
  fi

  mkdir -p "${REUSE_RUN_DIR}"
  cp -r "${BASELINE_RUN_DIR}/work" "${REUSE_WORK_DIR}"
  chmod -R 777 "${REUSE_WORK_DIR}"
  rm -rf "${REUSE_WORK_DIR}/.nextflow" 2>/dev/null || true
  echo "✅ Work dir ready for user $i"
done

echo ""
echo "════════════════════════════════════════"
echo "🚀 Concurrent run (${NUM_USERS} users, ${REUSE_PCT}%)"
echo "   SMA MEASURING NOW"
echo "════════════════════════════════════════"

PIDS=()
for i in $(seq 1 "$NUM_USERS"); do
  REUSE_RUN_ID="user${i}_reuse${REUSE_PCT}pct_${REUSE_TIMESTAMP}"
  REUSE_RUN_DIR="/workspace/runs/${REUSE_RUN_ID}"
  REUSE_WORK_DIR="${REUSE_RUN_DIR}/work"
  NXF_HOME="/workspace/.nextflow_user${i}_${REUSE_TIMESTAMP}"

  mkdir -p "${REUSE_RUN_DIR}/results"
  mkdir -p "$NXF_HOME"
  cp -r /workspace/.nextflow_shared/plugins "$NXF_HOME/" 2>/dev/null || true
  cp -r /workspace/.nextflow_shared/framework "$NXF_HOME/" 2>/dev/null || true
  mkdir -p "$NXF_HOME/assets" && cp -r /workspace/.nextflow_shared/assets/.repos "$NXF_HOME/assets/" 2>/dev/null || true

  cat > "/workspace/config_${REUSE_RUN_ID}.config" << CONFIGEOF
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
        [label: 'run_id', value: '${REUSE_RUN_ID}'],
        [label: 'reuse', value: '${REUSE_PCT}pct'],
        [imagePullPolicy: 'IfNotPresent']
    ]
}
workDir = '${REUSE_WORK_DIR}'
CONFIGEOF

  echo "🚀 Starting user $i..."
  NXF_HOME_FIXED="$NXF_HOME"
  (export NXF_HOME="$NXF_HOME_FIXED"; NXF_OPTS="-Dnxf.disable.histlock=true -Dnextflow.k8s.poll.interval=30s" \
  nextflow run nf-core/rnaseq -r 3.26.0 \
    -profile test \
    --input "$FULL_SAMPLESHEET" \
    -c "/workspace/config_${REUSE_RUN_ID}.config" \
    -c "/workspace/local_refs.config" \
    --outdir "${REUSE_RUN_DIR}/results" \
    -w "${REUSE_WORK_DIR}" \
    -resume \
    -with-trace    "${REUSE_RUN_DIR}/results/trace.txt" \
    -with-report   "${REUSE_RUN_DIR}/results/report.html" \
    -with-timeline "${REUSE_RUN_DIR}/results/timeline.html" \
    > "/workspace/logs/${REUSE_RUN_ID}.log" 2>&1) &

  PIDS+=($!)
  echo "✅ User $i started (PID: ${PIDS[-1]})"
done

echo ""
echo "⏳ Waiting..."
FAILED=0
for i in "${!PIDS[@]}"; do
  PID="${PIDS[$i]}"
  USER_NUM=$((i + 1))
  REUSE_RUN_ID="user${USER_NUM}_reuse${REUSE_PCT}pct_${REUSE_TIMESTAMP}"
  if wait "$PID"; then
    echo "✅ User $USER_NUM completed"
  else
    echo "❌ User $USER_NUM FAILED"
    FAILED=$((FAILED + 1))
  fi
done

echo ""
echo "📊 Copying metrics..."
for i in $(seq 1 "$NUM_USERS"); do
  REUSE_RUN_ID="user${i}_reuse${REUSE_PCT}pct_${REUSE_TIMESTAMP}"
  REUSE_RUN_DIR="/workspace/runs/${REUSE_RUN_ID}"
  LOCAL_METRICS="/workspace/metrics/${REUSE_RUN_ID}"
  mkdir -p "$LOCAL_METRICS"
  cp "${REUSE_RUN_DIR}/results/trace.txt" "${LOCAL_METRICS}/trace.txt" 2>/dev/null || true
  cp "${REUSE_RUN_DIR}/results/report.html" "${LOCAL_METRICS}/report.html" 2>/dev/null || true
  echo "✅ Metrics saved: $LOCAL_METRICS"
done

echo "🧹 Cleaning..."
for i in $(seq 1 "$NUM_USERS"); do
  REUSE_RUN_ID="user${i}_reuse${REUSE_PCT}pct_${REUSE_TIMESTAMP}"
  rm -f "/workspace/config_${REUSE_RUN_ID}.config" 2>/dev/null || true
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $FAILED -eq 0 ]]; then
  echo "🎉 Complete: ${NUM_USERS} users | ${REUSE_PCT}%"
else
  echo "⚠️  $FAILED failed"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit $FAILED