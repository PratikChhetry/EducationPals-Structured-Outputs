# Course Goal

Equip a developer to build a small Python pipeline that takes an LLM response, parses it as JSON, validates it against a schema, reports actionable validation errors, and—when the response is invalid—automatically repairs the response via a limited retry loop until a schema-valid result is returned (or retries are exhausted). The final capstone is a single Python function that accepts an LLM response (or a model-stub), performs parse → validate → repair → revalidate, and returns only schema-valid data.

# Lesson 1
## Purpose
Teach how to reliably parse LLM responses as JSON, validate the parsed data against a JSON schema, and produce clear, actionable validation error messages the code and a human can use.

## Checkpoints
1. Given a string that is purported JSON, parse it into Python objects or catch and report a JSONDecodeError with a clear message.
2. Given a Python object and a JSON Schema, run schema validation and programmatically detect whether the object matches the schema.
3. Given a validation failure, produce a concise, developer-friendly error summary that identifies the failing keys/paths and the expected types/constraints.

## Sections

Section 1
Title: Why "return JSON" from an LLM is not enough
Main idea: LLMs frequently produce prose, malformed JSON, or JSON structurally different from the schema you expect; understanding these failure modes prevents brittle pipelines.
Why it is needed: Sets the problem context and motivates the need for parsing and validation instead of blind trust.
Estimated learner time: 5 minutes

Section 2
Title: Safely parsing JSON in Python
Main idea: Use json.loads and handle json.JSONDecodeError; sanitize simple issues like surrounding prose by extracting the first JSON object.
Why it is needed: You must reliably convert the model string into a dict/list before validating.
Estimated learner time: 12 minutes

Section 3
Title: Defining schemas and validating with jsonschema
Main idea: Introduce JSON Schema basics (types, required, properties) and use the jsonschema library to validate Python objects.
Why it is needed: Distinguishes "valid JSON" from "JSON that matches the expected schema"; provides a programmatic validator that reports structured errors.
Estimated learner time: 12 minutes

Section 4
Title: Formatting and surfacing validation errors
Main idea: Map jsonschema ValidationError instances into concise, actionable messages (path to the bad field, the failing rule, expected vs actual).
Why it is needed: Useful error output is the input for automated repair instructions and helps developers debug.
Estimated learner time: 11 minutes

## Build-Along 1
Starting point
- A minimal Python script with:
  - from json import loads, JSONDecodeError
  - an example list of three sample LLM response strings:
    1. well-formed JSON matching the schema
    2. well-formed JSON with schema mismatch (wrong type/missing field)
    3. malformed JSON (extra prose or trailing commas)
  - a JSON Schema dict describing a simple object (e.g., {"type":"object","properties":{"title":{"type":"string"},"items":{"type":"array","items":{"type":"string"}}},"required":["title","items"]})
  - a stub function send_to_model(prompt) that simply returns elements from the sample list (no real API calls).

Step-by-step progression
1. Add JSON parsing with try/except:
   - Implement a function parse_model_response(text) -> (obj or None, error_message or None).
   - If json.loads(text) succeeds, return object and None.
   - If JSONDecodeError occurs, return None and an error string including the exception text.
2. Add a small heuristic to extract JSON from prose:
   - If parse fails, attempt to locate the first '{' or '[' and parse from that substring; if that works, return it and note the extraction.
3. Integrate jsonschema validation:
   - pip-install note for jsonschema (one-liner).
   - Implement validate_against_schema(obj, schema) -> (True/False, list_of_errors)
   - Call jsonschema.validate in try/except or use jsonschema.Draft7Validator to get iterator of ValidationError objects.
4. Build a human-readable error formatter:
   - For each ValidationError, produce a short message: "path: expected <rule> but got <value/type>"
   - For missing required properties, list property names.
5. Glue the flow:
   - For each sample response, run parse_model_response → if obj then validate_against_schema → print either "VALID" plus the object or "INVALID" plus formatted errors and original text.

