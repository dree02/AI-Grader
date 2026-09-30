# AI-Grader Project Plan

## Goal
Make AI tool to check handwritten answer sheets. Input: PDF answer sheet, PDF question paper, rules. Output: PDF with red marks (circles, cross, tick, score).

## Tech Stack
- **Python**: Handle PDF to image (`pymupdf`), AI vision grading (`google-genai`), draw red marks on image (`opencv-python`), image back to PDF (`Pillow`).
- **Go**: Backend server (`main.go`) to receive POST requests, save PDFs, and run Python script.

## Progress
- [x] Make Github repo `dree02/AI-Grader`
- [x] `pdf_processor.py`: Read Answer PDF and Question PDF, convert to images.
- [x] `grader.py`: Send images and rules to `gemini-3.5-flash`.
- [x] Add **Retry Logic** for Gemini 503 Server Busy errors.
- [x] Fix coordinate scaling from 1000x1000 grid to actual image size.
- [x] Draw red ticks, crosses, circles, and text on images.
- [x] Output final `_graded.pdf`.
- [x] Make Go backend server (`localhost:8080/grade`) to run it all via API.
- [x] Test with real Probability test papers.

## Next Steps (For Next Session)
- [ ] Connect Go backend server fully (right now it expects text question, we need to update it to accept Question PDF upload as well!).
- [ ] Make a simple Web UI (HTML/CSS) so user can drag-and-drop PDFs instead of using `curl` or terminal.
- [ ] Improve AI prompt to give more detailed step-by-step mark breakdown.

## How to Resume
Tell AI: "Read `PROJECT_PLAN.md` and continue from Next Steps."
