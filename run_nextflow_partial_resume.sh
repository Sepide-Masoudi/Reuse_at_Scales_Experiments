#!/bin/bash
# run_nextflow_partial_resume.sh
# S2-partial: N concurrent users, each first runs P% of samples (phase 1, sequential),
# then resumes with all 15 samples concurrently (phase 2)
# Usage: ./run_nextflow_partial_resume.sh <NUM_USERS> <REUSE_PCT>
# REUSE_PCT: 10, 20, or 50

set -euo pipefail

NUM_USERS="${1:-2}"
REUSE_PCT="${2:-20}"
NAMESPACE="nextflow"
LAUNCHER_POD="nextflow-launcher"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PIPELINE="/workspace/.nextflow/assets/nf-core/rnaseq/main.nf"
FULL_SAMPLESHEET="/workspace/samplesheet_extended.csv"
PIDS=()

# Compute how many samples to use in Phase 1 based on reuse percentage
# 15 samples total: 10%→2, 20%→3, 50%→8
if [[ "$REUSE_PCT" -eq 10 ]]; then
  PHASE1_SAMPLES=2
  PHASE1_SAMPLESHEET="/workspace/samplesheet_reuse10.csv"
elif [[ "$REUSE_PCT" -eq 20 ]]; then
  PHASE1_SAMPLES=3
  PHASE1_SAMPLESHEET="/workspace/samplesheet_reuse20.csv"
elif [[ "$REUSE_PCT" -eq 50 ]]; then
  PHASE1_SAMPLES=8
  PHASE1_SAMPLESHEET="/workspace/samplesheet_reuse50.csv"
else
  echo "❌ ERROR: REUSE_PCT must be 10, 20, or 50 (got: $REUSE_PCT)"
  exit 1
fi

mkdir -p ./logs ./metrics

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧬 Nextflow Partial Resume Runner (S2-partial)"
echo "Users        : $NUM_USERS"
echo "Reuse target : ${REUSE_PCT}% (Phase 1: ${PHASE1_SAMPLES} samples)"
echo "Phase 2      : 15 samples with -resume"
echo "Timestamp    : $TIMESTAMP"
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
# Create phase1 samplesheet on PVC
# (first N lines of the full samplesheet)
# ─────────────────────────────────────────
echo "📋 Creating Phase 1 samplesheet (${PHASE1_SAMPLES} samples)..."
kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  sh -c "head -1 ${FULL_SAMPLESHEET} > ${PHASE1_SAMPLESHEET} && \
         tail -n +2 ${FULL_SAMPLESHEET} | head -${PHASE1_SAMPLES} >> ${PHASE1_SAMPLESHEET} && \
         echo 'Phase 1 samplesheet:' && cat ${PHASE1_SAMPLESHEET}"

# ─────────────────────────────────────────
# Create configs and directories for all users
# ─────────────────────────────────────────
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_partial${REUSE_PCT}pct_${TIMESTAMP}"
  RUN_DIR="/workspace/runs/${RUN_ID}"
  USER_CONFIG="/workspace/config_${RUN_ID}.config"

  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    sh -c "mkdir -p ${RUN_DIR}/work ${RUN_DIR}/results_phase1 \
           ${RUN_DIR}/results_phase2 && chmod -R 777 ${RUN_DIR}"

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
# PHASE 1: Run partial samplesheet SEQUENTIALLY
# (avoids .nextflow cache lock conflicts)
# ─────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo "📦 PHASE 1: ${PHASE1_SAMPLES} samples per user (sequential)"
echo "════════════════════════════════════════"

for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_partial${REUSE_PCT}pct_${TIMESTAMP}"
  RUN_DIR="/workspace/runs/${RUN_ID}"
  USER_CONFIG="/workspace/config_${RUN_ID}.config"

  echo "🚀 Phase 1 for user $i..."
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    sh -c "cd /workspace && NXF_HOME=/workspace/.nextflow_user${i} \
      nextflow run ${PIPELINE} \
      -profile test \
      --input '${PHASE1_SAMPLESHEET}' \
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
echo "⏱ Waiting 60s and clearing session locks..."
sleep 60
for ui in $(seq 1 $NUM_USERS); do
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    sh -c "find /workspace/.nextflow_user${ui}/cache -name LOCK -delete 2>/dev/null || true"
done
echo "✅ Session locks cleared"

# ─────────────────────────────────────────
# PHASE 2: Resume with full 15 samples CONCURRENTLY
# SMA measures energy from HERE
# ─────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo "♻️  PHASE 2: 15 samples concurrent (-resume)"
echo "   ${PHASE1_SAMPLES} cached + $((15 - PHASE1_SAMPLES)) new per user"
echo "════════════════════════════════════════"

PIDS=()
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_partial${REUSE_PCT}pct_${TIMESTAMP}"
  RUN_DIR="/workspace/runs/${RUN_ID}"
  USER_CONFIG="/workspace/config_${RUN_ID}.config"

  echo "🚀 Phase 2 for user $i (15 samples with -resume)..."
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    sh -c "cd /workspace && NXF_HOME=/workspace/.nextflow_user${i} \
      nextflow run ${PIPELINE} \
      -profile test \
      --input '${FULL_SAMPLESHEET}' \
      -c '${USER_CONFIG}' \
      --outdir '${RUN_DIR}/results_phase2' \
      -w '${RUN_DIR}/work' \
      -resume \
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
  RUN_ID="user${i}_partial${REUSE_PCT}pct_${TIMESTAMP}"
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
echo "🧹 Cleaning up configs and samplesheets..."
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_partial${REUSE_PCT}pct_${TIMESTAMP}"
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    rm -f "/workspace/config_${RUN_ID}.config" 2>/dev/null || true
done
kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  rm -f "${PHASE1_SAMPLESHEET}" 2>/dev/null || true

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $FAILED -eq 0 ]]; then
  echo "🎉 Partial resume complete"
  echo "   Users: ${NUM_USERS}  Reuse: ${REUSE_PCT}%"
  echo "   Phase 1: ${PHASE1_SAMPLES} cached + $((15-PHASE1_SAMPLES)) new"
else
  echo "⚠️  $FAILED/${NUM_USERS} users failed in Phase 2"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit $FAILED