Visible checks (what appears in the terminal) after each major step
1. After successful parse step for the first sample: "Parsed OK: {'title': 'Example', 'items': ['a','b']}"
2. After heuristic extraction step (malformed example): "Extracted JSON from prose; Parsed OK: {...}"
3. After validation of schema-mismatched sample: "Validation FAILED: path 'items[0]': expected string but got 123; missing required property 'title'"
4. For the correct sample: "VALID: object matches schema" and print compact representation.

Final artifact
- A small Python module validator_v1.py containing:
  - parse_model_response(text)
  - validate_against_schema(obj, schema)
  - format_validation_errors(errors)
  - examples and a main loop printing parse/validation results for the three sample responses

How that artifact is used by the next lesson
- validator_v1.py will serve as the validator core that Lesson 2 reuses and extends by constructing repair prompts from formatted errors and implementing an automated repair+retry loop that calls the same parse and validate functions.

Estimated Build-Along 1 time: 18 minutes (keeps under 20)

# Lesson 2
## Purpose
Extend the validator from Lesson 1 into a repair loop: when a parsed response fails schema validation, use the formatted validation errors to create a concise repair request, resend to the model (via the same stub), re-parse and re-validate up to a small retry limit, and finally return only a schema-valid object or an informative failure.

## Checkpoints
1. Given validation errors, construct a concise repair prompt that instructs the model to output corrected JSON.
2. Implement a limited repair loop that resends the repair prompt, re-parses, and re-validates until the response passes or the retry budget is exhausted.
3. Return only schema-valid data (or a clear "could not repair" error) from the pipeline function.

## Sections

Section 1
Title: Turning validation errors into repair instructions
Main idea: How to convert ValidationError objects into a short, actionable instruction that asks the model to fix only the fields that failed and to return only JSON matching the schema.
Why it is needed: The repair prompt is the mechanism for getting a corrected response from the LLM; well-structured instructions increase chance of success and reduce repeated failures.
Estimated learner time: 10 minutes

Section 2
Title: Implementing a limited repair loop
Main idea: Build a retry loop (max_attempts N), each iteration: format repair prompt, send to send_to_model(prompt), parse, validate; stop on success.
Why it is needed: Automated repair prevents blind retries, enforces a retry budget, and produces deterministic handling of invalid outputs.
Estimated learner time: 12 minutes

Section 3
Title: Safety, logging, and stopping conditions
Main idea: Decide stop conditions (max retries, detect repeated identical responses, backoff or amendment), log each attempt and error for observability.
Why it is needed: Avoid infinite loops and provide useful debug info when automated repair fails.
Estimated learner time: 8 minutes

Section 4
Title: Returning only validated data
Main idea: Wrap the pipeline in a single function run_parse_validate_repair(response_or_prompt, schema, max_attempts) that returns either a Python object guaranteed to match schema or raises/returns an explicit repair-failed exception/structure.
Why it is needed: Consumers of this pipeline should receive only valid, schema-conforming data or a clear error; this enforces invariants for downstream code.
Estimated learner time: 5 minutes

## Build-Along 2
Starting artifact from Lesson 1
- validator_v1.py containing: parse_model_response, validate_against_schema, format_validation_errors, and the sample send_to_model stub (which can produce alternate canned responses to simulate repairs).

Step-by-step progression
1. Add a repair prompt template function:
   - Implement make_repair_prompt(original_text, formatted_errors, schema_snippet) -> str
   - Template must: (a) show the validation errors, (b) show the original response, (c) instruct the model to "Return only JSON that matches this schema" and optionally include a small schema snippet or an example of correct JSON.
   - Visible check: printing the prompt shows a concise instruction including the error list and "Return only JSON".
