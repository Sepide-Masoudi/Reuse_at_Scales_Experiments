#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="no-reuse-pipeline"
WORKFLOW_FILE="pipeline_noreuse.yaml"

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

# Split the YAML file into separate temporary files
echo "Splitting workflow file..."
csplit -f temp-workflow- "${WORKFLOW_FILE}" '/^---$/' '{*}' > /dev/null 2>&1

# Count the number of workflows
WORKFLOW_COUNT=$(ls temp-workflow-* 2>/dev/null | wc -l)
echo "Found ${WORKFLOW_COUNT} workflows"

if [ "${WORKFLOW_COUNT}" -lt 4 ]; then
    echo "⚠️ Warning: Expected 4 workflows, found ${WORKFLOW_COUNT}"
fi

echo "1️⃣ Running: parallel-full-data-generation-and-evaluation"
argo submit temp-workflow-00 -n "${NAMESPACE}"

echo "2️⃣ Running: synthesize-only"
if [ "${WORKFLOW_COUNT}" -ge 2 ]; then
    argo submit temp-workflow-01 -n "${NAMESPACE}"
else
    echo "⚠️ Skipping: Workflow not found in file"
fi

echo "3️⃣ Running: evaluation-only"
if [ "${WORKFLOW_COUNT}" -ge 3 ]; then
    argo submit temp-workflow-02 -n "${NAMESPACE}"
else
    echo "⚠️ Skipping: Workflow not found in file"
fi

echo "4️⃣ Running: full-data-generation-and-evaluation"
if [ "${WORKFLOW_COUNT}" -ge 4 ]; then
    argo submit temp-workflow-03 -n "${NAMESPACE}"
else
    echo "⚠️ Skipping: Workflow not found in file"
fi

# Clean up temporary files
rm -f temp-workflow-*

echo "---------------------------------------------------------------"
echo "✅ All workflows submitted successfully"