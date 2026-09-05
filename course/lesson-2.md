--- LESSON 2 ---

# Lesson 2: Automated repair loop — parse → validate → repair → revalidate

## What you will build

By the end of this lesson you'll have extended the validator from Lesson 1 into a small, deterministic repair pipeline. The pipeline accepts a model response (or a model-stub output), attempts to parse and validate it, and when validation fails it constructs a concise repair prompt, sends it back to the (stubbed) model, and retries parse→validate. The retry loop stops when a schema-valid object is returned or the retry budget is exhausted. The final artifact is validator_pipeline.py (which imports and reuses functions from validator_v1.py), exposing run_parse_validate_repair(input_text_or_prompt, schema, max_attempts) that returns a schema-valid Python object or a clear repair-failed summary.

## Checkpoints

1. Build a make_repair_prompt(original_text, formatted_errors, schema_snippet) function that produces a concise instruction asking the model to return only JSON matching the schema and to fix the specific errors.
2. Implement repair_once(prompt_text, schema) that calls send_to_model(prompt_text) — parses and validates the returned text — and reports whether it succeeded or what failed.
3. Implement run_repair_loop(original_text, schema, max_attempts=3) that cycles through repair attempts, detects repeated identical responses, logs each attempt, and stops on success or exhaustion.
4. Expose run_parse_validate_repair(input_text_or_prompt, schema, max_attempts) that returns (obj, None) on success or (None, failure_summary) on failure.

Note: This lesson reuses parse_model_response, validate_against_schema, and format_validation_errors from validator_v1.py. We assume validator_v1.py is in the same directory and contains:
- parse_model_response(text)
- validate_against_schema(obj, schema)
- format_validation_errors(errors)
- send_to_model(prompt) — a stub that returns canned responses sequentially (no real API calls).
- SAMPLE_RESPONSES and SCHEMA constants for demo usage (use the exact names SAMPLE_RESPONSES and SCHEMA).

## Section 1: Turning validation errors into repair instructions

When an object fails schema validation, the model doesn't benefit from a long verbose error dump — it needs a short, targeted instruction telling it what to fix and to return only JSON. The make_repair_prompt function converts formatted error messages into a compact repair request. A good prompt contains three elements: (1) a short list of the validation errors (one-line-per-error), (2) the original response so the model can see what to change, and (3) an explicit instruction to "Return only valid JSON that matches this schema" plus a minimal schema snippet or an example of correct JSON. Keep the prompt under a few sentences to reduce the model guessing.

Example of a concise repair prompt:

Please fix the JSON below so it matches the schema. Errors:
- items[0]: expected string but got 123
- missing required property: title

Original response:
{"title": "Example", "items": [123, "b"]}

Return only JSON matching this schema:
{"type":"object","properties":{"title":{"type":"string"},"items":{"type":"array","items":{"type":"string"}}},"required":["title","items"]}

Return only the fixed JSON — no prose.

Note the last line: "Return only the fixed JSON — no prose." That enforces a constrained output style that simplifies parsing and reduces the need for heuristics. For offline testing, our send_to_model stub can return a corrected JSON string when it sees the string "Return only JSON", simulating a cooperative model. The prompt must be machine-readable and short — it's consumed by our stub in the build-along.

Always include the minimal schema snippet or one small, concrete example of the correct shape. The schema snippet helps the model prefer types (e.g., arrays of strings) over guessing. Avoid including the entire large schema if you can extract the relevant properties; brevity improves reliability.

## Section 2: Implementing a limited repair loop

A repair loop wraps parse and validation into a retryable workflow. The loop's job is straightforward: try the original response first; if it fails, construct the repair prompt and call repair_once(prompt_text, schema). Repeat until success or until we've hit max_attempts. Each iteration should log what happened: parsed? yes/no; validation status; and the concise error summary. Logging makes it easy to debug automated runs.

Important behaviors for the loop:
- First attempt should validate the original_text without sending a repair prompt (this avoids unnecessary model calls).
- On failure, build a repair prompt using make_repair_prompt(original_text, formatted_errors, schema_snippet).
- Call repair_once(prompt_text, schema). If repair_once returns a schema-valid object, return it.
- Detect repeated identical model outputs across attempts: if the stub/model returns the exact same text twice in a row, assume it's stuck and abort early.
- Respect a max_attempts limit. Typical default: 3 attempts (original + 2 repairs) to keep budgets manageable.

A simple iteration log line might look like:
Attempt 2: INVALID – items[0] expected string but got 123

When success occurs:
Attempt 3: Parsed OK and VALID — returning object: {'title': 'Fixed', 'items': ['a','b']}

