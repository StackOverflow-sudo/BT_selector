#!/usr/bin/env bash
set -euo pipefail

cd /home/theshy/projects/mycode/kios_baseline

GENERATOR="${GENERATOR:-openai}"
MODEL="${OPENAI_MODEL:-gpt-5.4-mini}"

OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}" \
MKL_NUM_THREADS="${MKL_NUM_THREADS:-4}" \
python3 experiments/gpt_candidate_demo/run_single_vs_multi_gpt_baseline.py \
  --generator "$GENERATOR" \
  --model "$MODEL" \
  --case-count 10 \
  --repeats 3 \
  --multi-candidate-count 4 \
  "$@"
