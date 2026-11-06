
# MENTRIX AI
### AI-Assisted Teaching Assistant Platform

MENTRIX is an academic graduation project designed to assist
Teaching Assistants with classroom administration, student
attendance, answer recognition, and AI-assisted grading.

**Status:** Research and development prototype.

## Core Features

- Student and attendance management
- Handwritten English answer recognition (OCR)
- AI-assisted grading with human review
- MCQ, short-answer, and mathematical answer evaluation
- Attendance-related assistant
- OCR benchmarking and evaluation experiments

## AI Research

The project includes experimental handwriting recognition
pipelines using TrOCR and image preprocessing techniques.

Research tools support:
- Character Error Rate (CER)
- Word Error Rate (WER)
- Model and preprocessing comparisons
- Line and question detection evaluation
- Human ground-truth verification

Model performance on new handwriting is not yet fully
validated. OCR predictions must be reviewed before grading.

## Repository Structure

mentrix-ai/
  README.md
  requirements.txt
  environment_info.md
  configs/
  notebooks/
  results/
  MENTRIX/
    app.py
    grader.py
    ocr_integration.py
    research/
    training/
    static/
    tests/
    docs/

## Getting Started

The application is located inside the MENTRIX directory.

1. Clone the repository.
2. Open the MENTRIX directory on Windows.
3. Read README_START_HERE_EN.md or README_START_HERE_AR.md.
4. Follow the launcher instructions for the current version.

The current unified application documentation uses:
http://127.0.0.1:8765

The repository root also contains the AI development
environment. See environment_info.md.

## Documentation

- [Arabic Setup](MENTRIX/README_START_HERE_AR.md)
- [English Setup](MENTRIX/README_START_HERE_EN.md)
- [Sprint 08 Research Report](MENTRIX/docs/SPRINT08_IMPLEMENTATION_REPORT_AR.md)
- [AI Roadmap](MENTRIX/docs/AI_TRACK_ROADMAP.md)

## Security and Privacy

Do not commit API keys, passwords, real student records,
private handwritten answers, or local databases.

This is an academic prototype, not a production-ready
student information system.

## Future Development

- Evaluate OCR on independently verified handwriting data
- Improve full-answer-sheet processing
- Extend TA review and grading workflows
- Expand automated engineering tests
- Improve integration between platform components
