# Structured Outputs Course

A 90-minute, two-lesson course that teaches a developer how to turn unreliable LLM output into schema-validated structured data with a repair loop.

The course and build-alongs were generated through an AI pipeline with separate planning, lesson-generation, review, and revision stages.

## Learner

This course is written for a developer whose LLM pipeline breaks when the model returns prose, malformed JSON, or JSON that does not match the expected schema.

## Capstone

By the end of the course, the learner builds a Python pipeline that:

1. Parses an LLM response as JSON
2. Validates the parsed data against a JSON Schema
3. Reports useful validation errors
4. Builds a repair prompt when validation fails
5. Retries the response through a bounded repair loop
6. Revalidates the repaired response
7. Returns only schema-valid data or a clear failure summary

The final capstone artifact is:


build/lesson-2/validator_pipeline.py


## Course Structure

### Lesson 1: Reliable JSON Parsing and Schema Validation

The learner builds:


build/lesson-1/validator_v1.py


Checkpoints:

* Parse JSON responses and handle `JSONDecodeError`
* Recover JSON from simple surrounding prose
* Validate parsed data against a JSON Schema
* Produce concise, developer-friendly validation errors

Lesson 1 produces the validator core that Lesson 2 directly reuses.

### Lesson 2: Automated Repair Loop

The learner extends the Lesson 1 validator into:


build/lesson-2/validator_pipeline.py


Checkpoints:

* Turn validation errors into repair instructions
* Run a single repair attempt
* Implement a bounded repair loop
* Detect repeated responses and stop safely
* Return only schema-valid data or a clear failure result

Lesson 2 completes the capstone.

## Project Structure



README.md
requirements.txt
writeup.md
    course/
        lesson-1.md
        lesson-2.md

build/
    lesson-1/
        validator_v1.py
    lesson-2/
        validator_v1.py
        validator_pipeline.py

output/
    lesson-1.txt
    lesson-2.txt

agent/
    course-spec.md
    generate.py
    prompts/
        planner.txt
        lesson-generator.txt
        reviewer.txt
        reviser.txt
    generated/
        course-plan.md
        review.md
        lesson-1-revised.txt
        lesson-2-revised.txt


## Requirements

* Python 3.12
* `jsonschema`
* `openai`
* `python-dotenv`

Install dependencies with:

```bash
python -m pip install -r requirements.txt
```

## Run the Learner Build-Alongs

The learner-facing build-alongs run completely offline and do not require an API key.

Run Lesson 1:

```bash
python build/lesson-1/validator_v1.py
```

Expected behavior:

* Sample 1 parses and validates successfully
* Sample 2 parses but fails schema validation with clear errors
* Sample 3 extracts JSON from surrounding prose and validates successfully

Run Lesson 2:

```bash
python build/lesson-2/validator_pipeline.py
```

Expected final output:

```text
Attempt 1: INVALID path <root>: 'title' is a required property; path items[0]: expected type 'string' but got int (123)
Attempt 2: Parsed OK and VALID - returning object: {'title': 'Fixed', 'items': ['a', 'b']}
Final result: {'title': 'Fixed', 'items': ['a', 'b']}
```

The saved outputs from my local run are included in:

```text
output/lesson-1.txt
output/lesson-2.txt
```

## Offline Review

The learner-facing build does not make paid API calls.

`send_to_model()` is implemented as a deterministic local stub so the validator and repair loop can be replayed without network access.

The build demonstrates the same control flow as a production LLM pipeline:

```text
model output
    ↓
parse
    ↓
validate
    ↓
invalid
    ↓
repair prompt
    ↓
stubbed model response
    ↓
revalidate
    ↓
schema-valid result
```

## AI Generation Pipeline

The course was generated using a staged AI workflow rather than a single prompt.

```text
course-spec.md
    ↓
planner.txt
    ↓
course-plan.md
    ↓
lesson-generator.txt
    ↓
lesson-1.md + lesson-2.md
    ↓
reviewer.txt
    ↓
review.md
    ↓
reviser.txt
    ↓
revised lessons
```

### Planning Stage

`agent/course-spec.md` contains:

* learner definition
* breaking points
* checkpoints
* capstone
* lesson structure

`agent/prompts/planner.txt` transforms that specification into a detailed course blueprint.

### Lesson Generation Stage

`agent/prompts/lesson-generator.txt` turns the approved course plan into learner-facing lesson content and incremental build-alongs.

### Review Stage

`agent/prompts/reviewer.txt` checks:

* prerequisite order
* checkpoint coverage
* artifact reuse
* filename and function consistency
* offline execution
* build-along reliability
* capstone completion

### Revision Stage

`agent/prompts/reviser.txt` applies the reviewer feedback while preserving the approved lesson structure.

The generation code is in:


agent/generate.py


## API Key

An OpenAI API key is only required to regenerate the course through the agent pipeline.

The key is loaded from:


OPENAI_API_KEY


A local `.env` file can be used during development.

The real `.env` file is not included.

The learner-facing course and build-alongs do not require an API key.