# Skill: AI Ask Endpoint

## Description
Adds the /api/ask endpoint and classify_query() routing function to the
Mergington activities API. Routes natural language questions to the RAG
knowledge base (qualitative) or Text2SQL pipeline (quantitative).

## Trigger
Use when asked to: "add a question-answering endpoint", "implement NL
routing", "add an AI Q&A feature to the activities API".

Do NOT use when:
- Modifying existing activity endpoints
- Changing the ACTIVITIES dictionary
- Updating the existing frontend (index.html)

## Constraints

### NEVER_MODIFY — UAT-locked
- `get_activities()` in src/app.py
- `signup()` in src/app.py
- `remove_signup()` in src/app.py
- All existing functions in src/tests/test_app.py
- src/static/index.html
- The ACTIVITIES dictionary structure

### API contract (must not be changed once in production)
- POST /api/ask accepts {"question": str}
- Response: {"answer": str, "source": "rag"|"text2sql"|"direct", "confidence": float}
- 400 on missing/empty question, 500 on tool failure

### Security constraints
- Text2SQL: parameterised queries only — NEVER f-string SQL
- Text2SQL: SELECT only — NEVER DELETE, UPDATE, DROP, INSERT
- RAG: answers must cite source chunks — never generate from model training data
- No user input injected into SQL strings

### Required test outcomes
- All original 8 tests must pass after this skill is used
- New tests must cover: rag routing, text2sql routing, direct routing, 400 errors
- Coverage must not drop

## Examples

### Input
"Add routing so qualitative questions go to RAG and quantitative go to Text2SQL"

### Expected output
classify_query() with keyword matching + ask() route + stub imports for tools

## DRI
Capstone team lead — [name]
## Version
v1.0 — [capstone date]
## Deprecation policy
Update when new query types are added. Review after any schema migration.