#!/bin/bash
# phase2_reuse.sh - Runs directly on CP node using local nextflow
# Must be run AFTER phase1_baseline.sh
# Reads timestamp from /workspace/last_run_timestamp.txt
#
# Usage: ./phase2_reuse.sh <NUM_USERS> <REUSE_PCT>
# REUSE_PCT: 10, 20, or 50

set -euo pipefail

NUM_USERS="${1:-2}"
REUSE_PCT="${2:-10}"
NAMESPACE="nextflow"
FULL_SAMPLESHEET="/workspace/samplesheet_extended.csv"
PIDS=()

if [[ "$REUSE_PCT" -eq 10 ]]; then
  PHASE1_SAMPLES=1
  PHASE1_SAMPLESHEET="/workspace/samplesheet_reuse10.csv"
elif [[ "$REUSE_PCT" -eq 20 ]]; then
  PHASE1_SAMPLES=2
  PHASE1_SAMPLESHEET="/workspace/samplesheet_reuse20.csv"
elif [[ "$REUSE_PCT" -eq 50 ]]; then
  PHASE1_SAMPLES=6
  PHASE1_SAMPLESHEET="/workspace/samplesheet_reuse50.csv"
else
  echo "❌ ERROR: REUSE_PCT must be 10, 20, or 50"; exit 1
fi

mkdir -p /workspace/logs /workspace/metrics

# Read timestamp from phase1
LAST_RUN=$(cat /workspace/last_run_timestamp.txt 2>/dev/null || echo "")
if [[ -z "$LAST_RUN" ]]; then
  echo "❌ ERROR: No phase1 timestamp found. Run phase1_baseline.sh first."; exit 1
fi

TIMESTAMP=$(echo "$LAST_RUN" | cut -d: -f1)
REUSE_TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧬 PHASE 2 — Reuse (${REUSE_PCT}%)"
echo "Users           : $NUM_USERS"
echo "Phase1 timestamp: $TIMESTAMP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Verify phase1 work dirs exist
for i in $(seq 1 "$NUM_USERS"); do
  PHASE1_RUN_DIR="/workspace/runs/user${i}_baseline_${TIMESTAMP}"
  if [[ ! -d "${PHASE1_RUN_DIR}/work" ]]; then
    echo "❌ ERROR: Phase1 work dir not found for user $i: ${PHASE1_RUN_DIR}"; exit 1
  fi
  echo "✅ Phase1 work dir found for user $i"
done

kubectl delete pods -n "$NAMESPACE" \
  --field-selector=status.phase=Failed \
  --ignore-not-found=true 2>/dev/null || true

# Create partial samplesheet for cache seeding
head -1 "$FULL_SAMPLESHEET" > "$PHASE1_SAMPLESHEET"
tail -n +2 "$FULL_SAMPLESHEET" | head -"$PHASE1_SAMPLES" >> "$PHASE1_SAMPLESHEET"
echo "✅ Samplesheet created: $PHASE1_SAMPLES samples"

# ─────────────────────────────────────────
# Seed cache sequentially per user
# ─────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo "🔨 Seeding cache (${PHASE1_SAMPLES} samples, sequential)"
echo "   NOT measured by SMA"
echo "════════════════════════════════════════"

for i in $(seq 1 "$NUM_USERS"); do
  PHASE1_RUN_DIR="/workspace/runs/user${i}_baseline_${TIMESTAMP}"
  REUSE_RUN_ID="user${i}_reuse${REUSE_PCT}pct_${REUSE_TIMESTAMP}"
  REUSE_RUN_DIR="/workspace/runs/${REUSE_RUN_ID}"
  NXF_HOME="/workspace/.nextflow_user${i}_${TIMESTAMP}"

  mkdir -p "${REUSE_RUN_DIR}/results_seed"
  chmod -R 777 "${REUSE_RUN_DIR}"

  # Copy plugins and framework to NXF_HOME (already exists from phase1)
  mkdir -p "$NXF_HOME"
  cp -r /workspace/.nextflow_shared/plugins "$NXF_HOME/" 2>/dev/null || true
  cp -r /workspace/.nextflow_shared/framework "$NXF_HOME/" 2>/dev/null || true

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
workDir = '/workspace/runs/user${i}_baseline_${TIMESTAMP}/work'
CONFIGEOF

  echo "🔨 Seeding cache for user $i..."
  NXF_HOME_FIXED="$NXF_HOME"
  (export NXF_HOME="$NXF_HOME_FIXED"; NXF_OPTS="-Dnxf.disable.histlock=true" \
  nextflow run nf-core/rnaseq -r 3.26.0 \
    -profile test \
    --input "$PHASE1_SAMPLESHEET" \
    -c "/workspace/config_${REUSE_RUN_ID}.config" \
    --outdir "${REUSE_RUN_DIR}/results_seed" \
    -w "/workspace/runs/user${i}_baseline_${TIMESTAMP}/work" \
    > "/workspace/logs/${REUSE_RUN_ID}_seed.log" 2>&1)

  if [[ $? -eq 0 ]]; then
    echo "✅ Cache seeded for user $i"
  else
    echo "❌ Cache seeding FAILED for user $i"
    tail -5 "/workspace/logs/${REUSE_RUN_ID}_seed.log"
    exit 1
  fi

  # Clear lock files
  find "${NXF_HOME}/cache" -name 'LOCK' -delete 2>/dev/null || true
  echo "🔓 Lock cleared for user $i"
