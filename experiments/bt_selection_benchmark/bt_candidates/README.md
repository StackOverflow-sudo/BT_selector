# Candidate BT Library

This directory will contain behavior-tree candidates for each benchmark task.

Planned structure:

```text
bt_candidates/
  place_block3_on_block5/
    manifest.json
    correct_bt.json
    missing_precondition_bt.json
    wrong_object_bt.json
    wrong_support_bt.json
    redundant_bt.json
    unsafe_or_invalid_bt.json
```

Candidate categories are defined in `../experiment_protocol.md`.
