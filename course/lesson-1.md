--- LESSON 1 (REVISED) ---

# Lesson 1: Reliable JSON parsing and schema validation for LLM responses

## What you will build

By the end of this lesson you'll have a small Python module, validator_v1.py, that reads three example LLM response strings, reliably parses them into Python objects (with a small heuristic to extract JSON from surrounding prose), validates the parsed objects against a JSON Schema using the jsonschema library, and prints concise, developer-friendly validation error summaries when validation fails.

This module exposes:
- parse_model_response(text) -> (obj or None, error_message or None)
- validate_against_schema(obj, schema) -> (is_valid: bool, list_of_validation_errors)
- format_validation_errors(errors) -> list[str]
- a small main loop that demonstrates parsing/validation for three sample LLM responses and uses a send_to_model stub (no network calls)

## Checkpoints

1. Given a string that is purported JSON, parse it into Python objects or catch and report a JSONDecodeError with a clear message.
2. Given a Python object and a JSON Schema, run schema validation and programmatically detect whether the object matches the schema.
3. Given a validation failure, produce a concise, developer-friendly error summary that identifies the failing keys/paths and the expected types/constraints.

## Section 1: Why "return JSON" from an LLM is not enough

When you ask an LLM to "return JSON", three common failure modes break naive pipelines:

- Prose + JSON: The model often adds natural-language commentary before/after the JSON (e.g., "Here is the answer: {...}"). A strict json.loads call will fail unless you strip the prose.
- Malformed JSON: LLMs may produce trailing commas, unescaped quotes, or comments that are invalid JSON. These cause json.JSONDecodeError.
- Schema drift: Even syntactically valid JSON may not match your expected data model. Fields may be missing, types may differ (number instead of string), or arrays may contain the wrong element types.

Blindly trusting that a response is usable leads to brittle downstream code. You need three layered defenses:
1. Robust parsing that catches decode errors and extracts JSON from surrounding text.
2. Schema validation that distinguishes "valid JSON" from "valid, expected shape".
3. Clear, machine- and human-readable error reports so you can repair automatically or debug quickly.

This lesson focuses on layers 1 and 2 and on producing error reports that are actionable. The goal is pragmatic: build small utilities that turn a model response into either a validated Python object or a clear summary of what went wrong. That output will later be used to prompt the model to repair its output (Lesson 2), but for now we concentrate on parsing and validation hygiene so the rest of the pipeline can be reliable.

## Section 2: Safely parsing JSON in Python

Python's standard library json.loads is the canonical way to parse a JSON string to Python objects. It raises json.JSONDecodeError on invalid JSON. Basic pattern:

try:
    obj = json.loads(text)
except json.JSONDecodeError as e:
    # report e.msg / e.pos

Catching JSONDecodeError gives you the exception message and position, which are useful for diagnostics. However, many LLM responses embed valid JSON inside text. A pragmatic heuristic is to locate the first JSON opening character ('{' or '[') and the last closing character ('}' or ']'), extract that substring, and try json.loads again. This handles the common "prose wrapper" case:

text = "Note: {\"title\":\"A\",\"items\":[\"x\",\"y\"]} End."
start = text.find('{')  # or '['
end = text.rfind('}')   # or ']'
candidate = text[start:end+1]
json.loads(candidate)

This heuristic is intentionally simple: it assumes the model's JSON is contiguous and the opening/closing braces match somewhere in the response. It will not fix malformed JSON like trailing commas or unescaped quotes; these require more involved transformations or asking the model to repair (Lesson 2). For parsing, do this order:

1. Try json.loads(text) directly — best-case success.
2. If it fails, try extracting from the first opening brace/bracket to the last matching close and parse that substring, returning both the parsed object and a note that you extracted JSON.
3. If extraction fails, return the original JSONDecodeError message so callers can decide to repair or escalate.

Keep error messages concise and include the original exception text and any extraction note. That gives downstream code enough context to choose automatic repair or log an informative report.

## Section 3: Defining schemas and validating with jsonschema

