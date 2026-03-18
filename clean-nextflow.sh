#!/bin/bash
# clean_experiment_env.sh
# Cleans up nextflow environment before a new experiment round

set -euo pipefail

NAMESPACE="nextflow"
LAUNCHER_POD="nextflow-launcher"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧹 Cleaning Nextflow Experiment Environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ─────────────────────────────────────────
# 1. Delete all task pods (not launcher)
# ─────────────────────────────────────────
echo "🗑  Deleting task pods..."
kubectl delete pods -n "$NAMESPACE" \
  --field-selector=status.phase=Failed \
  --ignore-not-found=true 2>/dev/null || true
kubectl delete pods -n "$NAMESPACE" \
  --field-selector=status.phase=Succeeded \
  --ignore-not-found=true 2>/dev/null || true

# Force delete any stuck running task pods (not the launcher)
kubectl get pods -n "$NAMESPACE" --no-headers \
  | grep "^nf-" \
  | awk '{print $1}' \
  | xargs -r kubectl delete pod -n "$NAMESPACE" --force --grace-period=0 2>/dev/null || true

echo "✅ Task pods deleted"

# ─────────────────────────────────────────
# 2. Clean PVC (keep config)
# ─────────────────────────────────────────
echo "📁 Cleaning PVC..."
kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  sh -c "
    rm -rf /workspace/runs \
           /workspace/work \
           /workspace/work-fresh \
           /workspace/results \
           /workspace/results-fresh
    mkdir -p /workspace/runs
    chmod 777 /workspace/runs
    echo 'PVC cleaned'
  "
echo "✅ PVC cleaned"

# ─────────────────────────────────────────
# 3. Verify config is still intact
# ─────────────────────────────────────────
echo "🔍 Verifying config..."
kubectl exec "$LAUNCHER_POD" -n "$NAMESPACE" -- \
  ls -lh /workspace/
echo "✅ Config intact"

# ─────────────────────────────────────────
# 4. Check available resources
# ─────────────────────────────────────────
echo "📊 Current node resources:"
kubectl describe node gisele | grep -A8 "Allocated resources"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Environment ready for next experiment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"