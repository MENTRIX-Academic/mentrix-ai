# سجل تغييرات MENTRIX V3

- **Preserved:** original typed graders and question bank, FastAPI typed demo, OCR human-review flow and SQLite.
- **Added:** heuristic row-projection line suggestions, reviewer-confirmed only.
- **Added:** optional side-by-side Original RGB/Autocontrast TrOCR predictions per line (not automatic model selection).
- **Added:** local per-line diagnostic QA flags, not confidence estimates.
- **Added:** independent Chatbot tab with offline source-labelled retrieval for safe educational/project content; optional local Ollama.
- **Added:** SQLite migration for per-line candidate/quality data, backwards-compatible with previous records.
- **Added:** 4 new mocked tests, with 8 OCR tests overall, plus 15 integration and 5 research tests (28 in total).
- **Not claimed:** TrOCR general-accuracy improvement, trained essay grading, secure production accounts, generative LLM by default.