JSON Schema lets you declare the shape and constraints you expect. For our capstone we only need a small subset: type, properties, required, and items for arrays. Example schema (used in the build-along):

schema = {
  "type": "object",
  "properties": {
    "title": {"type": "string"},
    "items": {"type": "array", "items": {"type": "string"}}
  },
  "required": ["title", "items"]
}

To validate in Python, use the jsonschema package. Install with:
pip install jsonschema

Two common patterns:

- jsonschema.validate(instance, schema) — raises a ValidationError on the first failure.
- Draft7Validator(schema).iter_errors(instance) — returns an iterator of ValidationError objects for all violations.

We prefer Draft7Validator.iter_errors because it gives all the problems, not just the first. A ValidationError object contains useful attributes:
- .message — human-readable message
- .validator — the rule that failed, e.g., "type" or "required"
- .validator_value — the schema value for that validator, e.g., "string" or ["title","items"]
- .instance — the actual value that failed
- .absolute_path — an object representing the path to the failing element (deque-like)

Example usage:

from jsonschema import Draft7Validator
validator = Draft7Validator(schema)
errors = list(validator.iter_errors(obj))
if errors:
    # handle

Collecting all error objects lets you summarize them into a compact developer-friendly format (next section). Using a programmatic validator is essential — without it you cannot reliably detect missing fields or type mismatches before downstream code runs.

## Section 4: Formatting and surfacing validation errors

A raw ValidationError is rich but not concise. For automated repair and human debugging you want short messages that identify:
- the JSON path to the problem (e.g., items[0], title)
- the failing rule (e.g., expected type string, missing required property)
- what was actually received (value or type)

Construct a small formatter that converts a ValidationError into a one-line summary. Key steps:
- Convert .absolute_path into a canonical path string:
  - If absolute_path is empty → use '<root>'
  - For lists: join segments, rendering ints as [idx] (e.g., items[0]). If the root itself is an array (first segment is an int), render as "[0]" or similar.
- Inspect error.validator:
  - If 'required': error.message usually contains which property is missing; include the succinct message.
  - If 'type': use error.validator_value to show expected type and error.instance (or its Python type) to show actual.
  - For other validators, fall back to error.message.

Concrete examples:
- Missing required property "title" → "path <root>: missing required property 'title'"
- items[0] has number 123 but expected string → "path items[0]: expected type 'string' but got number (123)"

Keep messages short and deterministic so they are useful for:
- printing to a developer console
- building a machine-readable "repair instruction" later (Lesson 2)

The formatter should return a list of these strings for all errors. That list is the essential bridge between validation and repair logic: the repair prompt will include these concise lines so the model knows exactly what to fix.

## Build-Along

### Goal

Implement a minimal validator module that:
- parses model responses (with extraction heuristic),
- validates parsed objects against a JSON Schema using jsonschema,
- formats validation errors into concise messages,
- and demonstrates behavior on three sample LLM responses.

This build-along is incremental and should take under 20 minutes.

### Starting point

Create a file named validator_v1.py containing the following minimal skeleton. This is your starting point:

```python
# validator_v1.py (starting point)
from json import loads, JSONDecodeError
from jsonschema import Draft7Validator

# Sample model response strings
SAMPLE_RESPONSES = [
    '{"title": "Example", "items": ["a", "b"]}',            # well-formed, matches schema
    '{"items": [123, "b"]}',                               # well-formed, schema mismatch (missing title, wrong type)
    'Intro text... {"title": "Prose", "items": ["x", "y"]} End.'  # prose + JSON
]

# JSON schema to validate against
SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "items": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["title", "items"]
}

# Stub model sender:
# - If the prompt contains the substring "Return only JSON" we deterministically
#   return a valid JSON response (SAMPLE_RESPONSES[0]) so offline demos are robust.
# - Otherwise we cycle through sample responses for demo variety.
def send_to_model(prompt: str) -> str:
    """
    In a real integration you would call an API. For this course we provide a
    deterministic stub: when asked to "Return only JSON" it returns a valid JSON
    sample; otherwise it cycles through SAMPLE_RESPONSES for demo purposes.
    """
    if "Return only JSON" in prompt:
        # Return a clean, valid JSON sample to simulate the model fixing its output.
        return SAMPLE_RESPONSES[0]
    if not hasattr(send_to_model, "_i"):
        send_to_model._i = 0
    res = SAMPLE_RESPONSES[send_to_model._i % len(SAMPLE_RESPONSES)]
    send_to_model._i += 1
    return res

def main():
    # placeholder: you will add functions and call them here
    for text in SAMPLE_RESPONSES:
        print("RAW RESPONSE:", text)

if __name__ == "__main__":
    main()
```

