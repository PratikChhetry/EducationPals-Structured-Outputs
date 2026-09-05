import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# Setup

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY was not found in your .env file")

client = OpenAI(api_key=api_key)

agent_dir = Path(__file__).parent
project_dir = agent_dir.parent


# File paths

course_spec_path = agent_dir / "course-spec.md"

planner_prompt_path = agent_dir / "prompts" / "planner.txt"
lesson_generator_path = agent_dir / "prompts" / "lesson-generator.txt"

generated_dir = agent_dir / "generated"
course_plan_path = generated_dir / "course-plan.md"

course_dir = project_dir / "course"
lesson_1_path = course_dir / "lesson-1.md"


# Helper function

def read_file(path):
    return path.read_text(encoding="utf-8")


# Step 1: Generate course plan

def generate_course_plan():

    course_spec = read_file(course_spec_path)
    planner_prompt = read_file(planner_prompt_path)

    full_prompt = f"""
{planner_prompt}

Here is the course specification:

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

    generated_dir.mkdir(exist_ok=True)

    course_plan_path.write_text(
        course_plan,
        encoding="utf-8"
    )

    print("Course plan generated.")
    print(f"Saved to: {course_plan_path}")


# Step 2: Generate Lesson 1

def generate_lesson_1():

    course_plan = read_file(course_plan_path)
    lesson_generator = read_file(lesson_generator_path)

    full_prompt = f"""
{lesson_generator}

Here is the approved course plan:

--- COURSE PLAN ---

{course_plan}

--- END COURSE PLAN ---

Generate Lesson 1 only.

Follow the Lesson 1 plan exactly.
Do not generate Lesson 2.
"""

    print("Generating Lesson 1...")

    response = client.responses.create(
        model="gpt-5-mini",
        input=full_prompt
    )

    lesson_1 = response.output_text

    course_dir.mkdir(exist_ok=True)

    lesson_1_path.write_text(
        lesson_1,
        encoding="utf-8"
    )

    print("Lesson 1 generated.")
    print(f"Saved to: {lesson_1_path}")


# Run

if __name__ == "__main__":

    # Only regenerate the plan if it does not exist
    if not course_plan_path.exists():
        generate_course_plan()
    else:
        print("Existing course plan found.")

    generate_lesson_1()