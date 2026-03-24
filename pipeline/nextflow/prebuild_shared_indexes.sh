#!/bin/bash
# prebuild_shared_indexes.sh
# Runs PREPARE_GENOME once and saves shared indexes to PVC
# Run this BEFORE the reuse experiment
# For Reuse of STAR_GENOMEGENERATE and BBMAP_BBSPLIT indexes by two concurrent users.

set -euo pipefail

NAMESPACE="nextflow"
LAUNCHER_POD="nextflow-launcher"
SHARED_DIR="/workspace/shared"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RUN_DIR="/workspace/runs/prebuild_${TIMESTAMP}"
PIPELINE_DIR="/workspace/.nextflow/assets/nf-core/rnaseq"

mkdir -p ./logs

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧬 Pre-building Shared Genome Indexes"
echo "Shared dir : $SHARED_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ─────────────────────────────────────────
# Check launcher pod
# ─────────────────────────────────────────
POD_STATUS=$(kubectl get pod "$LAUNCHER_POD" -n "$NAMESPACE" \
  -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")

if [[ "$POD_STATUS" != "Running" ]]; then
  echo "❌ ERROR: Launcher pod is not running"
  exit 1
fi
echo "✅ Launcher pod is running"

# ─────────────────────────────────────────
# Check if shared indexes already exist
# ─────────────────────────────────────────
STAR_EXISTS=$(kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  sh -c "[ -d ${SHARED_DIR}/star_index ] && echo yes || echo no")
BBSPLIT_EXISTS=$(kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  sh -c "[ -d ${SHARED_DIR}/bbsplit_index ] && echo yes || echo no")

if [[ "$STAR_EXISTS" == "yes" && "$BBSPLIT_EXISTS" == "yes" ]]; then
  echo "✅ Shared indexes already exist at $SHARED_DIR"
  echo "   star_index   : ${SHARED_DIR}/star_index"
  echo "   bbsplit_index: ${SHARED_DIR}/bbsplit_index"
  echo "Skip pre-build — delete $SHARED_DIR to force rebuild"
  exit 0
fi

# ─────────────────────────────────────────
# Create directories
# ─────────────────────────────────────────
echo "📁 Creating directories..."
kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  sh -c "mkdir -p ${RUN_DIR}/work ${RUN_DIR}/results ${SHARED_DIR} && chmod -R 777 ${RUN_DIR} ${SHARED_DIR}"
echo "✅ Directories created"

# ─────────────────────────────────────────
# Create prebuild config
# ─────────────────────────────────────────
PREBUILD_CONFIG="/workspace/config_prebuild_${TIMESTAMP}.config"

kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- sh -c "cat > ${PREBUILD_CONFIG} << 'CONFIGEOF'
process {
    executor = 'k8s'
    memory   = '4 GB'
    cpus     = 2
}

k8s {
    namespace        = 'nextflow'
    serviceAccount   = 'nextflow-sa'
    storageClaimName = 'nextflow-pvc'
    storageMountPath = '/workspace'
    computeResourceType = 'Job'

    pod = [
        [nodeSelector: 'kubernetes.io/hostname=gisele'],
        [annotation: 'prometheus.io/scrape', value: 'true'],
        [annotation: 'prometheus.io/port',   value: '9090'],
        [label: 'pipeline', value: 'rnaseq'],
        [label: 'user', value: 'prebuild'],
        [imagePullPolicy: 'Always']
    ]
}

workDir = '${RUN_DIR}/work'
CONFIGEOF"

echo "✅ Config created"

# ─────────────────────────────────────────
# Run pipeline — only PREPARE_GENOME
# ─────────────────────────────────────────
echo "🚀 Running PREPARE_GENOME to build shared indexes..."
echo "⏱  Started at: $(date)"

kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  nextflow run ${PIPELINE_DIR}/main.nf \
    -profile test \
    -c "${PREBUILD_CONFIG}" \
    --outdir "${RUN_DIR}/results" \
    --skip_alignment \
    --skip_pseudo_alignment \
    --skip_qc \
    -w "${RUN_DIR}/work" \
    -with-trace "${RUN_DIR}/results/trace.txt"

EXIT_CODE=$?
echo "⏱  Finished at: $(date)"

if [[ $EXIT_CODE -ne 0 ]]; then
  echo "❌ Pre-build FAILED with exit code $EXIT_CODE"
  exit $EXIT_CODE
fi

echo "✅ PREPARE_GENOME completed"

# ─────────────────────────────────────────
# Copy indexes to shared directory
# ─────────────────────────────────────────
echo "📁 Copying indexes to shared directory..."

kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  sh -c "
    # Find and copy STAR index
    STAR_INDEX=\$(find ${RUN_DIR}/work -name 'genomeParameters.txt' -exec dirname {} \; 2>/dev/null | head -1)
    if [ -n \"\$STAR_INDEX\" ]; then
      cp -r \"\$STAR_INDEX\" ${SHARED_DIR}/star_index
      echo 'STAR index copied from: '\$STAR_INDEX
    else
      echo 'WARNING: STAR index not found'
    fi

    # Find and copy BBSplit index
    BBSPLIT_INDEX=\$(find ${RUN_DIR}/work -name 'bbsplit_index' -type d 2>/dev/null | head -1)
    if [ -n \"\$BBSPLIT_INDEX\" ]; then
      cp -r \"\$BBSPLIT_INDEX\" ${SHARED_DIR}/bbsplit_index
      echo 'BBSplit index copied from: '\$BBSPLIT_INDEX
    else
      echo 'WARNING: BBSplit index not found'
    fi

    chmod -R 777 ${SHARED_DIR}
    echo 'DONE'
  "

# ─────────────────────────────────────────
# Verify
# ─────────────────────────────────────────
echo ""
echo "🔍 Verifying shared indexes..."
kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  ls -lh ${SHARED_DIR}/

# ─────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────
kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  rm -f "${PREBUILD_CONFIG}" 2>/dev/null || true

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Shared indexes ready at: $SHARED_DIR"
echo "   star_index   : ${SHARED_DIR}/star_index"
echo "   bbsplit_index: ${SHARED_DIR}/bbsplit_index"
echo ""
echo "Now run the reuse experiment:"
echo "  ./run_nextflow_shared_index.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit 0