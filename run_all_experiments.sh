#!/usr/bin/env bash
set -euo pipefail

# Function to wait for all workflows in a namespace
wait_for_all_workflows() {
    local namespace=$1
    echo "Waiting for all workflows in namespace '${namespace}' to finish..."
    
    # Get the list of workflow names (only workflow IDs)
    workflows=$(argo list -n "$namespace" -o name)
    
    # Wait for each workflow
    for wf_full in $workflows; do
        # Remove 'workflow/' prefix
        wf="${wf_full#workflow/}"
        echo "⏳ Waiting for workflow: $wf"
        argo wait "$wf" -n "$namespace"
    done
    
    echo "✅ All workflows in '${namespace}' completed"
}

echo "Starting first batch..."
pipeline/output/run_all_NO_reuse_workflows.sh

wait_for_all_workflows "no-reuse-pipeline"
echo "First batch completed ✅"

#echo "Starting second batch..."
#pipeline/output/run_all_reuse_workflows.sh

#wait_for_all_workflows "pipeline"
#echo "Second batch completed ✅"

# Create a flag to indicate experiments are done
echo "ALL_EXPERIMENTS_DONE=true"
touch experiments_done.flag
echo "Experiments done flag created ✅"