For deterministic offline behavior, the send_to_model stub should be deterministic: either iterate through a list of canned responses on each call, or check for keywords in the prompt and return a fixed "repaired" JSON. The loop logic must not depend on any external timing or network, so it runs reliably in tests.

Important: throughout this lesson the repair_once signature is repair_once(prompt_text, schema) — be consistent when you implement and call it.

## Section 3: Safety, logging, and stopping conditions

Retries can easily lead to infinite loops if not properly bounded. Use these safety measures:
- max_attempts: an explicit numeric limit ensures termination.
- identical-response detection: store the last raw model text and break if the new raw text equals the previous one.
- parse failure handling: if parse_model_response fails (e.g., JSONDecodeError) on a repaired attempt, count that as a failed attempt and continue; don't crash the loop.
- logging per attempt: print Attempt i: parsed? <True/False>; validation: <VALID/INVALID> plus concise errors. These logs are the main observability surface to understand why repairs fail.
- final failure summary: after exhaustion, produce a clear summary containing the number of attempts, the last raw response, and the last formatted validation errors.

Example stopping policy:
- max_attempts = 3
- If after attempt 3 the object is still invalid, return (None, "Repair failed after 3 attempts: last errors: ...")
- If the same raw response occurs twice (e.g., repeated repeated bad output), abort early as "stuck".

Keep logs compact but informative. In non-toy deployments you might write logs to a file or structured logging system, but for this course, terminal prints suffice.

## Section 4: Returning only validated data

Consumers of the pipeline must not receive unvalidated or partially fixed data. The public function run_parse_validate_repair(input_text_or_prompt, schema, max_attempts=3) must guarantee either:
- It returns (obj, None) where obj matches the provided schema, or
- It returns (None, failure_summary) where failure_summary is a concise string explaining why repair failed.

Design choices:
- Use tuples (obj, None) and (None, failure_string) to keep the API simple and explicit.
- Don't raise exceptions for routine reparable failures; return structured failure so callers can programmatically decide (retry externally, log, human-in-the-loop).
- Reserve exceptions for truly unexpected runtime errors (I/O, unexpected exceptions), not for validation failures.

Example signature:
def run_parse_validate_repair(input_text_or_prompt: str, schema: dict, max_attempts: int = 3) -> (dict | None, str | None):

The function must:
1. Try parse_model_response on input_text_or_prompt.
2. If parsed and valid: return (obj, None).
3. Collect formatted errors and attempt repairs using the loop described earlier.
4. On success return (obj, None). On exhaustion return (None, "Repair failed after X attempts: last errors: ...").

This invariant — callers either get schema-conforming data or a clear failure — makes downstream code simpler and safer: you don't need to revalidate later.

## Build-Along

### Goal

Extend the Lesson 1 artifact (validator_v1.py) to implement a repair loop and a final wrapper run_parse_validate_repair that returns either a schema-valid object or a clear failure summary. You will create validator_pipeline.py that imports from validator_v1.py and implements:
- make_repair_prompt
- repair_once
- run_repair_loop
- run_parse_validate_repair
A small demo in validator_pipeline.py will exercise one failing-first-then-success sequence using the existing send_to_model stub.

### Starting point

You should have validator_v1.py in the current directory (created in Lesson 1). It must contain:
- parse_model_response(text) -> (obj or None, error_message or None)
- validate_against_schema(obj, schema) -> (True/False, list_of_errors)
- format_validation_errors(errors) -> list_of_short_messages
- send_to_model(prompt) -> returns samples from a predefined list sequentially (no real API calls)
- SAMPLE_RESPONSES and SCHEMA constants for demo usage

If you don't have it, create or reuse the Lesson 1 artifact before proceeding.

Open a terminal in the directory containing validator_v1.py.

### Step 1: Add a repair prompt template function

What you add
- Create a new file validator_pipeline.py and add an import line:
  from validator_v1 import parse_model_response, validate_against_schema, format_validation_errors, send_to_model, SAMPLE_RESPONSES, SCHEMA
- Implement make_repair_prompt(original_text, formatted_errors, schema_snippet) -> str

Why it matters
- This function produces the concise repair instruction the model (stub) will use to produce fixed JSON. A consistent prompt improves repair success and is what repair_once will send.

Exact code to add (in validator_pipeline.py, but add incrementally as described):
- Implement make_repair_prompt that:
  - Joins formatted_errors into lines
  - Includes the original_text (shortened if >1000 chars)
  - Appends "Return only JSON matching this schema:" and the schema_snippet
  - Ends with "Return only JSON — no explanatory text."

