The learner is:
    A developer whose AI pipeline breaks when the model returns prose, malformed JSON, 
    or JSON that does not match the structure their program expects.


Breaking Points:
    The user thinks that asking an LLM to "return JSON" guarantees usable JSON
    They do not understand the difference between valid JSON and JSON that matches a required schema
    They do not know how to detect and explain schema validation failures
    They do not know what to do after validation fails besides blindy retrying the model


Checkpoints:
    A checkpoint is something that the learner can actually do after learning

Lesson 1:
    Parse an LLM response as JSON
    Validate the parsed response against a schema
    Print useful validation errors when the response is wrong

Lesson 2:
    Use validation errors to create a repair request
    Retry an invalid repsonse with a limited repair loop
    Return only data that successfully passes the schema validation 


Final Capstone:
    A Python pipeline that accepts an LLM repsonse, parses it, validates it against a schema, detects invalid output, repairs the response, and validates the repaired result before returning it.

Visualization:


                    LLM Response
                        ↓
                    Parse JSON
                    /       \
                Valid       Invalid
                  ↓             ↓
                Return      Validation Errors
                                ↓
                            Repair Request
                                ↓
                            New Response
                                ↓
                            Validate Again



Splitting the Lessons:
    Lesson 1: Validating Structured Output
        The learner builds: 
            LLM Response -> JSON Parser -> Schema Validator
        A working validator will tell them whether the model output matches the required schema

    Lesson 2: Repairing Invalid Output
        Start with the validator from Lesson 1 and add:
            Validation Failure -> Repaire Instructions -> Retry -> Revalidation 
        The final result is the complete schema-validaiton and repair pipeline aka CAPSTONE!!
        