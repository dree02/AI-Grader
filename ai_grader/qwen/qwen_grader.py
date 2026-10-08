import os
import sys
import json
import base64
from openai import OpenAI
import glob
from qwen_pdf_processor import pdf_to_images, evaluate_answer_sheet, grade_answer_sheets

# This script uses Qwen2.5-VL via Together AI or OpenRouter
def main():
    if len(sys.argv) < 4:
        print("Usage: python3 qwen_grader.py <answer_sheets_dir> <question_pdf> <rules_text>")
        sys.exit(1)

    answer_sheets_dir = sys.argv[1]
    question_pdf = sys.argv[2]
    rules = sys.argv[3]

    # Use OpenRouter or Together API key
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("TOGETHER_API_KEY")
    if not api_key:
        print("Error: Please set OPENROUTER_API_KEY or TOGETHER_API_KEY in your environment.")
        sys.exit(1)

    # Determine base URL based on which key is available
    if os.environ.get("TOGETHER_API_KEY"):
        base_url = "https://api.together.xyz/v1"
        model_name = "Qwen/Qwen2.5-VL-72B-Instruct"
    else:
        base_url = "https://openrouter.ai/api/v1"
        model_name = "qwen/qwen-2.5-vl-72b-instruct"

    print(f"Using Model: {model_name} via {base_url}")
    grade_answer_sheets(answer_sheets_dir, question_pdf, rules, api_key, base_url, model_name)

if __name__ == "__main__":
    main()
