#!/bin/bash
# run_nextflow_sequential_reuse.sh
# Runs 2 users sequentially where user2 reuses user1's cached artifacts via -resume

set -euo pipefail

NAMESPACE="nextflow"
LAUNCHER_POD="nextflow-launcher"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p ./logs ./metrics

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧬 Nextflow Sequential Reuse Runner"
echo "User 1 → full run, User 2 → reuse cache"
echo "Timestamp : $TIMESTAMP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ─────────────────────────────────────────
# Check launcher pod
# ─────────────────────────────────────────
POD_STATUS=$(kubectl get pod "$LAUNCHER_POD" -n "$NAMESPACE" \
  -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")

if [[ "$POD_STATUS" != "Running" ]]; then
  echo "❌ ERROR: Launcher pod is not running"
  echo "Recreate it with: kubectl apply -f nextflow-launcher.yaml"
  exit 1
fi
echo "✅ Launcher pod is running"

# ─────────────────────────────────────────
# Clean up old failed pods
# ─────────────────────────────────────────
echo "🧹 Cleaning up old failed pods..."
kubectl delete pods -n "$NAMESPACE" \
  --field-selector=status.phase=Failed \
  --ignore-not-found=true 2>/dev/null || true
echo "✅ Cleanup done"

# ─────────────────────────────────────────
# Shared work dir — both users point here
# ─────────────────────────────────────────
SHARED_WORK="/workspace/runs/shared_work_${TIMESTAMP}"

# ─────────────────────────────────────────
# USER 1 — full run, builds the cache
# ─────────────────────────────────────────
RUN_ID_U1="user1_${TIMESTAMP}"
RUN_DIR_U1="/workspace/runs/${RUN_ID_U1}"
USER_CONFIG_U1="/workspace/config_user1_${TIMESTAMP}.config"

echo ""
echo "👤 Setting up User 1..."
kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  sh -c "mkdir -p ${RUN_DIR_U1}/results ${SHARED_WORK} && chmod -R 777 ${RUN_DIR_U1} ${SHARED_WORK}"

kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- sh -c "cat > ${USER_CONFIG_U1} << 'CONFIGEOF'
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
        [label: 'user', value: 'user1'],
        [label: 'run_id', value: '${RUN_ID_U1}'],
        [imagePullPolicy: 'Always']
    ]
}

workDir = '${SHARED_WORK}'
CONFIGEOF"

echo "🚀 Launching User 1 (full run)..."
echo "⏱  User 1 started at: $(date)"

kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  nextflow run nf-core/rnaseq \
    -revision 3.23.0 \
    -profile test \
    -c "${USER_CONFIG_U1}" \
    --outdir "${RUN_DIR_U1}/results" \
    -w "${SHARED_WORK}" \
    -with-trace    "${RUN_DIR_U1}/results/trace.txt" \
    -with-report   "${RUN_DIR_U1}/results/report.html" \
    -with-timeline "${RUN_DIR_U1}/results/timeline.html"

EXIT_U1=$?
echo "⏱  User 1 finished at: $(date)"

if [[ $EXIT_U1 -ne 0 ]]; then
  echo "❌ User 1 FAILED — aborting reuse experiment"
  exit $EXIT_U1
fi
echo "✅ User 1 completed — cache is ready at ${SHARED_WORK}"

# ─────────────────────────────────────────
# USER 2 — resume from user1's cache
# ─────────────────────────────────────────
RUN_ID_U2="user2_${TIMESTAMP}"
RUN_DIR_U2="/workspace/runs/${RUN_ID_U2}"
USER_CONFIG_U2="/workspace/config_user2_${TIMESTAMP}.config"

echo ""
echo "👤 Setting up User 2 (reuse mode)..."
kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  sh -c "mkdir -p ${RUN_DIR_U2}/results && chmod -R 777 ${RUN_DIR_U2}"

kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- sh -c "cat > ${USER_CONFIG_U2} << 'CONFIGEOF'
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
        [label: 'user', value: 'user2'],
        [label: 'run_id', value: '${RUN_ID_U2}'],
        [imagePullPolicy: 'Always']
    ]
}

workDir = '${SHARED_WORK}'
CONFIGEOF"

echo "🚀 Launching User 2 (reuse from User 1 cache)..."
echo "⏱  User 2 started at: $(date)"

kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  nextflow run nf-core/rnaseq \
    -revision 3.23.0 \
    -profile test \
    -c "${USER_CONFIG_U2}" \
    --outdir "${RUN_DIR_U2}/results" \
    -w "${SHARED_WORK}" \
    -with-trace    "${RUN_DIR_U2}/results/trace.txt" \
    -with-report   "${RUN_DIR_U2}/results/report.html" \
    -with-timeline "${RUN_DIR_U2}/results/timeline.html" \
    -resume

EXIT_U2=$?
echo "⏱  User 2 finished at: $(date)"

if [[ $EXIT_U2 -ne 0 ]]; then
  echo "❌ User 2 FAILED"
  exit $EXIT_U2
fi
echo "✅ User 2 completed"

# ─────────────────────────────────────────
# Copy metrics locally
# ─────────────────────────────────────────
echo ""
echo "📊 Copying metrics..."
for user in 1 2; do
  if [[ $user -eq 1 ]]; then
    RUN_ID="${RUN_ID_U1}"
    RUN_DIR="${RUN_DIR_U1}"
  else
    RUN_ID="${RUN_ID_U2}"
    RUN_DIR="${RUN_DIR_U2}"
  fi

  LOCAL_METRICS="./metrics/${RUN_ID}"
  mkdir -p "$LOCAL_METRICS"

  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    cat "${RUN_DIR}/results/trace.txt" > "${LOCAL_METRICS}/trace.txt" 2>/dev/null || true
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    cat "${RUN_DIR}/results/report.html" > "${LOCAL_METRICS}/report.html" 2>/dev/null || true
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    cat "${RUN_DIR}/results/timeline.html" > "${LOCAL_METRICS}/timeline.html" 2>/dev/null || true

  echo "✅ Metrics saved to: $LOCAL_METRICS"
done

# ─────────────────────────────────────────
# Cleanup per-user configs from PVC
# ─────────────────────────────────────────
echo ""
echo "🧹 Cleaning up configs..."
kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  rm -f "${USER_CONFIG_U1}" "${USER_CONFIG_U2}" 2>/dev/null || true

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Reuse experiment complete"
echo "  User 1 (full run) : $RUN_ID_U1"
echo "  User 2 (reuse)    : $RUN_ID_U2"
echo "  Shared work dir   : $SHARED_WORK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit 0