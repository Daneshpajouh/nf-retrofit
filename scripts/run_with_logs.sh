#!/usr/bin/env bash
# Run a Nextflow pipeline with a manifest before, trace and logs during, a summary after.
# Usage: scripts/run_with_logs.sh <run_dir> <pipeline_dir> [nextflow run args...]
# The pipeline's output directory must be passed as --outdir <run_dir>/results (or set
# OUTDIR_PARAM to the parameter name the pipeline uses).
set -euo pipefail

run_dir=$1; shift
pipeline=$1; shift
here=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$run_dir"
run_dir=$(cd "$run_dir" && pwd)
pipeline=$(cd "$pipeline" && pwd)
export PYTHONPATH="$here/src${PYTHONPATH:+:$PYTHONPATH}"
outdir_param=${OUTDIR_PARAM:-outdir}

# every argument that names files (directly or as a glob) is hashed in the manifest
inputs=()
for arg in "$@"; do
    [[ "$arg" == -* ]] || inputs+=("$arg")
done

python3 -m nf_legacy_testkit manifest --out "$run_dir/manifest.json" \
    --pipeline-dir "$pipeline" --container "${PIPELINE_CONTAINER:-from the pipeline config}" \
    --param "args=$*" ${inputs[@]+"${inputs[@]}"}

set +e
nextflow -log "$run_dir/nextflow.log" run "$pipeline" \
    -work-dir "$run_dir/work" \
    -with-trace "$run_dir/trace.tsv" \
    -with-report "$run_dir/report.html" \
    -with-timeline "$run_dir/timeline.html" \
    "--$outdir_param" "$run_dir/results" "$@" 2>&1 | tee "$run_dir/console.txt"
status=${PIPESTATUS[0]}
set -e

python3 -m nf_legacy_testkit summarise --trace "$run_dir/trace.tsv" --outdir "$run_dir/results" \
    --exit-code "$status" --manifest "$run_dir/manifest.json" --out "$run_dir/summary.json"
