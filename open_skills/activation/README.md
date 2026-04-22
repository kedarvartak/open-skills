# Activation

The activation feature decides which skills apply to a user task.

It contains:

- `engine.py`: host-neutral scoring, threshold filtering, host filtering, ambiguity detection, and explainable match output.

The activation engine uses skill names, descriptions, triggers, capabilities, permissions, and instruction headings. Host adapters should reuse this feature instead of implementing separate matching behavior.
