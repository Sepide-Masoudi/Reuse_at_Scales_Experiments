#!/bin/bash
# phase3_pod_service_single.sh
# Runs the pod-service pipeline for EXACTLY ONE user (given index).
# Called once per user by main_pod_service_peruser.py so each user gets
# its own SMA measurement window/fetch.
#
# Usage: ./phase3_pod_service_single.sh <USER_INDEX> <TOTAL_USERS> <TIMESTAMP>
#   USER_INDEX  : which user this invocation runs (1..TOTAL_USERS)
#   TOTAL_USERS : total users in the experiment (for labels only)
#   TIMESTAMP   : shared timestamp for the whole experiment (so all users
#                 of one experiment share a run grouping)

set -euo pipefail

USER_INDEX="${1:?need user index}"
TOTAL_USERS="${2:?need total users}"
TIMESTAMP="${3:?need timestamp}"

NAMESPACE="nextflow"
FULL_SAMPLESHEET="/workspace/samplesheet_extended.csv"
PIPELINE_DIR="/workspace/rnaseq-podservice"
NXF_HOME="/workspace/.nextflow_shared_home"

mkdir -p /workspace/logs /workspace/metrics

# ── Verify services are up (every invocation, cheap and safe) ──────────
FC_STATUS=$(kubectl get pod featurecounts-service -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
ST_STATUS=$(kubectl get pod stringtie-service -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
if [[ "$FC_STATUS" != "Running" ]]; then
  echo "❌ ERROR: featurecounts-service not running (status: $FC_STATUS)"; exit 1
fi
if [[ "$ST_STATUS" != "Running" ]]; then
  echo "❌ ERROR: stringtie-service not running (status: $ST_STATUS)"; exit 1
fi

# ── Ensure shared NXF_HOME exists (only meaningfully copies on user 1) ──
mkdir -p "$NXF_HOME"
cp -r /workspace/.nextflow_shared/plugins   "$NXF_HOME/" 2>/dev/null || true
cp -r /workspace/.nextflow_shared/framework "$NXF_HOME/" 2>/dev/null || true
mkdir -p "$NXF_HOME/assets" && cp -r /workspace/.nextflow_shared/assets/.repos "$NXF_HOME/assets/" 2>/dev/null || true

i="$USER_INDEX"
RUN_ID="user${i}_podservice_${TIMESTAMP}"
RUN_DIR="/workspace/runs/${RUN_ID}"
LOCAL_METRICS="/workspace/metrics/${RUN_ID}"

echo "🚀 Running user $i / $TOTAL_USERS (pod service reuse) — run_id=$RUN_ID"

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
        [label: 'reuse', value: 'pod-service'],
        [imagePullPolicy: 'IfNotPresent']
    ]
}
workDir = '${RUN_DIR}/work'
CONFIGEOF

# ── Run pipeline (guard errexit so we can capture exit code) ───────────
set +e
(cd "${RUN_DIR}" && export NXF_HOME="$NXF_HOME"; \
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
  > "/workspace/logs/${RUN_ID}.log" 2>&1)
RUN_EXIT=$?
set -e

if [[ $RUN_EXIT -eq 0 ]]; then
  echo "✅ User $i completed"
  grep 'Succeeded\|Duration\|CPU hours' "/workspace/logs/${RUN_ID}.log" | tail -3
else
  echo "❌ User $i FAILED (exit $RUN_EXIT)"
  tail -5 "/workspace/logs/${RUN_ID}.log"
fi

# ── Save metrics BEFORE any cleanup ────────────────────────────────────
mkdir -p "$LOCAL_METRICS"
cp "${RUN_DIR}/results/trace.txt"     "${LOCAL_METRICS}/trace.txt"     2>/dev/null || true
cp "${RUN_DIR}/results/report.html"   "${LOCAL_METRICS}/report.html"   2>/dev/null || true
cp "${RUN_DIR}/results/timeline.html" "${LOCAL_METRICS}/timeline.html" 2>/dev/null || true
echo "📊 Metrics saved: $LOCAL_METRICS"

# ── Cleanup work scratch (metrics already safe) ────────────────────────
rm -rf "${RUN_DIR}/work"
rm -f  "/workspace/config_${RUN_ID}.config"
echo "🧹 Work dir cleaned: ${RUN_DIR}/work"

exit $RUN_EXIT
