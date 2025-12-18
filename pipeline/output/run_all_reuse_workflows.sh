#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="pipeline"
WORKFLOW_FILE="pipeline_reuse.yaml"

echo "Submitting Argo workflows from ${WORKFLOW_FILE} in namespace ${NAMESPACE}"
echo "---------------------------------------------------------------"

# Split the YAML file into separate temporary files
csplit -f temp-workflow- "${WORKFLOW_FILE}" '/^---$/' '{*}'

echo "1️⃣ Running: parallel-full-data-generation-and-evaluation"
argo submit temp-workflow-00 -n "${NAMESPACE}"

echo "2️⃣ Running: synthesize-only"
argo submit temp-workflow-01 -n "${NAMESPACE}"

echo "3️⃣ Running: evaluation-only"
argo submit temp-workflow-02 -n "${NAMESPACE}"

echo "4️⃣ Running: full-data-generation-and-evaluation"
argo submit temp-workflow-03 -n "${NAMESPACE}"

# Clean up temporary files
rm temp-workflow-*

echo "---------------------------------------------------------------"
echo "✅ All workflows submitted successfully"