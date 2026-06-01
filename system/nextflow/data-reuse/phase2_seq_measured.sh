#!/bin/bash
set -euo pipefail

NUM_USERS="${1:-2}"
REUSE_PCT="${2:-10}"
BASELINE_TIMESTAMP="${3:-}"
FULL_SAMPLESHEET="/workspace/samplesheet_extended.csv"
NXF_HOME="/workspace/.nextflow_shared_home"

if [[ -z "$BASELINE_TIMESTAMP" ]]; then
  echo "❌ ERROR: Must provide baseline timestamp"; exit 1
fi

TIMESTAMP="$BASELINE_TIMESTAMP"
REUSE_TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 SEQUENTIAL REUSE (${REUSE_PCT}%)"
echo "Users: $NUM_USERS | Baseline: $TIMESTAMP"
echo "   SMA IS MEASURING NOW"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

mkdir -p /workspace/logs /workspace/metrics "$NXF_HOME"
cp -r /workspace/.nextflow_shared/plugins "$NXF_HOME/" 2>/dev/null || true
cp -r /workspace/.nextflow_shared/framework "$NXF_HOME/" 2>/dev/null || true
mkdir -p "$NXF_HOME/assets" && cp -r /workspace/.nextflow_shared/assets/.repos "$NXF_HOME/assets/" 2>/dev/null || true

FAILED=0
for i in $(seq 1 "$NUM_USERS"); do
  BASELINE_WORK_DIR="/workspace/runs/user${i}_baseline_${TIMESTAMP}/work"
  REUSE_RUN_ID="user${i}_reuse${REUSE_PCT}pct_${REUSE_TIMESTAMP}"
  REUSE_RUN_DIR="/workspace/runs/${REUSE_RUN_ID}"

  if [[ ! -d "$BASELINE_WORK_DIR" ]]; then
    echo "❌ ERROR: Baseline work dir not found for user $i"; exit 1
  fi

  mkdir -p "${REUSE_RUN_DIR}/results"

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
workDir = '${BASELINE_WORK_DIR}'
CONFIGEOF

  if [[ "$i" -eq 1 ]]; then
    RESUME_FLAG=""
    echo "🚀 Running user $i (fresh - no cache)..."
  else
    SESSION_UUID=$(cat "/workspace/session_uuid_user${i}_${REUSE_PCT}pct.txt" 2>/dev/null || echo "")
    SEED_RUN_DIR=$(cat "/workspace/seed_run_dir_user${i}_${REUSE_PCT}pct.txt" 2>/dev/null || echo "")
    if [[ -z "$SESSION_UUID" ]] || [[ -z "$SEED_RUN_DIR" ]]; then
      echo "❌ ERROR: No session UUID or seed run dir for user $i"; exit 1
    fi
    cp -r "${SEED_RUN_DIR}/.nextflow" "${REUSE_RUN_DIR}/"
    RESUME_FLAG="-resume $SESSION_UUID"
    echo "🚀 Running user $i (reuse=${REUSE_PCT}%, session=${SESSION_UUID})..."
  fi

  (cd "${REUSE_RUN_DIR}" && export NXF_HOME="$NXF_HOME"; \
  NXF_OPTS="-Dnxf.disable.histlock=true -Dnextflow.k8s.poll.interval=30s" \
  nextflow run nf-core/rnaseq -r 3.26.0 \
    -profile test \
    --input "$FULL_SAMPLESHEET" \
    -c "/workspace/config_${REUSE_RUN_ID}.config" \
    -c "/workspace/local_refs.config" \
    --outdir "${REUSE_RUN_DIR}/results" \
    -w "${BASELINE_WORK_DIR}" \
    $RESUME_FLAG \
    -with-trace    "${REUSE_RUN_DIR}/results/trace.txt" \
    -with-report   "${REUSE_RUN_DIR}/results/report.html" \
    -with-timeline "${REUSE_RUN_DIR}/results/timeline.html" \
    > "/workspace/logs/${REUSE_RUN_ID}.log" 2>&1)

  if [[ $? -eq 0 ]]; then
    echo "✅ User $i completed"
    grep 'cached\|Succeeded\|Duration\|CPU hours' "/workspace/logs/${REUSE_RUN_ID}.log" | tail -4
    rm -f "/workspace/session_uuid_user${i}_${REUSE_PCT}pct.txt"
    rm -f "/workspace/seed_run_dir_user${i}_${REUSE_PCT}pct.txt"
  else
    echo "❌ User $i FAILED"
    tail -5 "/workspace/logs/${REUSE_RUN_ID}.log"
    FAILED=$((FAILED + 1))
  fi

  rm -f "/workspace/config_${REUSE_RUN_ID}.config"
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

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $FAILED -eq 0 ]]; then
  echo "🎉 Complete: ${NUM_USERS} users | ${REUSE_PCT}%"
else
  echo "⚠️  $FAILED/${NUM_USERS} users failed"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit $FAILED