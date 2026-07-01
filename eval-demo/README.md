# EvalOps Demo

A dependency-free local product demo for an evaluation platform inspired by the system design chart.

## Run

```bash
python3 backend/server.py
```

Open:

```text
http://127.0.0.1:8000
```

## What It Demos

- Dataset registry for release evals, custom evals, and product-log samples.
- Dataset search, custom dataset tags, tag filtering, row deletion, and optional column clearing.
- CSV, JSON, and JSONL dataset upload from the UI.
- Eval run creation across dataset, model, prompt version, and run type.
- Mock or OpenAI-backed target model calls that store outputs, traces, latency, pass rate, baseline delta, and scorer rationales.
- Working LLM-as-Judge flow with five editable scorers, judge model/checkpoint selection, no-key local judges, OpenAI execution, saved judge scores, and judge-run editing/deletion.
- Playground for testing local no-key or OpenAI checkpoints with a system prompt and user input.
- Dashboard with recent run/model selection, focused run drilldown, score trends, and regression signals.
- Run drilldown with example-level expected output, model output, tags, and scorer results.
- Eval-run deletion and judge-run deletion for demo data management.

## Architecture

```text
Product logs / custom datasets
  -> PII scrubbed and tagged datasets
  -> Eval request
  -> Eval runner
  -> Deterministic and LLM-as-judge scorers
  -> Results, reporting, monitoring
```

The backend is a small Python HTTP server with SQLite persistence. The frontend is plain HTML/CSS/JavaScript served by the backend so the demo has no install step.

## OpenAI Runs

Open **New eval run**, set **Provider** to **OpenAI Responses API**, choose a target model or enter a custom fine-tuned checkpoint ID, and paste an API key into the password field. The key is used only for that request and is not stored in SQLite.

If no key is supplied for an OpenAI target run, the app falls back to local mode and records that in the example trace.

Use **Connect OpenAI and load models** to validate the key and populate the model dropdown from the OpenAI models endpoint.

## No-Key Local Models

Set **Provider** to **Local no-key models** to run the demo without OpenAI credentials. These backend models are deterministic local simulators:

- `local-helpful`
- `local-fast`
- `local-buggy`
- `local-json-strict`

They are useful for testing the eval UI, dataset upload, run storage, drilldowns, and LLM-as-Judge workflow setup without spending API calls.

## LLM-as-Judge

Open **Judge Lab** after creating at least one eval run.

1. Select the source eval run.
2. Choose a local no-key judge, OpenAI judge model, or custom judge checkpoint.
3. Select and edit the Safety, Factuality, Instruction Following, Completeness, and Style & Tone scorer prompts.
4. Paste an OpenAI API key only when using OpenAI judge models.
5. Run the judge on a small sample, such as 5 examples.

Judge scores, pass/fail, rationales, and average judge score are saved in SQLite and shown in the Judge Lab.

Click a saved judge run in the Judge summary list to view, edit, or delete it.

## Playground

Open **Playground** to test a model before creating an eval run.

1. Select Local no-key models or OpenAI Responses API.
2. Choose a model checkpoint.
3. Enter a system prompt and user input.
4. Generate and inspect the model output.

## Dataset Upload

Open **Upload dataset** and choose a `.csv`, `.json`, or `.jsonl` file.

Supported row fields:

```json
{
  "input": "User request or eval prompt",
  "expected": "Reference answer or rubric expectation",
  "tags": "safety,hard"
}
```

CSV files should use headers such as:

```text
input,expected,tags
Summarize this policy.,Two concise bullets.,"instruction-following,support"
```
