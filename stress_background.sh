#!/bin/bash
# stress_background.sh
# Background stress generator: N concurrent "users" continuously sending POST /run
# to a service, running UNTIL KILLED (no fixed duration). Used to apply sustained
# contention on the shared services WHILE a measured pipeline runs.
#
# Launch in background, kill when the measured pipeline finishes.
#
# Usage: ./stress_background.sh <SERVICE> <N_USERS> <RESULTS_CSV>
#   SERVICE     : featurecounts | stringtie
#   N_USERS     : number of concurrent background senders
#   RESULTS_CSV : where to log requests (for stress-side record)
#
# Writes its child PIDs to /tmp/stress_pids_<SERVICE>.txt so the caller can kill them.

set -uo pipefail

SERVICE="${1:?need service}"
N_USERS="${2:?need n_users}"
RESULTS_CSV="${3:?need results csv}"

if [[ "$SERVICE" == "featurecounts" ]]; then
  URL="http://10.233.5.152:8080/run"
elif [[ "$SERVICE" == "stringtie" ]]; then
  URL="http://10.233.39.91:8081/run"
else
  echo "ERROR: unknown service $SERVICE"; exit 1
fi

BAM="/workspace/loadtest_inputs/test.bam"
GTF="/workspace/loadtest_inputs/annotation.gtf"
OUTBASE="/workspace/loadtest_outputs"
RUN_TS=$(date +%Y%m%d_%H%M%S)
PIDFILE="/tmp/stress_pids_${SERVICE}.txt"
: > "$PIDFILE"

make_body() {
  local uid="$1"
  local outdir="${OUTBASE}/stress_${SERVICE}_${RUN_TS}"
  if [[ "$SERVICE" == "featurecounts" ]]; then
    printf '{"bams":["%s"],"annotation":"%s","outdir":"%s","prefix":"s%s","paired_end":true,"strandedness":0,"cpus":2}' \
      "$BAM" "$GTF" "$outdir" "$uid"
  else
    printf '{"bam":"%s","annotation":"%s","outdir":"%s","prefix":"s%s","strandedness":"unstranded","cpus":2}' \
      "$BAM" "$GTF" "$outdir" "$uid"
  fi
}

# One background user: loop forever until killed
user_loop() {
  local uid="$1"
  local body; body="$(make_body "$uid")"
  while true; do
    local start end lat code
    start=$(date +%s.%N)
    code=$(curl -s -o /dev/null -w '%{http_code}' -m 600 \
      -X POST "$URL" -H 'Content-Type: application/json' -d "$body" 2>/dev/null)
    end=$(date +%s.%N)
    lat=$(awk "BEGIN{printf \"%.4f\", $end - $start}")
    echo "${SERVICE},${N_USERS},${uid},${code},${lat},${start}" >> "$RESULTS_CSV"
  done
}

echo "  [stress] $SERVICE: launching $N_USERS background senders (until killed)"
for u in $(seq 1 "$N_USERS"); do
  user_loop "$u" &
  echo $! >> "$PIDFILE"
done

# This script stays alive holding the background loops; caller kills the process group.
wait