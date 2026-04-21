process SUBREAD_FEATURECOUNTS {
    tag "${meta.id}"
    label 'process_medium'

    // No container needed — this process just calls the external service via curl
    container 'docker.io/curlimages/curl:8.5.0'

    input:
    tuple val(meta), path(bams), path(annotation)

    output:
    tuple val(meta), path("*featureCounts.tsv")        , emit: counts
    tuple val(meta), path("*featureCounts.tsv.summary") , emit: summary
    tuple val("${task.process}"), val('subread'), val('2.0.6')  , emit: versions_subread, topic: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args         = task.ext.args ?: ''
    def prefix       = task.ext.prefix ?: "${meta.id}"
    def paired_end   = meta.single_end ? false : true
    def strandedness = 0
    if (meta.strandedness == 'forward')  { strandedness = 1 }
    else if (meta.strandedness == 'reverse') { strandedness = 2 }

    //def bam_list = bams.collect { it.toString() }.join('","')
    def bam_list = bams.collect { "\"${it.toString()}\"" }.join(',')
    def service_url = "http://featurecounts-service.nextflow.svc.cluster.local:8080/run"
    def outdir = "/workspace/service_outputs/featurecounts/${prefix}"

    """
    # Call featureCounts service
    RESPONSE=\$(curl -sS -X POST "${service_url}" \\
        -H "Content-Type: application/json" \\
        -d '{
            "bams": ["${bam_list}"],
            "annotation": "${annotation}",
            "outdir": "${outdir}",
            "prefix": "${prefix}",
            "paired_end": ${paired_end ? 'true' : 'false'},
            "strandedness": ${strandedness},
            "cpus": ${task.cpus},
            "args": "${args}"
        }') || { echo "Curl failed"; exit 1; }

    # Check response
    STATUS=\$(echo "\$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','error'))")
    if [ "\$STATUS" != "success" ]; then
        echo "Service call failed: \$RESPONSE" >&2
        exit 1
    fi

    # Symlink outputs to current directory for Nextflow to collect
    COUNTS=\$(echo "\$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['counts'])")
    SUMMARY=\$(echo "\$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['summary'])")

    ln -s "\$COUNTS"  "${prefix}.featureCounts.tsv"
    ln -s "\$SUMMARY" "${prefix}.featureCounts.tsv.summary"
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch ${prefix}.featureCounts.tsv
    touch ${prefix}.featureCounts.tsv.summary
    """
}