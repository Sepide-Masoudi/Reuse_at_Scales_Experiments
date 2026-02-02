#!/usr/bin/env bash
set -euo pipefail

# -----------------------------
# Usage check
# -----------------------------
if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <workflow-yaml-path> [namespace]"
  exit 1
fi

WORKFLOW_FILE="$1"
NAMESPACE="${2:-pipeline}"

echo "🚀 Submitting workflow: $WORKFLOW_FILE (ns=$NAMESPACE)"

# Submit and capture workflow name
WF_FULL=$(argo submit "$WORKFLOW_FILE" -n "$NAMESPACE" -o name)
WF_NAME="${WF_FULL#workflow/}"

echo "Submitted workflow: $WF_NAME"

# Wait until finished
echo "⏳ Waiting for completion..."
argo wait "$WF_NAME" -n "$NAMESPACE"

# Check final status
STATUS=$(argo get "$WF_NAME" -n "$NAMESPACE" -o json | jq -r '.status.phase')

echo "Final status: $STATUS"

if [[ "$STATUS" != "Succeeded" ]]; then
    echo "❌ Workflow failed"
    exit 1
fi

echo "✅ Workflow succeeded"
exit 0
