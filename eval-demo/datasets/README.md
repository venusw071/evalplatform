# Versioned Eval Datasets

Put datasets that should run in GitHub Actions in this folder.

Recommended format: JSONL, one example per line.

```json
{"id":"example-1","input":"User request","expected":"Reference answer","tags":"release,completeness"}
```

Supported row fields:

- Prompt: `input`, `prompt`, or `question`
- Reference: `expected`, `reference`, `ideal`, or `answer`
- Optional model output: `output`, `response`, `model_output`, or `actual`
- Optional labels: `tags`

When you push a new or changed dataset file under `eval-demo/datasets/`,
the `Completeness Eval` GitHub Action runs automatically.

For private or large datasets, keep only small redacted regression sets here and
store raw production logs in a data warehouse or object store.
