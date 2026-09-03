The learner is:
    A developer whose AI pipeline breaks when the model returns prose, malformed JSON, 
    or JSON that does not match the structure their program expects.

Breaking Points:
    The user thinks that asking an LLM to "return JSON" guarantees usable JSON
    They do not understand the difference between valid JSON and JSON that matches a required schema
    They do not know how to detect and explain schema validation failures
    They do not know what to do after validation fails besides blindy retrying the model