Save this file and run:
python validator_v1.py
Expected output: three "RAW RESPONSE:" lines showing the three sample strings.

---

### Step 1: Add basic JSON parsing with try/except

What you add
- Implement parse_model_response(text) that:
  - tries json.loads(text)
  - on success returns (obj, None)
  - on JSONDecodeError returns (None, f"JSONDecodeError: {str(e)}")

Why it matters
- This satisfies Checkpoint 1: reliably attempt to parse and return clear decode error messages that callers can act on.

Code to add to validator_v1.py (replace main placeholder or append before main):

```python
def parse_model_response(text):
    """
    Try to parse the full text as JSON.
    Returns (obj, None) on success or (None, error_message) on failure.
    """
    try:
        obj = loads(text)
        return obj, None
    except JSONDecodeError as e:
        return None, f"JSONDecodeError: {e.msg} at pos {e.pos}"
```

Command to run
python validator_v1.py

Expected terminal output
- The same three RAW RESPONSE lines (unchanged)
- No parsing output yet because main still only prints raw responses.

To check parsing interactively, add a small test call in main (temporary) and run:

Add inside main() after the RAW RESPONSE print:
```python
obj, err = parse_model_response(text)
if obj:
    print("Parsed OK:", obj)
else:
    print("Parse FAILED:", err)
```

Now run:
python validator_v1.py

Expected output (for the first sample):
Parsed OK: {'title': 'Example', 'items': ['a', 'b']}
For the second sample:
Parsed OK: {'items': [123, 'b']}
For the third sample (prose wrapper):
Parse FAILED: JSONDecodeError: Expecting property name enclosed in double quotes at pos <n>
(Exact pos will vary based on parsing attempt; the key is you see a JSONDecodeError message.)

Visible check 1 (from the course plan):
After successful parse step for the first sample: "Parsed OK: {'title': 'Example', 'items': ['a', 'b']}"

---

### Step 2: Add a simple heuristic to extract JSON from prose

What you add
- Update parse_model_response to, on JSONDecodeError, attempt to find the first '{' or '[' and the last matching '}' or ']' and try to loads that substring. If this secondary parse succeeds, return the parsed object and an extraction note in the error field (e.g., "extracted JSON from surrounding text").

Why it matters
- This handles the common case where the model wraps JSON with prose and lets pipelines recover without immediate repair.

Code change (replace parse_model_response with this full function):

```python
def parse_model_response(text):
    """
    Try to parse text as JSON. If that fails, attempt to extract the first JSON
    object/array from the text (a simple heuristic).
    Returns (obj, None) on success or (None, error_message) on failure.
    """
    try:
        obj = loads(text)
        return obj, None
    except JSONDecodeError as e:
        # Try to extract JSON from surrounding prose
        first_positions = [pos for pos in (text.find('{'), text.find('[')) if pos != -1]
        first_obj = min(first_positions) if first_positions else -1
        if first_obj != -1:
            # decide which closing bracket to use depending on opening
            if text[first_obj] == '{':
                last_close = text.rfind('}')
            else:
                last_close = text.rfind(']')
            if last_close != -1 and last_close > first_obj:
                candidate = text[first_obj:last_close+1]
                try:
                    obj = loads(candidate)
                    return obj, "extracted JSON from surrounding text"
                except JSONDecodeError:
                    pass
        return None, f"JSONDecodeError: {e.msg} at pos {e.pos}"
```

