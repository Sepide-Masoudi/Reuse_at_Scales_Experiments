process SUBREAD_FEATURECOUNTS {
    tag "${meta.id}"
    label 'process_medium'
    container 'biocontainers/subread:2.0.6--he4a0461_2'

    input:
    tuple val(meta), path(bams), path(annotation)

    output:
    tuple val(meta), path("*featureCounts.tsv"),         emit: counts
    tuple val(meta), path("*featureCounts.tsv.summary"), emit: summary
    tuple val("${task.process}"), val('subread'), eval("echo 2.0.6"), emit: versions_subread, topic: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args         = task.ext.args ?: ''
    def prefix       = task.ext.prefix ?: "${meta.id}"
    def paired_end   = meta.single_end ? false : true
    def strandedness = meta.strandedness == 'forward' ? 1 : meta.strandedness == 'reverse' ? 2 : 0
    def bam_list     = bams instanceof List ? bams.collect { "\$(pwd)/" + it.toString() } : ["\$(pwd)/" + bams.toString()]
    def outdir       = "\$(pwd)/"
    """
    cat > request.json << REQEOF
{
  "args": "${args}",
  "bams": ${groovy.json.JsonOutput.toJson(bam_list)},
  "annotation": "\$(pwd)/${annotation}",
  "outdir": "${outdir}",
  "prefix": "${prefix}",
  "paired_end": ${paired_end},
  "strandedness": ${strandedness},
  "cpus": ${task.cpus}
}
REQEOF
    wget -q -O- --post-file=request.json --header="Content-Type: application/json" http://featurecounts-service.nextflow.svc.cluster.local:8080/run \\
        \
        
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch ${prefix}.featureCounts.tsv
    touch ${prefix}.featureCounts.tsv.summary
    """
}
