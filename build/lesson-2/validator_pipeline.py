import json

from validator_v1 import (
    SAMPLE_RESPONSES,
    SCHEMA,
    format_validation_errors,
    parse_model_response,
    send_to_model,
    validate_against_schema,
)


def make_repair_prompt(original_text, formatted_errors, schema):
    error_text = "\n".join(f"- {error}" for error in formatted_errors)

    return f"""
Please fix the JSON below so it matches the schema.

Errors:
{error_text}

Original response:
{original_text}

Return only JSON matching this schema:
{json.dumps(schema)}

Return only JSON — no explanatory text.
""".strip()


def repair_once(prompt_text, schema):
    raw_response = send_to_model(prompt_text)

    obj, parse_note = parse_model_response(raw_response)

    if obj is None:
        return (
            None,
            False,
            False,
            [parse_note],
            raw_response,
        )

    valid, errors = validate_against_schema(obj, schema)

    if valid:
        return (
            obj,
            True,
            True,
            [],
            raw_response,
        )

    formatted_errors = format_validation_errors(errors)

    return (
        obj,
        True,
        False,
        formatted_errors,
        raw_response,
    )


def run_repair_loop(original_text, schema, max_attempts=3):
    obj, parse_note = parse_model_response(original_text)

    # Attempt 1: validate the original response
    if obj is not None:
        valid, errors = validate_against_schema(obj, schema)

        if valid:
            print(
                "Attempt 1: Parsed OK and VALID — returning object:",
                obj,
            )
            return obj, None

        formatted_errors = format_validation_errors(errors)

        print(
            "Attempt 1: INVALID —",
            "; ".join(formatted_errors),
        )

    else:
        formatted_errors = [parse_note]

        print(
            "Attempt 1: Parse FAILED —",
            parse_note,
        )

    last_raw_response = original_text

    # Repair attempts
    for attempt in range(2, max_attempts + 1):

        prompt = make_repair_prompt(
            last_raw_response,
            formatted_errors,
            schema,
        )

        (
            repaired_obj,
            parsed_ok,
            validation_ok,
            new_errors,
            raw_response,
        ) = repair_once(prompt, schema)

        if raw_response == last_raw_response:
            print("Repeated identical response; aborting early.")

            return (
                None,
                f"Repair failed after {attempt - 1} attempts: "
                f"repeated identical response",
            )

        if parsed_ok and validation_ok:
            print(
                f"Attempt {attempt}: Parsed OK and VALID "
                f"— returning object:",
                repaired_obj,
            )

            return repaired_obj, None

        print(
            f"Attempt {attempt}: INVALID —",
            "; ".join(new_errors),
        )

        last_raw_response = raw_response
        formatted_errors = new_errors

    return (
        None,
        f"Repair failed after {max_attempts} attempts: "
        f"last errors: {'; '.join(formatted_errors)}",
    )


def run_parse_validate_repair(
    input_text,
    schema,
    max_attempts=3,
):
    return run_repair_loop(
        input_text,
        schema,
        max_attempts=max_attempts,
    )


def main():
    # Start with the intentionally invalid sample from Lesson 1
    initial_response = SAMPLE_RESPONSES[1]

    result, error = run_parse_validate_repair(
        initial_response,
        SCHEMA,
        max_attempts=3,
    )

    if result is not None:
        print("Final result:", result)
    else:
        print("Final failure:", error)


if __name__ == "__main__":
    main()