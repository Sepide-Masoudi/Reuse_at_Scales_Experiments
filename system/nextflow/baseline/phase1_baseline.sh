#!/bin/bash
# phase1_baseline.sh v3
# Key fix: writes a runner script to the pod and executes it
# instead of using heredocs with kubectl exec

set -euo pipefail

NUM_USERS="${1:-2}"
NAMESPACE="nextflow"
LAUNCHER_POD="nextflow-launcher"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PIPELINE="/workspace/.nextflow/assets/nf-core/rnaseq/main.nf"
FULL_SAMPLESHEET="/workspace/samplesheet_extended.csv"
PIDS=()

mkdir -p ./logs ./metrics

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧬 PHASE 1 — Baseline (no reuse)"
echo "Users     : $NUM_USERS"
echo "Timestamp : $TIMESTAMP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

POD_STATUS=$(kubectl get pod "$LAUNCHER_POD" -n "$NAMESPACE" \
  -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
if [[ "$POD_STATUS" != "Running" ]]; then
  echo "❌ ERROR: Launcher pod is not running"; exit 1
fi
echo "✅ Launcher pod is running"

kubectl delete pods -n "$NAMESPACE" \
  --field-selector=status.phase=Failed \
  --ignore-not-found=true 2>/dev/null || true

# Save timestamp for phase2
kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  sh -c "echo '${TIMESTAMP}:${NUM_USERS}' > /workspace/last_run_timestamp.txt"
echo "✅ Saved timestamp: $TIMESTAMP"

# Setup each user's isolated environment
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_baseline_${TIMESTAMP}"
  RUN_DIR="/workspace/runs/${RUN_ID}"
  NXF_HOME_I="/workspace/.nextflow_user${i}_${TIMESTAMP}"

  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    sh -c "mkdir -p ${RUN_DIR}/work ${RUN_DIR}/results && \
           chmod -R 777 ${RUN_DIR} && \
           mkdir -p ${NXF_HOME_I} && \
           cp -r /workspace/.nextflow/framework ${NXF_HOME_I}/ 2>/dev/null || true && \
           cp -r /workspace/.nextflow/plugins ${NXF_HOME_I}/ 2>/dev/null || true && \
           touch ${NXF_HOME_I}/history && \
           echo done"

  # Write k8s config
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    sh -c "cat > /workspace/config_${RUN_ID}.config << 'CONFIGEOF'
process {
    executor = 'k8s'
    memory   = '4 GB'
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
        [label: 'reuse', value: 'baseline'],
        [imagePullPolicy: 'IfNotPresent']
    ]
}
workDir = '${RUN_DIR}/work'
CONFIGEOF"

  # Write a runner script for this user inside the pod
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    sh -c "cat > /workspace/run_user${i}_${TIMESTAMP}.sh << 'RUNEOF'
#!/bin/sh
export NXF_HOME=/workspace/.nextflow_user${i}_${TIMESTAMP}
export NXF_DISABLE_CONFIGS=true
export NXF_OPTS=\"-Dnxf.disable.histlock=true\"
cd /workspace
exec nextflow run /workspace/.nextflow/assets/nf-core/rnaseq/main.nf \
  -profile test \
  --input /workspace/samplesheet_extended.csv \
  -c /workspace/config_user${i}_baseline_${TIMESTAMP}.config \
  --outdir /workspace/runs/user${i}_baseline_${TIMESTAMP}/results \
  -w /workspace/runs/user${i}_baseline_${TIMESTAMP}/work \
  -with-trace    /workspace/runs/user${i}_baseline_${TIMESTAMP}/results/trace.txt \
  -with-report   /workspace/runs/user${i}_baseline_${TIMESTAMP}/results/report.html \
  -with-timeline /workspace/runs/user${i}_baseline_${TIMESTAMP}/results/timeline.html
RUNEOF
chmod +x /workspace/run_user${i}_${TIMESTAMP}.sh
echo Config and runner ready for user ${i}"

  echo "✅ Setup done for user $i"
done

echo ""
echo "════════════════════════════════════════"
echo "🚀 Running $NUM_USERS users concurrently (baseline)"
echo "   No cache — SMA IS MEASURING NOW"
echo "════════════════════════════════════════"

PIDS=()
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_baseline_${TIMESTAMP}"
  echo "🚀 Starting user $i..."

  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    sh -c "/workspace/run_user${i}_${TIMESTAMP}.sh" \
    > "./logs/${RUN_ID}.log" 2>&1 &

  PIDS+=($!)
  echo "✅ User $i started (PID: ${PIDS[-1]})"
done

echo ""
echo "⏳ Waiting for all users to complete..."
FAILED=0
for i in "${!PIDS[@]}"; do
  PID="${PIDS[$i]}"
  USER_NUM=$((i + 1))
  if wait "$PID"; then
    echo "✅ User $USER_NUM completed"
  else
    echo "❌ User $USER_NUM FAILED"
    tail -5 "./logs/user${USER_NUM}_baseline_${TIMESTAMP}.log" 2>/dev/null || true
    FAILED=$((FAILED + 1))
  fi
done

echo ""
echo "📊 Copying metrics..."
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_baseline_${TIMESTAMP}"
  RUN_DIR="/workspace/runs/${RUN_ID}"
  LOCAL_METRICS="./metrics/${RUN_ID}"
  mkdir -p "$LOCAL_METRICS"
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    cat "${RUN_DIR}/results/trace.txt" > "${LOCAL_METRICS}/trace.txt" 2>/dev/null || true
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    cat "${RUN_DIR}/results/report.html" > "${LOCAL_METRICS}/report.html" 2>/dev/null || true
  echo "✅ Metrics saved to: $LOCAL_METRICS"
done

echo ""
echo "🧹 Cleaning up..."
for i in $(seq 1 "$NUM_USERS"); do
  RUN_ID="user${i}_baseline_${TIMESTAMP}"
  kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
    sh -c "rm -f /workspace/config_${RUN_ID}.config /workspace/run_user${i}_${TIMESTAMP}.sh 2>/dev/null; true"
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $FAILED -eq 0 ]]; then
  echo "🎉 Phase 1 complete: ${NUM_USERS} users"
  echo "   Timestamp: ${TIMESTAMP}"
else
  echo "⚠️  $FAILED/${NUM_USERS} users failed"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit $FAILED