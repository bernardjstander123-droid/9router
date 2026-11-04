"""Optional, localhost-only RealmForge document endpoints for the existing BTU gateway.

Untrusted documents are DATA. The model has no access to render queues, shell,
filesystem tools, or arbitrary HTTP actions. Only approved JSON report exports exist.
"""
from __future__ import annotations

import hmac
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

MAX_BODY = 115_000
CASE_ID = re.compile(r"[a-f0-9]{32}\Z")
_ALLOWED_LOCAL = ("127.0.0.1", "::1")


def _authorize(handler):
    if handler.server.server_address[0] not in _ALLOWED_LOCAL:
        handler.respond(403, {"error": "documents_loopback_only"})
        return False
    token = os.environ.get("BTU_DEVICE_TOKEN", "")
    if len(token) < 32:
        handler.respond(503, {"error": "strong_device_token_required"})
        return False
    auth = handler.headers.get("Authorization", "")
    if not hmac.compare_digest(auth, "Bearer " + token):
        handler.respond(401, {"error": "unauthorized"})
        return False
    return True


def _body(handler):
    if handler.headers.get("Content-Type", "").split(";", 1)[0].lower().strip() != "application/json":
        raise ValueError("JSON content-type required")
    size = int(handler.headers.get("Content-Length", "-1"))
    if size <= 0 or size > MAX_BODY:
        raise ValueError("Invalid request size")
    data = json.loads(handler.rfile.read(size).decode("utf-8", "strict"))
    if not isinstance(data, dict):
        raise ValueError("JSON object required")
    return data


def _agent(need_provider=False):
    # Optional dependencies only loaded when a documents endpoint is called.
    from secure_doc_core import Store, DocumentAgent, OpenAIProvider
    home = Path(os.environ.get("REALMFORGE_DOC_DATA", str(Path.home() / ".realmforge"))).expanduser()
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    store = Store(home / "documents.sqlite3")
    try:
        agent = DocumentAgent(store, OpenAIProvider(model="gpt-4o-mini") if need_provider else None, home / "exports")
    except Exception:
        store.close()
        raise
    return agent


def _reply(handler, status, obj):
    handler.respond(status, obj)


def handle_documents(handler):
    """Call only from /documents/* routes, never from the render jobs path."""
    if not _authorize(handler):
        return
    parts = urlsplit(handler.path)
    if parts.query or parts.fragment:
        return _reply(handler, 404, {"error": "not_found"})
    path = parts.path.split("/")[1:]
    method = handler.command
    # Do not expose internal service exception messages or private document contents.
    try:
        from secure_doc_core import GuardError
        if method == "POST" and path == ["documents", "analyze"]:
            payload = _body(handler)
            if set(payload) != {"text"}:
                raise ValueError("Only 'text' is accepted")
            agent = _agent(need_provider=True)
            try:
                return _reply(handler, 200, agent.ingest(payload["text"]))
            finally:
                agent.store.close()

        if method == "GET" and len(path) == 2 and path[0] == "documents" and CASE_ID.fullmatch(path[1]):
            agent = _agent()
            try:
                return _reply(handler, 200, agent.show(path[1]))
            finally:
                agent.store.close()

        if method == "GET" and path == ["documents", "audit"]:
            agent = _agent()
            try:
                return _reply(handler, 200, {"events": agent.audit()})
            finally:
                agent.store.close()

        if method == "POST" and len(path) == 3 and path[0] == "documents" and CASE_ID.fullmatch(path[1]):
            action = path[2]
            if action not in ("review", "propose-export"):
                return _reply(handler, 404, {"error": "not_found"})
            payload = _body(handler)
            agent = _agent()
            try:
                if action == "review":
                    if set(payload) != {"reviewer"}:
                        raise ValueError("Reviewer required")
                    result = agent.mark_reviewed(path[1], payload["reviewer"], handler.headers.get("X-Approval-Token", ""))
                else:
                    if payload:
                        raise ValueError("Proposal must not include extra fields")
                    result = agent.propose_export(path[1])
                return _reply(handler, 200, result)
            finally:
                agent.store.close()

        if method == "POST" and len(path) == 4 and path[:2] == ["documents", "exports"] and CASE_ID.fullmatch(path[2]):
            action = path[3]
            if action not in ("approve", "execute"):
                return _reply(handler, 404, {"error": "not_found"})
            payload = _body(handler)
            agent = _agent()
            try:
                if action == "approve":
                    if set(payload) != {"reviewer"}:
                        raise ValueError("Reviewer required")
                    result = agent.approve(path[2], payload["reviewer"], handler.headers.get("X-Approval-Token", ""))
                else:
                    if payload:
                        raise ValueError("No execution arguments allowed")
                    result = agent.execute(path[2])
                return _reply(handler, 200, result)
            finally:
                agent.store.close()
        return _reply(handler, 404, {"error": "not_found"})
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        return _reply(handler, 400, {"error": "invalid_request"})
    except GuardError:
        return _reply(handler, 403, {"error": "document_action_denied_or_invalid"})
    except (ImportError, ModuleNotFoundError):
        return _reply(handler, 503, {"error": "document_dependencies_missing"})
    except Exception:
        return _reply(handler, 503, {"error": "document_service_unavailable"})