Command to run
python validator_v1.py

Expected terminal output (with the temporary test prints):
- First sample: Parsed OK: {'title': 'Example', 'items': ['a', 'b']}
- Second sample: Parsed OK: {'items': [123, 'b']}
- Third sample: Extracted JSON from surrounding text -> then Parsed OK: {'title': 'Prose', 'items': ['x', 'y']}

Visible check 2:
"Extracted JSON from prose; Parsed OK: {'title': 'Prose', 'items': ['x', 'y']}"

---

### Step 3: Integrate jsonschema validation

What you add
- pip install jsonschema if you don't already have it:
  pip install jsonschema

- Implement validate_against_schema(obj, schema) that returns (True, []) if no errors, or (False, [ValidationError objects]) using Draft7Validator.iter_errors.

Why it matters
- This lets you detect schema mismatches programmatically (Checkpoint 2).

Code to add to validator_v1.py:

```python
def validate_against_schema(obj, schema):
    """
    Returns (is_valid: bool, errors: list[ValidationError])
    """
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(obj))
    return (len(errors) == 0), errors
```

Command to run
python validator_v1.py

Expected terminal output (with main updated to run validation when parse succeeds):
- For the first sample:
  Parsed OK: {'title': 'Example', 'items': ['a', 'b']}
  VALID: object matches schema
- For the second sample:
  Parsed OK: {'items': [123, 'b']}
  INVALID: 2 validation errors
- For the third sample:
  Extracted JSON from surrounding text
  Parsed OK: {'title': 'Prose', 'items': ['x', 'y']}
  VALID: object matches schema

Visible check 3:
"Validation FAILED: path 'items[0]': expected string but got 123; missing required property 'title'"

