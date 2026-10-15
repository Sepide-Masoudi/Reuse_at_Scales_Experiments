#!/bin/bash
# run_nextflow_partial_resume.sh
# S2-partial: 2 concurrent users where each user first runs 5 samples (phase 1, sequential),
# then resumes with 15 samples concurrently (phase 2 - only 10 new samples computed)

set -euo pipefail

NUM_USERS="${1:-2}"
NAMESPACE="nextflow"
LAUNCHER_POD="nextflow-launcher"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PIPELINE="/workspace/.nextflow/assets/nf-core/rnaseq/main.nf"
PIDS=()

mkdir -p ./logs ./metrics

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧬 Nextflow Partial Resume Runner (S2-partial)"
echo "Users      : $NUM_USERS"
echo "Phase 1    : 5 samples sequential (builds cache per user)"
echo "Phase 2    : 15 samples concurrent with -resume"
echo "Timestamp  : $TIMESTAMP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

POD_STATUS=$(kubectl get pod "$LAUNCHER_POD" -n "$NAMESPACE" \
  -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
if [[ "$POD_STATUS" != "Running" ]]; then
  echo "❌ ERROR: Launcher pod is not running"; exit 1
fi
echo "✅ Launcher pod is running"

echo "🧹 Cleaning up old failed pods..."
kubectl delete pods -n "$NAMESPACE" \
  --field-selector=status.phase=Failed \
  --ignore-not-found=true 2>/dev/null || true
echo "✅ Cleanup done"

# ─────────────────────────────────────────
# Create configs and directories for all users
# ─────────────────────────────────────────
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_partial_${TIMESTAMP}"
  RUN_DIR="/workspace/runs/${RUN_ID}"
  USER_CONFIG="/workspace/config_${RUN_ID}.config"

  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    sh -c "mkdir -p ${RUN_DIR}/work ${RUN_DIR}/results_phase1 ${RUN_DIR}/results_phase2 && chmod -R 777 ${RUN_DIR}"

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
        [nodeSelector: 'kubernetes.io/hostname=sm-gpu'],
        [annotation: 'prometheus.io/scrape', value: 'true'],
        [annotation: 'prometheus.io/port',   value: '9090'],
        [label: 'pipeline', value: 'rnaseq'],
        [label: 'user', value: 'user${i}'],
        [label: 'run_id', value: '${RUN_ID}'],
        [label: 'reuse', value: 'partial'],
        [imagePullPolicy: 'Always']
    ]
}
workDir = '${RUN_DIR}/work'
CONFIGEOF"
done

# ─────────────────────────────────────────
# PHASE 1: Run 5 samples SEQUENTIALLY per user
# (avoids .nextflow cache lock conflicts)
# ─────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo "📦 PHASE 1: Running 5 samples per user (sequential)"
echo "════════════════════════════════════════"

for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_partial_${TIMESTAMP}"
  RUN_DIR="/workspace/runs/${RUN_ID}"
  USER_CONFIG="/workspace/config_${RUN_ID}.config"

  echo "🚀 Phase 1 for user $i..."
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    sh -c "cd /workspace && NXF_HOME=/workspace/.nextflow_user${i} nextflow run ${PIPELINE} \
      -profile test \
      -c '${USER_CONFIG}' \
      --outdir '${RUN_DIR}/results_phase1' \
      -w '${RUN_DIR}/work' \
      -with-trace    '${RUN_DIR}/results_phase1/trace.txt' \
      -with-report   '${RUN_DIR}/results_phase1/report.html' \
      -with-timeline '${RUN_DIR}/results_phase1/timeline.html'" \
      > "./logs/${RUN_ID}_phase1.log" 2>&1

  if [[ $? -eq 0 ]]; then
    echo "✅ User $i Phase 1 completed"
  else
    echo "❌ User $i Phase 1 FAILED — aborting"
    exit 1
  fi
done