done

echo "✅ All caches seeded"
echo "⏳ Waiting 30s before concurrent reuse run..."
sleep 30

# ─────────────────────────────────────────
# Concurrent reuse run — MEASURED by SMA
# ─────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo "🚀 Concurrent reuse run (${NUM_USERS} users, ${REUSE_PCT}% cached)"
echo "   SMA IS MEASURING NOW"
echo "════════════════════════════════════════"

PIDS=()
for i in $(seq 1 "$NUM_USERS"); do
  PHASE1_RUN_DIR="/workspace/runs/user${i}_baseline_${TIMESTAMP}"
  REUSE_RUN_ID="user${i}_reuse${REUSE_PCT}pct_${REUSE_TIMESTAMP}"
  REUSE_RUN_DIR="/workspace/runs/${REUSE_RUN_ID}"
  NXF_HOME="/workspace/.nextflow_user${i}_${TIMESTAMP}"

  mkdir -p "${REUSE_RUN_DIR}/results"
  chmod -R 777 "${REUSE_RUN_DIR}"

  echo "🚀 Starting user $i (reuse=${REUSE_PCT}%)..."
  NXF_HOME_FIXED="$NXF_HOME"
  (export NXF_HOME="$NXF_HOME_FIXED"; NXF_OPTS="-Dnxf.disable.histlock=true" \
  nextflow run nf-core/rnaseq -r 3.26.0 \
    -profile test \
    --input "$FULL_SAMPLESHEET" \
    -c "/workspace/config_${REUSE_RUN_ID}.config" \
    --outdir "${REUSE_RUN_DIR}/results" \
    -w "/workspace/runs/user${i}_baseline_${TIMESTAMP}/work" \
    -resume \
    -with-trace    "${REUSE_RUN_DIR}/results/trace.txt" \
    -with-report   "${REUSE_RUN_DIR}/results/report.html" \
    -with-timeline "${REUSE_RUN_DIR}/results/timeline.html" \
    > "/workspace/logs/${REUSE_RUN_ID}.log" 2>&1) &

  PIDS+=($!)
  echo "✅ User $i started (PID: ${PIDS[-1]})"
done

echo ""
echo "⏳ Waiting for all reuse runs to complete..."
FAILED=0
for i in "${!PIDS[@]}"; do
  PID="${PIDS[$i]}"
  USER_NUM=$((i + 1))
  REUSE_RUN_ID="user${USER_NUM}_reuse${REUSE_PCT}pct_${REUSE_TIMESTAMP}"
  if wait "$PID"; then
    echo "✅ User $USER_NUM completed"
  else
    echo "❌ User $USER_NUM FAILED"
    tail -5 "/workspace/logs/${REUSE_RUN_ID}.log" 2>/dev/null || true
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
  echo "✅ Metrics saved to: $LOCAL_METRICS"
done

echo ""
echo "🧹 Cleaning up..."
for i in $(seq 1 "$NUM_USERS"); do
  REUSE_RUN_ID="user${i}_reuse${REUSE_PCT}pct_${REUSE_TIMESTAMP}"
  rm -f "/workspace/config_${REUSE_RUN_ID}.config" 2>/dev/null || true
done
rm -f "$PHASE1_SAMPLESHEET" 2>/dev/null || true

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $FAILED -eq 0 ]]; then
  echo "🎉 Phase 2 complete: ${NUM_USERS} users | ${REUSE_PCT}% reuse"
else
  echo "⚠️  $FAILED/${NUM_USERS} users failed"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit $FAILED