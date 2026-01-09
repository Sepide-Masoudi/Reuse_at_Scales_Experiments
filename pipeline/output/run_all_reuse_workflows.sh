#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="pipeline"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKFLOW_FILE="$DIR/pipeline_reuse.yaml"

echo "Submitting Argo workflows (non-reuse) from ${WORKFLOW_FILE} in namespace ${NAMESPACE}"
echo "---------------------------------------------------------------"

# Check if csplit is available
if ! command -v csplit &> /dev/null; then
    echo "❌ Error: csplit command not found. Please install it or use a different method."
    echo "On macOS: brew install coreutils"
    echo "On Ubuntu/Debian: sudo apt-get install coreutils"
    exit 1
fi

# Check if file exists
if [ ! -f "${WORKFLOW_FILE}" ]; then
    echo "❌ Error: File ${WORKFLOW_FILE} not found!"
    exit 1
fi

# Clean up any old temp files
rm -f temp-workflow-*

# Split the YAML file into separate temporary files
echo "Splitting workflow file..."
csplit -f temp-workflow- "${WORKFLOW_FILE}" '/^---$/' '{*}' > /dev/null 2>&1

# Submit all split files that actually contain a workflow and capture their names
submitted_wfs=()
i=1
for wf in temp-workflow-*; do
    if grep -q "^kind: Workflow" "$wf"; then
        echo "${i}️⃣ Submitting workflow from $wf"
        # capture ONLY the workflow name (without "workflow/" prefix)
        wf_full=$(argo submit "$wf" -n "${NAMESPACE}" -o name)
        wf_name="${wf_full#workflow/}"
        echo "✅ Submitted workflow: $wf_name"
        submitted_wfs+=("$wf_name")
        ((i++))
    fi
done

# Output all submitted workflow names for the batch script
echo "${submitted_wfs[@]}"

# Clean up temporary files
rm -f temp-workflow-*

echo "---------------------------------------------------------------"
echo "✅ All workflows submitted successfully"