Exact command to run
- Save validator_pipeline.py and run:
  python -c "import validator_pipeline; print(validator_pipeline.make_repair_prompt('{\"title\":\"X\",\"items\":[123]}', ['items[0]: expected string but got 123','missing required property: title'], '{\"type\":\"object\",\"properties\":{\"title\":{\"type\":\"string\"},\"items\":{\"type\":\"array\",\"items\":{\"type\":\"string\"}}},\"required\":[\"title\",\"items\"]}') )"

Expected terminal output
- A single string printed (the prompt). Example (formatted here as one-line output from print):

Please fix the JSON below so it matches the schema. Errors:
- items[0]: expected string but got 123
- missing required property: title

Original response:
{"title":"X","items":[123]}

Return only JSON matching this schema:
{"type":"object","properties":{"title":{"type":"string"},"items":{"type":"array","items":{"type":"string"}}},"required":["title","items"]}

Return only the fixed JSON — no explanatory text.

Visible check
- You should see the error list, the original response, the schema snippet, and the explicit "Return only the fixed JSON — no explanatory text." line. If you see those pieces, Step 1 worked.

### Step 2: Implement a single-retry repair attempt function

What you add
- In validator_pipeline.py implement repair_once(prompt_text, schema) -> (obj_or_none, parsed_ok_bool, validation_ok_bool, formatted_errors, raw_response)
  - Call send_to_model(prompt_text) to get raw_response (stubbed).
  - Call parse_model_response(raw_response) to get obj or parse_error.
  - If parse failed, return (None, False, False, [parse_error], raw_response)
  - If parsed, call validate_against_schema(obj, schema) to get (valid, errors)
  - Format errors using format_validation_errors(errors) if any.
  - If valid, return (obj, True, True, [], raw_response)

Why it matters
- repair_once encapsulates a single roundtrip: sending a prompt and inspecting the returned text. The repair loop will call this repeatedly.

Note: the function signature must be repair_once(prompt_text, schema) — ensure you pass schema into the function and that callers (run_repair_loop) pass schema too.

Exact command to run
- Save validator_pipeline.py and run this small script to call the function:
  python -c "from validator_pipeline import repair_once; from validator_v1 import send_to_model; import json; from validator_v1 import SCHEMA; prompt='test prompt'; print(repair_once(prompt, SCHEMA))"

Expected terminal output
- A 5-tuple printed. For the typical stub that returns a canned repaired JSON for certain prompts you might see:

(None, False, False, ['JSONDecodeError: Expecting value: line 1 column 1 (char 0)'], 'Some malformed prose before JSON...')

or, if the stub returns valid JSON:

({'title':'Fixed','items':['a','b']}, True, True, [], '{"title":"Fixed","items":["a","b"]}')

Visible check
- If parse failed, you should see parsed_ok_bool False and a parse error message in formatted_errors.
- If parse succeeded and was valid, parsed_ok_bool True and validation_ok_bool True and first element is the object. Confirm the tuple reflects the parsed/validation outcome.

### Step 3: Implement the repair loop wrapper

What you add
- Add run_repair_loop(original_text, schema, max_attempts=3)
  - Attempt 1: Try parsing and validating original_text without calling repair prompt. Use parse_model_response and validate_against_schema.
  - If valid, print "Attempt 1: Parsed OK and VALID — returning object: ..." and return (obj, None).
  - If invalid, generate formatted_errors and schema_snippet (you can reuse the full schema dict serialized via json.dumps(schema) as schema_snippet; be sure to import json at the top of validator_pipeline.py).
  - For attempt in 2..max_attempts:
    - Build prompt = make_repair_prompt(last_raw_text, formatted_errors, schema_snippet)
    - Call repair_once(prompt, schema)
    - Log "Attempt i: parsed? <True/False>; validation: <VALID/INVALID> — errors: <...>"
    - If success: print success line and return (obj, None)
    - If the new raw_response equals the last_raw_text, print "Repeated identical response; aborting early." and break.
    - Update last_raw_text and formatted_errors and continue
  - After loop exhaustion, return (None, f"Repair failed after {attempts} attempts: last errors: {joined_errors}")

Why it matters
- This function puts the pieces together and enforces the retry budget and stopping conditions.

Exact command to run
- Save validator_pipeline.py and run:
  python -c "from validator_pipeline import run_repair_loop; from validator_v1 import SCHEMA, SAMPLE_RESPONSES; import json; print(run_repair_loop(SAMPLE_RESPONSES[1], SCHEMA, max_attempts=3))"

Note: we intentionally recommend running run_repair_loop with validator_v1.SAMPLE_RESPONSES[1] (the invalid sample) for the offline demo because the send_to_model stub in validator_v1.py is deterministic and cycles through canned responses. Using SAMPLE_RESPONSES[1] typically ensures the first repair call will receive the next canned response (often a repaired JSON) and produces the expected failing-first-then-success logs in this lesson. If you pass a different initial input, the canned-sequence alignment may differ and produce a different (but still correct) behavior.

