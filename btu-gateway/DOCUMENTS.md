# RealmForge Secure Document Agent: BTU Gateway Integration

This adds an isolated, authenticated document service to the existing Python BTU gateway without changing `/jobs` or the video worker. It uses the existing Pydantic document analysis model with OpenAI moderation and structured outputs. Documents remain untrusted data; no instructions in a document are executed.

## Install

Copy `btu-gateway/document_api.py` and `btu-gateway/secure_doc_core.py` alongside the existing `btu-gateway/server.py` and update `server.py` using the supplied copy. Install dependencies with `python -m pip install -r btu-gateway/requirements-documents.txt` on the gateway host. Configure **private environment variables**:

- `OPENAI_API_KEY`: OpenAI Platform API key. Never include it in a document or commit it.
- `BTU_DEVICE_TOKEN`: random token of at least 32 characters to call the documents endpoints.
- `DOC_AGENT_APPROVAL_TOKEN`: different random token of at least 32 characters for review and approval.
- `REALMFORGE_DOC_DATA`: optional private directory for SQLite audit and approved JSON exports.

Default gateway bind is `127.0.0.1` and default port `5000`; document endpoints are disabled when BTU is bound to other interfaces. Use an authenticated SSH tunnel for remote access. Do not expose the service on the public internet or over an untrusted LAN.

Start the gateway with `python btu-gateway/server.py`. Existing `POST /jobs` remains separate and does not invoke the document analyzer.

## Documents endpoints

All requests need `Authorization: Bearer <BTU_DEVICE_TOKEN>`; all POSTs use `Content-Type: application/json` and JSON objects. Approval/review POSTs *also* need the private `X-Approval-Token: <DOC_AGENT_APPROVAL_TOKEN>` header, which must come from the human operator, never from a document or model-generated text.

- `POST /documents/analyze` `{"text":"Ticket message"}`: moderated, structured analysis; returns case ID, SHA-256 fingerprint, heuristic indicators and review state.
- `GET /documents/{case_id}`: retrieve a stored analysis (never raw document).
- `GET /documents/audit`: show an event log without original document text.
- `POST /documents/{case_id}/review` `{"reviewer":"operator"}`: acknowledge a flagged document, requires approval token.
- `POST /documents/{case_id}/propose-export` `{}`: create pending local report proposal; flags must first be reviewed.
- `POST /documents/exports/{proposal_id}/approve` `{"reviewer":"operator"}`: human approves the pending export, requires approval token.
- `POST /documents/exports/{proposal_id}/execute` `{}`: output JSON report in configured export folder, only once, after approval. This does **not** upload, email, submit render jobs, execute commands, or contact arbitrary destinations.

Moderation is a content-policy screening signal, **not** an injection detector. Regex patterns only trigger review and are not perfect protection. Model output is always validated with Pydantic before saving, and action decisions depend on the host database and human token, not on model instructions. Both OpenAI calls are fail-closed. `store=False` is used for the model classification request; review the OpenAI platform data policy for your intended document sensitivity.

## Testing

Run `python -m unittest discover -s tests -v` from this integration package's root. Tests mock the OpenAI provider and do not prove live API availability or the safety of production networking. No GPU inference, video rendering, Android installation, or production deployment is claimed.