2. Implement a single-retry repair attempt function:
   - repair_once(prompt_text) calls send_to_model(prompt_text), then runs parse_model_response and validate_against_schema.
   - If parse fails, return parse error; if validation fails, return formatted validation errors and the raw response.
   - Visible check: for a simulated bad initial response, calling repair_once prints (or returns) "Attempt 1: parsed? False; validation errors: …" or "Attempt 1: success".
3. Implement the repair loop wrapper:
   - run_repair_loop(original_text, schema, max_attempts=3)
   - On each iteration:
     - If iteration==1, you may first try to parse/validate original_text (reuse validator_v1 behavior).
     - If invalid, call make_repair_prompt and repair_once.
     - If the repaired response is schema-valid, return the object immediately.
     - Detect identical model output across iterations and break early if stuck.
   - Add logging lines: "Attempt i: result = VALID/INVALID (errors...)"
   - Visible checks: For a sample sequence (use the stub to return first an invalid response, then a corrected response on attempt 2), the terminal should show:
     - "Attempt 1: INVALID – items[0] expected string but got 123"
     - "Attempt 2: Parsed OK and VALID — returning object: {...}"
4. Add final wrapper function and return semantics:
   - Implement run_parse_validate_repair(input_text_or_prompt, schema, max_attempts=3) that returns (obj, None) on success or (None, failure_summary) on exhaustions.
   - Visible checks: When using a sample case where repair cannot succeed within max_attempts, the terminal prints "Repair failed after 3 attempts: last errors: …" and the function returns a clear failure object.

Final capstone artifact
- validator_pipeline.py (or extended validator_v2.py) that contains:
  - parse_model_response
  - validate_against_schema
  - format_validation_errors
  - make_repair_prompt
  - repair_once
  - run_repair_loop / run_parse_validate_repair
  - A short CLI/demo main that uses the same send_to_model stub to simulate a failing-first-then-repaired response sequence and prints the final returned object or a repair-failed summary.

Estimated Build-Along 2 time: 17 minutes (keeps under 20)

# Prerequisite Check
Explain why Lesson 2 only depends on concepts introduced in Lesson 1

- Parsing JSON: Lesson 2 reuses parse_model_response from Lesson 1 to convert model text to Python objects. No new parsing technique is introduced.
- Schema validation: Lesson 2 uses validate_against_schema from Lesson 1 to determine success/failure of attempts and to collect ValidationError instances.
- Formatting validation errors: Lesson 1's format_validation_errors produces the concise messages that Lesson 2 consumes to build repair prompts. Lesson 2 does not invent a new error representation.
- send_to_model stub: The stub introduced in Lesson 1 is reused; Lesson 2 calls it in a loop but does not require introducing any new API concepts.
- Control flow and retries: No new libraries or validation techniques are introduced in Lesson 2; the retry loop is an application-level orchestration that composes the functions and messages the learner already implemented in Lesson 1.

Therefore every concrete operation in Lesson 2 (construct prompt, call model stub, parse, validate, format errors, decide to retry/stop) directly reuses functions or patterns introduced and exercised in Lesson 1.

# Scope Cuts
Concepts intentionally excluded because they are not necessary for the capstone or 90-minute scope
- Full LLM API integration: How to call OpenAI/Azure/Anthropic APIs, authentication, streaming responses. (We use a send_to_model stub and note where to plug a real API.)
- Advanced schema systems: pydantic models, typed dataclasses, or schema generation from code; only JSON Schema and basic usage is taught.
- Complex schema features: deep conditional schemas (if/then/else), custom validators, or complex formats beyond basic type/required/properties.
- Automatic inference of schema from examples or schema learning techniques.
- Sophisticated retry strategies: exponential backoff with jitter, rate-limiting, or distributed retry coordination.
- Human-in-the-loop repair workflows: asking a human to fix the JSON; this course covers automated repair only.
- Production concerns like secure logging of model outputs, encryption, or full observability stacks.
- UI or interactive notebook-specific tooling; the course is text/terminal-focused with small printed examples.
- Bulk batch processing scalability and asynchronous streaming validation.