Expected terminal output
- For a stub sequence that returns an invalid first response and a corrected response on second model call, you should see:

Attempt 1: INVALID – items[0] expected string but got 123
Attempt 2: Parsed OK and VALID — returning object: {'title':'Fixed','items':['a','b']}
({'title': 'Fixed', 'items': ['a','b']}, None)

If the stub cannot repair within the attempts, you'll see something like:

Attempt 1: INVALID – items[0] expected string but got 123
Attempt 2: INVALID – items[0] expected string but got 123
Repeated identical response; aborting early.
(None, 'Repair failed after 2 attempts: last errors: items[0] expected string but got 123')

Visible check
- Confirm the log lines for each attempt. Confirm that the function returns (obj, None) on success, or (None, failure_string) on failure.

### Step 4: Final wrapper and CLI/demo

What you add
- Implement run_parse_validate_repair(input_text_or_prompt, schema, max_attempts=3) that delegates to run_repair_loop and returns the same (obj, None) or (None, failure_summary).
- Add a small __main__ demo at the bottom of validator_pipeline.py that:
  - Imports SAMPLE_RESPONSES and SCHEMA from validator_v1
  - Calls run_parse_validate_repair on SAMPLE_RESPONSES[1] (the invalid sample) so the deterministic stub sequence demonstrates the failing-first-then-success case
  - Prints either "Final result: <obj>" or "Final failure: <summary>"

Why it matters
- This exposes the capstone pipeline function and provides a quick demo to validate the whole flow.

Exact command to run
- Run the demo:
  python validator_pipeline.py

Expected terminal output (for the simulated failing-first-then-success sequence):
Attempt 1: INVALID – items[0] expected string but got 123
Attempt 2: Parsed OK and VALID — returning object: {'title': 'Fixed', 'items': ['a','b']}
Final result: {'title': 'Fixed', 'items': ['a','b']}

Or, if repair fails:
Attempt 1: INVALID – items[0] expected string but got 123
Attempt 2: INVALID – items[0] expected string but got 123
Repeated identical response; aborting early.
Final failure: Repair failed after 2 attempts: last errors: items[0] expected string but got 123

Visible check
- The final line must clearly state "Final result: <object>" or "Final failure: <summary>". That confirms the pipeline either returned schema-validated data or a clear failure.

### Final Check

Command to run:
python validator_pipeline.py

Note: for the deterministic offline demo we recommend running the pipeline using the provided SAMPLE_RESPONSES and SCHEMA constants from validator_v1.py:

python -c "from validator_pipeline import run_parse_validate_repair; from validator_v1 import SAMPLE_RESPONSES, SCHEMA; print(run_parse_validate_repair(SAMPLE_RESPONSES[1], SCHEMA))"

Expected successful terminal output (successful repair case):
Attempt 1: INVALID – items[0] expected string but got 123
Attempt 2: Parsed OK and VALID — returning object: {'title': 'Fixed', 'items': ['a','b']}
Final result: {'title': 'Fixed', 'items': ['a','b']}

If your send_to_model stub doesn't produce a repaired JSON on the second call, you'll see the failure case output above; that indicates the loop behaved correctly but the stub couldn't fix the response. The recommended SAMPLE_RESPONSES[1] input aligns with the stub's canned sequence in the Lesson 1 artifact to demonstrate the intended repaired outcome.

### Artifact

You now have validator_pipeline.py (which imports and reuses parse_model_response, validate_against_schema, format_validation_errors, and send_to_model from validator_v1.py) that implements:
- make_repair_prompt
- repair_once
- run_repair_loop
- run_parse_validate_repair
- A CLI/demo main that runs a sample repair sequence using the stub.

(validator_v1.py remains unchanged and provides the parsing/validation primitives and the send_to_model stub, plus SAMPLE_RESPONSES and SCHEMA constants used in the demo.)

### Next Lesson

This artifact is the completed capstone: it performs parse → validate → repair → revalidate and returns only schema-valid data (or a clear failure). If you continue beyond this course, you can:
- Swap send_to_model to call a real LLM API (replace the stub).
- Add structured logging and metrics.
- Expand schema complexity or convert the pipeline function into an asynchronous service.

Prerequisite note: Lesson 2 relied only on the functions built in Lesson 1:
- parse_model_response for parsing,
- validate_against_schema for checking schema compliance,
- format_validation_errors for making concise error lists,
- the send_to_model stub for deterministic offline testing.

These were reused directly; no new parsing or validation libraries were introduced.

--- END LESSON 2 ---