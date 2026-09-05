from json import loads, JSONDecodeError

from jsonschema import Draft7Validator


SAMPLE_RESPONSES = [
    '{"title": "Example", "items": ["a", "b"]}',
    '{"items": [123, "b"]}',
    'Intro text... {"title": "Prose", "items": ["x", "y"]} End.',
]

SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "items": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["title", "items"],
}


def send_to_model(prompt):
    """
    Offline stub used by the course.

    It returns deterministic canned responses instead of making
    a real API call.
    """
    if "Return only JSON" in prompt:
        return '{"title": "Fixed", "items": ["a", "b"]}'

    if not hasattr(send_to_model, "_i"):
        send_to_model._i = 0

    response = SAMPLE_RESPONSES[
        send_to_model._i % len(SAMPLE_RESPONSES)
    ]

    send_to_model._i += 1
    return response


def parse_model_response(text):
    """
    Parse a model response as JSON.

    If direct parsing fails, try a limited heuristic that extracts
    one JSON object or array from surrounding prose.
    """

    try:
        return loads(text), None

    except JSONDecodeError as original_error:

        positions = [
            position
            for position in (
                text.find("{"),
                text.find("["),
            )
            if position != -1
        ]

        if positions:
            start = min(positions)

            if text[start] == "{":
                end = text.rfind("}")
            else:
                end = text.rfind("]")

            if end > start:

                candidate = text[start : end + 1]

                try:
                    obj = loads(candidate)
                    return obj, "extracted JSON from surrounding text"

                except JSONDecodeError:
                    pass

        return (
            None,
            f"JSONDecodeError: "
            f"{original_error.msg} "
            f"at pos {original_error.pos}",
        )


def validate_against_schema(obj, schema):

    validator = Draft7Validator(schema)

    errors = sorted(
        validator.iter_errors(obj),
        key=lambda error: list(error.absolute_path),
    )

    return len(errors) == 0, errors


def _path_to_string(path):

    result = ""

    for part in path:

        if isinstance(part, int):
            result += f"[{part}]"

        else:
            if result:
                result += "."

            result += str(part)

    return result or "<root>"


def format_validation_errors(errors):

    messages = []

    for error in errors:

        path = _path_to_string(error.absolute_path)

        if error.validator == "type":

            expected = error.validator_value
            actual = error.instance
            actual_type = type(actual).__name__

            messages.append(
                f"path {path}: expected type "
                f"'{expected}' but got "
                f"{actual_type} ({actual})"
            )

        elif error.validator == "required":

            messages.append(
                f"path {path}: {error.message}"
            )

        else:

            messages.append(
                f"path {path}: {error.message}"
            )

    return messages


def main():

    for number, text in enumerate(
        SAMPLE_RESPONSES,
        start=1,
    ):

        print("=" * 40)
        print(f"Sample {number} RAW RESPONSE: {text}")

        obj, parse_note = parse_model_response(text)

        if obj is None:

            print("Parse FAILED:", parse_note)
            continue

        if parse_note:
            print("Note:", parse_note)

        print("Parsed OK:", obj)

        valid, errors = validate_against_schema(
            obj,
            SCHEMA,
        )

        if valid:

            print(
                "VALID: object matches schema:",
                obj,
            )

        else:

            print("INVALID:")

            for message in format_validation_errors(
                errors
            ):
                print(" -", message)

            print(
                "Original text for context:",
                text,
            )


if __name__ == "__main__":
    main()