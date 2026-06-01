#!/bin/bash
set -euo pipefail

NUM_USERS="${1:-2}"
REUSE_PCT="${2:-10}"
BASELINE_TIMESTAMP="${3:-}"

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
SEED_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FULL_SAMPLESHEET="/workspace/samplesheet_extended.csv"
NXF_HOME="/workspace/.nextflow_shared_home"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔨 SEEDING (${REUSE_PCT}% = ${SEED_SAMPLES} samples)"
echo "Seeding users 2 to $NUM_USERS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

mkdir -p /workspace/logs "$NXF_HOME"
cp -r /workspace/.nextflow_shared/plugins "$NXF_HOME/" 2>/dev/null || true
cp -r /workspace/.nextflow_shared/framework "$NXF_HOME/" 2>/dev/null || true
mkdir -p "$NXF_HOME/assets" && cp -r /workspace/.nextflow_shared/assets/.repos "$NXF_HOME/assets/" 2>/dev/null || true

head -1 "$FULL_SAMPLESHEET" > "$SEED_SAMPLESHEET"
tail -n +2 "$FULL_SAMPLESHEET" | head -"$SEED_SAMPLES" >> "$SEED_SAMPLESHEET"
echo "✅ Seed samplesheet: $SEED_SAMPLES samples"

for i in $(seq 2 "$NUM_USERS"); do
  BASELINE_WORK_DIR="/workspace/runs/user${i}_baseline_${TIMESTAMP}/work"
  SEED_RUN_ID="user${i}_seed${REUSE_PCT}pct_${SEED_TIMESTAMP}"
  SEED_RUN_DIR="/workspace/runs/${SEED_RUN_ID}"

  if [[ ! -d "$BASELINE_WORK_DIR" ]]; then
    echo "❌ ERROR: Baseline work dir not found for user $i"; exit 1
  fi

  mkdir -p "${SEED_RUN_DIR}/results"

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
        [label: 'user', value: 'user${i}'],
        [label: 'seed', value: '${REUSE_PCT}pct'],
        [imagePullPolicy: 'IfNotPresent']
    ]
}
workDir = '${BASELINE_WORK_DIR}'
CONFIGEOF

  echo "🔨 Seeding user $i..."
  (cd "${SEED_RUN_DIR}" && export NXF_HOME="$NXF_HOME"; \
  NXF_OPTS="-Dnxf.disable.histlock=true -Dnextflow.k8s.poll.interval=30s" \
  nextflow run nf-core/rnaseq -r 3.26.0 \
    -profile test \
    --input "$SEED_SAMPLESHEET" \
    -c "/workspace/config_${SEED_RUN_ID}.config" \
    -c "/workspace/local_refs.config" \
    --outdir "${SEED_RUN_DIR}/results" \
    -w "${BASELINE_WORK_DIR}" \
    > "/workspace/logs/${SEED_RUN_ID}.log" 2>&1)

  if [[ $? -eq 0 ]]; then
    echo "✅ User $i seeded"
    SESSION_UUID=$(grep 'Session UUID' "${SEED_RUN_DIR}/.nextflow.log" 2>/dev/null | awk '{print $NF}' | head -1)
    echo "$SESSION_UUID" > "/workspace/session_uuid_user${i}_${REUSE_PCT}pct.txt"
    echo "$SEED_RUN_DIR" > "/workspace/seed_run_dir_user${i}_${REUSE_PCT}pct.txt"
    echo "✅ Session UUID: $SESSION_UUID"
  else
    echo "❌ Seeding FAILED for user $i"
    tail -5 "/workspace/logs/${SEED_RUN_ID}.log"
    exit 1
  fi

  rm -f "/workspace/config_${SEED_RUN_ID}.config"
done

rm -f "$SEED_SAMPLESHEET"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Seeding complete for users 2-${NUM_USERS}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"