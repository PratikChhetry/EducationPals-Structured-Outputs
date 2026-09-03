import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Load API key from .env
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY was not found in your .env file")

client = OpenAI(api_key=api_key)

# Find the agent folder
agent_dir = Path(__file__).parent

# File paths
course_spec_path = agent_dir / "course-spec.md"
planner_prompt_path = agent_dir / "prompts" / "planner.txt"
output_dir = agent_dir / "generated"
output_path = output_dir / "course-plan.md"

# Read the course specification
course_spec = course_spec_path.read_text(encoding="utf-8")

# Read the planner instructions
planner_prompt = planner_prompt_path.read_text(encoding="utf-8")

# Combine the planner instructions with the course specification
full_prompt = f"""
{planner_prompt}

Here is the course specification you must use:

--- COURSE SPECIFICATION ---

{course_spec}

--- END COURSE SPECIFICATION ---
"""


print("Generating course plan...")


response = client.responses.create(
    model="gpt-5-mini",
    input=full_prompt
)

course_plan = response.output_text

# Create generated folder if it does not exist
output_dir.mkdir(exist_ok=True)

# Save the generated course plan
output_path.write_text(course_plan, encoding="utf-8")

print("Course plan generated successfully.")
print(f"Saved to: {output_path}")