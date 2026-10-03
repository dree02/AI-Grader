import os
import sys
import json
from google import genai
from google.genai import types
from pdf_processor import pdf_to_images

def main():
    if len(sys.argv) < 4:
        print("Usage: python3 submit_batch.py <answer_sheets_dir> <question_pdf> <rules_text>")
        sys.exit(1)

    answer_sheets_dir = sys.argv[1]
    question_pdf = sys.argv[2]
    rules = sys.argv[3]

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # Fallback to keys string
        keys_str = os.environ.get("GEMINI_API_KEYS")
        if keys_str:
            api_key = keys_str.split(',')[0].strip()
        else:
            print("Error: Please set GEMINI_API_KEY")
            sys.exit(1)

    client = genai.Client(api_key=api_key)

    prompt = f"""
    You are an expert examiner grading a student's answer sheet.
    Attached are the images of the student's answer sheet.
    Please refer to the uploaded Question Paper images.
    Here are the grading rules and rubric:
    {rules}
    
    Please grade the attached answer sheet images meticulously step-by-step.
    Provide a detailed mark breakdown for each question. Evaluate every step the student took, assigning partial marks according to the rubric.

    CRITICAL INSTRUCTIONS FOR MISTAKES & MARKS:
    1. Identify mistakes clearly in the feedback.
    2. Add a 'circle' mark to encircle the exact mistake on the image. BE EXTREMELY PRECISE with your bounding boxes (bbox). The bbox [x1, y1, x2, y2] is on a 0-1000 scale. Do not make circles huge.
    3. Add a 'text' mark near the mistake to write the correct explanation and solution.
    4. For EVERY question attempted by the student, add a 'text' mark exactly NEXT TO the handwritten question number on the image writing the marks awarded (e.g., "Q1: 2/5 marks"). Find where the student wrote "Q1" or "Ans 1" and place it near there. Do not put it randomly.
    5. Double-check your coordinates so marks do not overlap the student's writing incorrectly.

    Output your response in JSON format.
    The JSON must contain:
    1. 'student_name': string (Extract the full name, including surname, written by the student on the first page. If no name is found, use "Unknown_Student").
    2. 'total_score': integer
    3. 'feedback': string (detailed step-by-step feedback)
    4. 'coordinate_reasoning': string (THINK step-by-step about exactly where each question number and mistake is physically located on the page BEFORE generating the marks. Explain the visual layout and why you chose specific coordinates).
    5. 'marks': a list of objects representing where to draw marks on the image.
       Each mark object must have:
       - 'page_index': integer (0-indexed, which image this mark belongs to)
       - 'type': string (one of 'tick', 'cross', 'circle', 'text')
       - 'bbox': [x1, y1, x2, y2] (approximate coordinates where to draw on a 1000x1000 scaled grid, 0,0 is top-left)
       - 'text': string (only if type is 'text', e.g. correct solution/explanation)
    """

    print(f"Processing Question Paper: {question_pdf}")
    q_out_dir = question_pdf + "_images"
    q_images = pdf_to_images(question_pdf, q_out_dir)
    print("Uploading Question Paper images...")
    q_file_uris = []
    for img in q_images:
        f = client.files.upload(file=img)
        q_file_uris.append(f.uri)

    requests_jsonl = []
    
    import glob
    pdf_files = glob.glob(os.path.join(answer_sheets_dir, "*.pdf"))
    if not pdf_files:
        print("No PDFs found in directory.")
        sys.exit(1)

    print(f"Found {len(pdf_files)} PDFs. Preparing batch requests...")
    
    for i, pdf_file in enumerate(pdf_files):
        print(f"Processing ({i+1}/{len(pdf_files)}): {pdf_file}")
        out_dir = pdf_file + "_images"
        images = pdf_to_images(pdf_file, out_dir)
        
        parts = [{"text": prompt}]
        # Add answer sheet images
        for img in images:
            f = client.files.upload(file=img)
            parts.append({"fileData": {"fileUri": f.uri, "mimeType": "image/png"}})
        # Add question paper images
        for q_uri in q_file_uris:
            parts.append({"fileData": {"fileUri": q_uri, "mimeType": "image/png"}})
            
        request_obj = {
            "id": f"student_{i}",
            "request": {
                "contents": [
                    {"parts": parts}
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.1
                }
            }
        }
        requests_jsonl.append(json.dumps(request_obj))

    # Write JSONL to file
    jsonl_filename = "batch_input.jsonl"
    with open(jsonl_filename, "w") as f:
        f.write("\n".join(requests_jsonl))
        
    print(f"Uploading {jsonl_filename} to Gemini...")
    batch_input_file = client.files.upload(file=jsonl_filename, config={"mime_type": "application/jsonl"})
    
    print("Creating Batch Job...")
    try:
        batch_job = client.batches.create(
            model="gemini-3.1-pro-preview",
            src=batch_input_file.name,
            config={"display_name": "answersheet_eval_3_1"}
        )
        print("========================================")
        print("BATCH JOB CREATED SUCCESSFULLY!")
        print(f"Job Name: {batch_job.name}")
        print("========================================")
        print("Save this Job Name! You will need it to fetch the results.")
        
        # Save to a local file for the fetch script
        with open("latest_batch_job.txt", "w") as f:
            f.write(batch_job.name)
            
    except Exception as e:
        print("Failed to create batch job. Error:")
        print(e)
        print("\nNote: FAILED_PRECONDITION usually means your API key requires a Paid Tier (Billing Enabled) to use the Batch API.")

if __name__ == "__main__":
    main()
