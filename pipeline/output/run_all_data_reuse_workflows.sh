#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <workflow-yaml-path> [namespace]"
    exit 1
fi

WORKFLOW_FILE="$1"
NAMESPACE="${2:-pipeline}"

echo "Submitting Argo workflows from ${WORKFLOW_FILE} in namespace ${NAMESPACE}"
echo "---------------------------------------------------------------"

if ! command -v csplit &> /dev/null; then
    echo "Error: csplit command not found."
    exit 1
fi

if [ ! -f "${WORKFLOW_FILE}" ]; then
    echo "Error: File ${WORKFLOW_FILE} not found!"
    exit 1
fi

rm -f temp-workflow-*

echo "Splitting workflow file..."
csplit -f temp-workflow- "${WORKFLOW_FILE}" '/^---$/' '{*}' > /dev/null 2>&1

submitted_wfs=()
i=1

for wf in temp-workflow-*; do
    if grep -q "^kind: Workflow" "$wf"; then
        echo "${i}) Submitting workflow from $wf"

        wf_full=$(argo submit "$wf" -n "${NAMESPACE}" -o name)
        wf_name="${wf_full#workflow/}"

        echo "Submitted workflow: $wf_name"
        submitted_wfs+=("$wf_name")

        ((i++))

#        echo "Waiting 15 seconds before next submission..."
#        sleep 15
    fi
done

rm -f temp-workflow-*

echo "---------------------------------------------------------------"
echo "Waiting for all workflows to complete..."

# ---- wait and verify all workflows ----
for wf_name in "${submitted_wfs[@]}"; do
    echo "Waiting for workflow: $wf_name"

    argo wait "$wf_name" -n "$NAMESPACE"

    status=$(argo get "$wf_name" -n "$NAMESPACE" -o json | jq -r '.status.phase')

    echo "Final status for $wf_name: $status"

    if [[ "$status" != "Succeeded" ]]; then
        echo "Workflow $wf_name failed"
        exit 1
    fi
done

echo "---------------------------------------------------------------"
echo "All workflows completed successfully"
exit 0