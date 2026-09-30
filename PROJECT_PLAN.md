# AI-Grader Project Plan

## Goal
Make AI tool to check handwritten answer sheets. Input: PDF answer sheet, question paper, rules. Output: PDF with red marks (circles, cross, tick, score).

## Tech Stack
- **Python**: Handle PDF to image, AI vision grading (Gemini), draw red marks on image, image back to PDF.
- **Go**: Backend server to run Python scripts and manage files.

## Progress
- [x] Make Github repo `dree02/AI-Grader`
- [x] Make basic Python folder `ai_grader`
- [x] Make `pdf_processor.py` for read PDF and draw marks

## Next Steps
- [ ] Install Go (`brew install go`) if needed.
- [ ] Make `grader.py` in Python to talk to Gemini AI and get JSON grading result (with bounding boxes).
- [ ] Make Go backend to upload PDF, call Python, return final PDF.

## How to Resume
Tell AI: "Read PROJECT_PLAN.md and continue from Next Steps."