echo "✅ Phase 1 complete — cache built for all users"
echo "⏱ Waiting 30s for session locks to release..."
sleep 60
# Force remove any leftover lock files
for ui in $(seq 1 $NUM_USERS); do
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    sh -c "find /workspace/.nextflow_user${ui}/cache -name LOCK -delete 2>/dev/null || true"
done
echo "✅ Session locks cleared"

# ─────────────────────────────────────────
# PHASE 2: Resume with 15 samples CONCURRENTLY
# SMA framework measures energy from HERE
# ─────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo "♻️  PHASE 2: Resuming with 15 samples (concurrent)"
echo "   5 samples reused from cache, 10 new computed"
echo "════════════════════════════════════════"

PIDS=()
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_partial_${TIMESTAMP}"
  RUN_DIR="/workspace/runs/${RUN_ID}"
  USER_CONFIG="/workspace/config_${RUN_ID}.config"

  echo "🚀 Phase 2 for user $i (15 samples with -resume)..."
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    sh -c "cd /workspace && NXF_HOME=/workspace/.nextflow_user${i} nextflow run ${PIPELINE} \
      -profile test \
      --input /workspace/samplesheet_extended.csv \
      -c '${USER_CONFIG}' \
      --outdir '${RUN_DIR}/results_phase2' \
      -w '${RUN_DIR}/work' \
      -resume \
      --fasta https://raw.githubusercontent.com/nf-core/test-datasets/626c8fab639062eade4b10747e919341cbf9b41a/reference/genome.fasta \
      -with-trace    '${RUN_DIR}/results_phase2/trace.txt' \
      -with-report   '${RUN_DIR}/results_phase2/report.html' \
      -with-timeline '${RUN_DIR}/results_phase2/timeline.html'" \
      > "./logs/${RUN_ID}_phase2.log" 2>&1 &

  PIDS+=($!)
  echo "✅ User $i Phase 2 started (PID: ${PIDS[-1]})"
done

echo ""
echo "⏳ Waiting for Phase 2 to complete..."
FAILED=0
for i in "${!PIDS[@]}"; do
  PID="${PIDS[$i]}"
  USER_NUM=$((i + 1))
  if wait "$PID"; then
    echo "✅ User $USER_NUM Phase 2 completed"
  else
    echo "❌ User $USER_NUM Phase 2 FAILED"
    FAILED=$((FAILED + 1))
  fi
done

# ─────────────────────────────────────────
# Copy metrics
# ─────────────────────────────────────────
echo ""
echo "📊 Copying metrics..."
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_partial_${TIMESTAMP}"
  RUN_DIR="/workspace/runs/${RUN_ID}"
  LOCAL_METRICS="./metrics/${RUN_ID}"
  mkdir -p "$LOCAL_METRICS"
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    cat "${RUN_DIR}/results_phase2/trace.txt" > "${LOCAL_METRICS}/trace.txt" 2>/dev/null || true
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    cat "${RUN_DIR}/results_phase2/report.html" > "${LOCAL_METRICS}/report.html" 2>/dev/null || true
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    cat "${RUN_DIR}/results_phase2/timeline.html" > "${LOCAL_METRICS}/timeline.html" 2>/dev/null || true
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    cat "${RUN_DIR}/results_phase1/trace.txt" > "${LOCAL_METRICS}/trace_phase1.txt" 2>/dev/null || true
  echo "✅ Metrics saved to: $LOCAL_METRICS"
done

# ─────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────
echo ""
echo "🧹 Cleaning up configs..."
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_partial_${TIMESTAMP}"
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    rm -f "/workspace/config_${RUN_ID}.config" 2>/dev/null || true
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $FAILED -eq 0 ]]; then
  echo "🎉 Partial resume experiment complete"
  echo "   Phase 2: 5 cached + 10 new samples per user"
else
  echo "⚠️  $FAILED/$NUM_USERS users failed in Phase 2"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit $FAILED