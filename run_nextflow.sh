#!/bin/bash
# run_nextflow.sh
# Runs nf-core/rnaseq pipeline via the nextflow-launcher pod
# Called by the SMA experiment framework (run_experiments.py)

set -euo pipefail

NAMESPACE="nextflow"
LAUNCHER_POD="nextflow-launcher"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RUN_ID="rnaseq_${TIMESTAMP}"
RUN_DIR="/workspace/runs/${RUN_ID}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧬 Nextflow Pipeline Runner"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Run ID      : $RUN_ID"
echo "Run dir     : $RUN_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ─────────────────────────────────────────
# Check launcher pod is running
# ─────────────────────────────────────────
echo "🔍 Checking launcher pod..."
POD_STATUS=$(kubectl get pod "$LAUNCHER_POD" -n "$NAMESPACE" \
  -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")

if [[ "$POD_STATUS" != "Running" ]]; then
  echo "❌ ERROR: Launcher pod is not running (status: $POD_STATUS)"
  echo "Recreate it with: kubectl apply -f nextflow-launcher.yaml"
  exit 1
fi
echo "✅ Launcher pod is running"

# ─────────────────────────────────────────
# Create run directory on PVC
# ─────────────────────────────────────────
echo "📁 Creating run directory on PVC..."
kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  sh -c "mkdir -p ${RUN_DIR}/work ${RUN_DIR}/results && chmod -R 777 ${RUN_DIR}"
echo "✅ Directories created"

# ─────────────────────────────────────────
# Clean up old failed pods
# ─────────────────────────────────────────
echo "🧹 Cleaning up old failed pods..."
kubectl delete pods -n "$NAMESPACE" \
  --field-selector=status.phase=Failed \
  --ignore-not-found=true 2>/dev/null || true
echo "✅ Cleanup done"

# ─────────────────────────────────────────
# Run the pipeline
# ─────────────────────────────────────────
echo "🚀 Launching pipeline..."
echo "⏱  Started at: $(date)"

kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  nextflow run nf-core/rnaseq \
    -revision 3.23.0 \
    -profile test \
    -c /workspace/nextflow.config \
    --outdir "${RUN_DIR}/results" \
    -w "${RUN_DIR}/work" \
    -with-trace    "${RUN_DIR}/results/trace.txt" \
    -with-report   "${RUN_DIR}/results/report.html" \
    -with-timeline "${RUN_DIR}/results/timeline.html"

EXIT_CODE=$?
echo "⏱  Finished at: $(date)"

# ─────────────────────────────────────────
# Check result
# ─────────────────────────────────────────
if [[ $EXIT_CODE -ne 0 ]]; then
  echo "❌ Pipeline FAILED with exit code $EXIT_CODE"
  exit $EXIT_CODE
fi
echo "✅ Pipeline completed successfully"

# ─────────────────────────────────────────
# Copy metrics to local directory
# ─────────────────────────────────────────
LOCAL_METRICS="./metrics/${RUN_ID}"
mkdir -p "$LOCAL_METRICS"

echo "📊 Copying metrics to $LOCAL_METRICS..."

kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  cat "${RUN_DIR}/results/trace.txt" > "${LOCAL_METRICS}/trace.txt"

kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  cat "${RUN_DIR}/results/report.html" > "${LOCAL_METRICS}/report.html"

kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  cat "${RUN_DIR}/results/timeline.html" > "${LOCAL_METRICS}/timeline.html"

echo "✅ Metrics saved to: $LOCAL_METRICS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Run complete: $RUN_ID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit 0