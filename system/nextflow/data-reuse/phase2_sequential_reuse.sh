#!/bin/bash
# phase2_sequential_reuse.sh
# Runs sequential reuse experiment
# User 1 runs fresh, each subsequent user resumes from previous user's work dir
#
# Usage: ./phase2_sequential_reuse.sh <NUM_USERS> <REUSE_PCT> <BASELINE_TIMESTAMP>

set -euo pipefail

NUM_USERS="${1:-2}"
REUSE_PCT="${2:-10}"
BASELINE_TIMESTAMP="${3:-}"
NAMESPACE="nextflow"
FULL_SAMPLESHEET="/workspace/samplesheet_extended.csv"

if [[ "$REUSE_PCT" -eq 10 ]]; then
  SEED_SAMPLES=1
  SEED_SAMPLESHEET="/workspace/samplesheet_reuse10.csv"
elif [[ "$REUSE_PCT" -eq 20 ]]; then
  SEED_SAMPLES=2
  SEED_SAMPLESHEET="/workspace/samplesheet_reuse20.csv"
elif [[ "$REUSE_PCT" -eq 50 ]]; then
  SEED_SAMPLES=6
  SEED_SAMPLESHEET="/workspace/samplesheet_reuse50.csv"
else
  echo "❌ ERROR: REUSE_PCT must be 10, 20, or 50"; exit 1
fi

if [[ -z "$BASELINE_TIMESTAMP" ]]; then
  echo "❌ ERROR: Must provide baseline timestamp"; exit 1
fi

TIMESTAMP="$BASELINE_TIMESTAMP"
REUSE_TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧬 PHASE 2 — Sequential Reuse (${REUSE_PCT}%)"
echo "Users    : $NUM_USERS"
echo "Baseline : $TIMESTAMP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

mkdir -p /workspace/logs /workspace/metrics

# Verify baseline work dirs exist
for i in $(seq 1 "$NUM_USERS"); do
  BASELINE_RUN_DIR="/workspace/runs/user${i}_baseline_${TIMESTAMP}"
  if [[ ! -d "${BASELINE_RUN_DIR}/work" ]]; then
    echo "❌ ERROR: Baseline work dir not found for user $i: ${BASELINE_RUN_DIR}"; exit 1
  fi
  echo "✅ Baseline work dir found for user $i"
done

kubectl delete pods -n "$NAMESPACE" \
  --field-selector=status.phase=Failed \
  --ignore-not-found=true 2>/dev/null || true

# Create partial samplesheet for seeding
head -1 "$FULL_SAMPLESHEET" > "$SEED_SAMPLESHEET"
tail -n +2 "$FULL_SAMPLESHEET" | head -"$SEED_SAMPLES" >> "$SEED_SAMPLESHEET"
echo "✅ Seed samplesheet created: $SEED_SAMPLES samples"

# ─────────────────────────────────────────
# Step 1: Seed cache for user 1 (not measured)
# ─────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo "🔨 Seeding cache for user 1 (${SEED_SAMPLES} samples)"
echo "   NOT measured by SMA"
echo "════════════════════════════════════════"

SEED_RUN_ID="user1_seed${REUSE_PCT}pct_${REUSE_TIMESTAMP}"
SEED_RUN_DIR="/workspace/runs/${SEED_RUN_ID}"
SEED_WORK_DIR="/workspace/runs/user1_baseline_${TIMESTAMP}/work"
NXF_HOME_SEED="/workspace/.nextflow_seed1_${REUSE_TIMESTAMP}"

mkdir -p "${SEED_RUN_DIR}/results"
mkdir -p "$NXF_HOME_SEED"
cp -r /workspace/.nextflow_shared/plugins "$NXF_HOME_SEED/" 2>/dev/null || true
cp -r /workspace/.nextflow_shared/framework "$NXF_HOME_SEED/" 2>/dev/null || true
mkdir -p "$NXF_HOME_SEED/assets" && cp -r /workspace/.nextflow_shared/assets/.repos "$NXF_HOME_SEED/assets/" 2>/dev/null || true

cat > "/workspace/config_${SEED_RUN_ID}.config" << CONFIGEOF
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
        [label: 'user', value: 'user1'],
        [label: 'seed', value: '${REUSE_PCT}pct'],
        [imagePullPolicy: 'IfNotPresent']
    ]
}
workDir = '${SEED_WORK_DIR}'
CONFIGEOF

(cd "${SEED_RUN_DIR}" && export NXF_HOME="$NXF_HOME_SEED"; NXF_OPTS="-Dnxf.disable.histlock=true -Dnextflow.k8s.poll.interval=30s" \
nextflow run nf-core/rnaseq -r 3.26.0 \
  -profile test \
  --input "$SEED_SAMPLESHEET" \
  -c "/workspace/config_${SEED_RUN_ID}.config" \
  -c "/workspace/local_refs.config" \
  --outdir "${SEED_RUN_DIR}/results" \
  -w "${SEED_WORK_DIR}" \
  > "/workspace/logs/${SEED_RUN_ID}.log" 2>&1)

if [[ $? -eq 0 ]]; then
  echo "✅ Cache seeded for user 1"
else
  echo "❌ Seeding FAILED"; exit 1
fi

rm -f "/workspace/config_${SEED_RUN_ID}.config"

# ─────────────────────────────────────────
# Step 2: Sequential reuse runs — MEASURED by SMA
# ─────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo "🚀 Sequential reuse runs (${NUM_USERS} users, ${REUSE_PCT}%)"
echo "   SMA IS MEASURING NOW"
echo "════════════════════════════════════════"

PREV_WORK_DIR="/workspace/runs/user1_baseline_${TIMESTAMP}/work"

FAILED=0
for i in $(seq 1 "$NUM_USERS"); do
  REUSE_RUN_ID="user${i}_reuse${REUSE_PCT}pct_${REUSE_TIMESTAMP}"
  REUSE_RUN_DIR="/workspace/runs/${REUSE_RUN_ID}"
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
workDir = '${PREV_WORK_DIR}'
CONFIGEOF

  echo "🚀 Running user $i (reuse=${REUSE_PCT}%, work=${PREV_WORK_DIR})..."
  (cd "${REUSE_RUN_DIR}" && export NXF_HOME="$NXF_HOME"; NXF_OPTS="-Dnxf.disable.histlock=true -Dnextflow.k8s.poll.interval=30s" \
  nextflow run nf-core/rnaseq -r 3.26.0 \
    -profile test \
    --input "$FULL_SAMPLESHEET" \
    -c "/workspace/config_${REUSE_RUN_ID}.config" \
    -c "/workspace/local_refs.config" \
    --outdir "${REUSE_RUN_DIR}/results" \
    -w "${PREV_WORK_DIR}" \
    -resume \
    -with-trace    "${REUSE_RUN_DIR}/results/trace.txt" \
    -with-report   "${REUSE_RUN_DIR}/results/report.html" \
    -with-timeline "${REUSE_RUN_DIR}/results/timeline.html" \
    > "/workspace/logs/${REUSE_RUN_ID}.log" 2>&1)

  if [[ $? -eq 0 ]]; then
    echo "✅ User $i completed"
    PREV_WORK_DIR="/workspace/runs/user${i}_baseline_${TIMESTAMP}/work"
  else
    echo "❌ User $i FAILED"
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

rm -f "$SEED_SAMPLESHEET"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $FAILED -eq 0 ]]; then
  echo "🎉 Complete: ${NUM_USERS} users | ${REUSE_PCT}% reuse"
else
  echo "⚠️  $FAILED/${NUM_USERS} users failed"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit $FAILED