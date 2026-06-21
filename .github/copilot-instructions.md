## Capstone — AI Ask Endpoint

### New in-scope files (capstone only)
- `src/app.py` — add /api/ask endpoint and classify_query() below existing routes
- `src/extensions/kb_extension.py` — RAG tool wrapper
- `src/sql/text2sql.py` — Text2SQL tool wrapper
- `src/static/ask.html` — frontend widget
- `src/tests/test_app.py` — new tests at BOTTOM only

### Capstone NEVER_MODIFY (in addition to existing NEVER_MODIFY list)
- src/static/index.html — existing UI must not change
- The ACTIVITIES dictionary — do not restructure, rename, or move
- Any existing route function signatures

### Query routing logic
- "Tell me about", "What is", "Describe", "How does" → RAG tool
- "How many", "Which activities", "List all", "How many spots" → Text2SQL
- "Sign up", "Register", "Join" → return link to existing signup endpoint (do not implement)

### API contract for /api/ask
POST /api/ask
Body: {"question": "string"}
Response 200: {"answer": "string", "source": "rag"|"text2sql"|"direct", "confidence": 0-1}
Response 400: {"error": "question field required"}
Response 500: {"error": "classification failed"}