(We haven't formatted the errors yet; the main output will currently show the number of errors.)

---

### Step 4: Build a human-readable error formatter

What you add
- Implement format_validation_errors(errors) that converts ValidationError objects to short strings like:
  "path items[0]: expected type 'string' but got number (123)"
  "path <root>: missing required property 'title'"

Why it matters
- This converts raw validator objects into concise messages that developers and repair prompts can consume (Checkpoint 3).

Code to add:

```python
def _path_to_string(path_iterable):
    """
    Convert an iterable of path segments into a canonical string.
    Examples:
      [] -> "<root>"
      ["items", 0] -> "items[0]"
      [0] -> "[0]"   # root array element
    """
    parts = []
    for p in path_iterable:
        if isinstance(p, int):
            if not parts:
                # root is an array index
                parts.append(f"[{p}]")
            else:
                parts[-1] = f"{parts[-1]}[{p}]"
        else:
            parts.append(str(p))
    return ".".join(parts) if parts else "<root>"

def format_validation_errors(errors):
    msgs = []
    for err in errors:
        path = _path_to_string(list(err.absolute_path))
        if err.validator == "required":
            # err.message usually contains which property is missing; include the message
            msgs.append(f"path {path}: {err.message}")
        elif err.validator == "type":
            expected = err.validator_value
            actual = err.instance
            actual_type = type(actual).__name__
            msgs.append(f"path {path}: expected type '{expected}' but got {actual_type} ({actual})")
        else:
            msgs.append(f"path {path}: {err.message}")
    return msgs
```

Notes:
- The _path_to_string implementation avoids an IndexError if the first path segment is an int (root array case) by handling that explicitly.
- For required-property errors we keep the concise err.message rather than brittle string splits; for this course that is acceptable and clear.

Update your main to call format_validation_errors when validation fails and print each formatted line.

Command to run
python validator_v1.py

Expected terminal output for the second sample (schema mismatch):
Parsed OK: {'items': [123, 'b']}
INVALID:
path items[0]: expected type 'string' but got int (123)
path <root>: 'title' is a required property

Visible check 4:
"Validation FAILED: path 'items[0]': expected string but got 123; missing required property 'title'"

(Your formatted lines will reflect the messages above. The important part is that you see the path, the expected rule, and the actual value/type.)

---

### Step 5: Glue the flow and produce final output for sample responses

What you add
- Tie parse_model_response, validate_against_schema, and format_validation_errors into a single main loop that:
  - For each sample response:
    - attempts parse (noting extraction messages)
    - if parsed, runs validation
      - if valid: prints "VALID: object matches schema: <compact obj>"
      - if invalid: prints "INVALID:" and each formatted error and prints the original response for context

Why it matters
- This final glue demonstrates all three checkpoints working together and produces the artifact described by the course plan.

Add or update main() to:

```python
def main():
    for i, text in enumerate(SAMPLE_RESPONSES, 1):
        print("="*40)
        print(f"Sample {i} RAW RESPONSE: {text}")
        obj, perr = parse_model_response(text)
        if obj:
            if perr:
                print("Note:", perr)
            print("Parsed OK:", obj)
            valid, errors = validate_against_schema(obj, SCHEMA)
            if valid:
                print("VALID: object matches schema:", obj)
            else:
                print("INVALID:")
                for line in format_validation_errors(errors):
                    print(" -", line)
                print("Original text for context:", text)
        else:
            print("Parse FAILED:", perr)
```

Command to run
python validator_v1.py

Expected successful terminal output (compact):

========================================
Sample 1 RAW RESPONSE: {"title": "Example", "items": ["a", "b"]}
Parsed OK: {'title': 'Example', 'items': ['a', 'b']}
VALID: object matches schema: {'title': 'Example', 'items': ['a', 'b']}
========================================
Sample 2 RAW RESPONSE: {"items": [123, "b"]}
Parsed OK: {'items': [123, 'b']}
INVALID:
 - path items[0]: expected type 'string' but got int (123)
 - path <root>: 'title' is a required property
Original text for context: {"items": [123, "b"]}
========================================
Sample 3 RAW RESPONSE: Intro text... {"title": "Prose", "items": ["x", "y"]} End.
Note: extracted JSON from surrounding text
Parsed OK: {'title': 'Prose', 'items': ['x', 'y']}
VALID: object matches schema: {'title': 'Prose', 'items': ['x', 'y']}

Final visible checks (matching the course plan)
1. After successful parse step for the first sample: "Parsed OK: {'title': 'Example', 'items': ['a', 'b']}"
2. After heuristic extraction step (third sample): "Note: extracted JSON from surrounding text; Parsed OK: {'title':'Prose','items':['x','y']}"
3. After validation of schema-mismatched sample: "INVALID: path items[0]: expected type 'string' but got int (123); path <root>: 'title' is a required property"
4. For the correct sample: "VALID: object matches schema" and prints compact representation.

### Final Check

Run:
python validator_v1.py

You should see the three sample runs and the validation/parse outputs described above. Confirm that:
- The first sample parsed and validated as VALID.
- The second sample parsed but produced two clear formatted validation errors (type mismatch and missing required).
- The third sample used extraction to parse JSON inside prose and validated as VALID.

### Artifact

You have produced validator_v1.py which contains:
- parse_model_response(text) → (obj or None, error_message or None)
- validate_against_schema(obj, schema) → (bool, list_of_errors)
- format_validation_errors(errors) → list[str]
- SAMPLE_RESPONSES, SCHEMA, send_to_model stub (deterministic behavior for offline demos), and a demo main loop printing parse/validation results.

### Next Lesson

validator_v1.py is the validator core for Lesson 2. In the next lesson you'll reuse parse_model_response, validate_against_schema, and format_validation_errors to:
- Construct concise repair prompts from the formatted errors,
- Call send_to_model(prompt) to request corrected JSON (the send_to_model stub will respond deterministically to prompts that include "Return only JSON"),
- Implement a limited repair + retry loop that parses and re-validates repaired responses,
- Return only schema-valid data or a clear repair-failed summary.

Because validator_v1.py already produces deterministic, well-formatted validation errors and handles parsing+extraction, Lesson 2 will be able to build a repair loop without introducing new parsing or validation techniques.

--- END LESSON 1 ---