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


# Step 2: Generate a lesson

def generate_lesson(lesson_number):

    course_plan = read_file(course_plan_path)
    lesson_generator = read_file(lesson_generator_path)

    full_prompt = f"""
{lesson_generator}

Here is the approved course plan:

--- COURSE PLAN ---

{course_plan}

--- END COURSE PLAN ---

Generate Lesson {lesson_number} only.

Follow the Lesson {lesson_number} plan exactly.
Do not generate content for any other lesson.
"""

    print(f"Generating Lesson {lesson_number}...")

    response = client.responses.create(
        model="gpt-5-mini",
        input=full_prompt
    )

    lesson = response.output_text

    course_dir.mkdir(exist_ok=True)

    lesson_path = course_dir / f"lesson-{lesson_number}.md"

    lesson_path.write_text(
        lesson,
        encoding="utf-8"
    )

    print(f"Lesson {lesson_number} generated.")
    print(f"Saved to: {lesson_path}")


# Run

if __name__ == "__main__":

    if not course_plan_path.exists():
        generate_course_plan()
    else:
        print("Existing course plan found.")

    lesson_1_path = course_dir / "lesson-1.md"
    lesson_2_path = course_dir / "lesson-2.md"

    if not lesson_1_path.exists():
        generate_lesson(1)
    else:
        print("Existing Lesson 1 found.")

    if not lesson_2_path.exists():
        generate_lesson(2)
    else:
        print("Existing Lesson 2 found.")

if __name__ == "__main__":

    if not course_plan_path.exists() or course_plan_path.stat().st_size == 0:
        generate_course_plan()
    else:
        print("Existing course plan found.")

    lesson_1_path = course_dir / "lesson-1.md"
    lesson_2_path = course_dir / "lesson-2.md"

    if not lesson_1_path.exists() or lesson_1_path.stat().st_size == 0:
        generate_lesson(1)
    else:
        print("Existing Lesson 1 found.")

    if not lesson_2_path.exists() or lesson_2_path.stat().st_size == 0:
        generate_lesson(2)
    else:
        print("Existing Lesson 2 found.")