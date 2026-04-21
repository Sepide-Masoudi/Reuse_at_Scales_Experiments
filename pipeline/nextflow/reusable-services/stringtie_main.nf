process STRINGTIE_STRINGTIE {
    tag "$meta.id"
    label 'process_medium'

    // No container needed — this process just calls the external service via curl
    container 'docker.io/curlimages/curl:8.5.0'

    input:
    tuple val(meta), path(bam)
    path  annotation_gtf

    output:
    tuple val(meta), path("*.transcripts.gtf")  , emit: transcript_gtf
    tuple val(meta), path("*.abundance.txt")     , emit: abundance
    tuple val(meta), path("*.coverage.gtf")      , optional: true, emit: coverage_gtf
    tuple val(meta), path("*.ballgown")          , optional: true, emit: ballgown
    tuple val("${task.process}"), val('stringtie'), val('2.2.3'), emit: versions_stringtie, topic: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args        = task.ext.args ?: ''
    def prefix      = task.ext.prefix ?: "${meta.id}"
    def strandedness = meta.strandedness ?: 'unstranded'
    def service_url = "http://stringtie-service.nextflow.svc.cluster.local:8081/run"
    def outdir      = "/workspace/service_outputs/stringtie/${prefix}"
    def annotation  = annotation_gtf ? annotation_gtf.toString() : ""

    """
    # Call StringTie service
    RESPONSE=\$(curl -sS -X POST "${service_url}" \\
        -H "Content-Type: application/json" \\
        -d '{
            "bam": "${bam}",
            "annotation": "${annotation}",
            "outdir": "${outdir}",
            "prefix": "${prefix}",
            "strandedness": "${strandedness}",
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
    TRANSCRIPT_GTF=\$(echo "\$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['transcript_gtf'])")
    ABUNDANCE=\$(echo "\$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['abundance'])")
    COVERAGE=\$(echo "\$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('coverage_gtf') or '')")
    BALLGOWN=\$(echo "\$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ballgown') or '')")

    ln -s "\$TRANSCRIPT_GTF" "${prefix}.transcripts.gtf"
    ln -s "\$ABUNDANCE"      "${prefix}.gene.abundance.txt"
    [ -n "\$COVERAGE" ]  && ln -s "\$COVERAGE"  "${prefix}.coverage.gtf"  || true
    [ -n "\$BALLGOWN" ]  && ln -s "\$BALLGOWN"  "${prefix}.ballgown"      || true
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch ${prefix}.transcripts.gtf
    touch ${prefix}.gene.abundance.txt
    touch ${prefix}.coverage.gtf
    touch ${prefix}.ballgown
    """
}