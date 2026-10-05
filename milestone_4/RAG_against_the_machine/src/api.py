"""API HTTP locale (bonus 5): interrogare l'indice e farsi rispondere
senza CLI.

`http.server` della stdlib: zero dipendenze, sufficientemente robusto per
un servizio di sviluppo a una sola macchina. Gli endpoint:

- `POST /search`  {"question", "k", "retrieval"?} -> StudentSearchResults
- `POST /answer`  same body -> StudentSearchResultsAndAnswer
- `GET  /healthz` -> {"status": "ok"}

I corpi di risposta sono i modelli pydantic del subject, quindi il JSON
volante è lo stesso dei file. `Qwen3` si carica pigro alla prima `/answer`.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from pydantic import BaseModel
from tqdm import tqdm

from src.models import (
    MinimalAnswer, MinimalSearchResults, StudentSearchResults,
    StudentSearchResultsAndAnswer,
)
from src.retriever import RETRIEVAL_CHOICES, RETRIEVAL_MODES, Retriever


class ApiRequest(BaseModel):
    """Corpo di `/search` e `/answer`; `retrieval` è opzionale."""

    question: str = ""
    k: int = 5
    retrieval: str = "bm25"


class Api:
    """Stato condiviso del server: indice una volta, modello al bisogno."""

    def __init__(self, processed_dir: str,
                 retrieval: str = "bm25") -> None:
        """Carica l'indice; il generatore resta pigro (torch è lento).

        Raises:
            ValueError: indice assente o `retrieval` non valida (il
                messaggio dice cosa manca).
        """
        if retrieval not in RETRIEVAL_MODES:
            raise ValueError(f"retrieval must be one of "
                             f"{RETRIEVAL_CHOICES}, got {retrieval!r}")
        self.retriever = Retriever(processed_dir, retrieval=retrieval)
        self.retrieval = retrieval
        self._generator: Any | None = None
        self._generator_lock = threading.Lock()

    def generator(self) -> Any:
        """Il `Generator`, caricato una sola volta (thread-safe)."""
        if self._generator is None:
            with self._generator_lock:
                if self._generator is None:
                    from src.generator import MODEL_NAME, Generator

                    tqdm.write(f"loading {MODEL_NAME} ...")
                    self._generator = Generator()
        return self._generator

    def handle(self, path: str, body: bytes) -> tuple[int, dict[str, Any]]:
        """Smanda un'HTTP request già letta: (status, corpo JSON).

        Ogni input degenere (JSON malformato, k=0, query vuota) dà
        4xx e un corpo leggibile: l'API non fa mai crollare il server.
        """
        if path == "/healthz":
            return 200, {"status": "ok"}
        if path not in ("/search", "/answer"):
            return 404, {"error": "unknown endpoint; use /search or /answer"}
        try:
            payload = ApiRequest.model_validate_json(body)
        except Exception as e:
            message = str(e).splitlines()[0] if str(e) else "empty body"
            return 400, {"error": f"invalid request body: {message}"}
        question = payload.question.strip()
        if not question:
            return 400, {"error": "question must not be empty"}
        if payload.k < 1:
            return 400, {"error": "k must be >= 1"}
        if payload.retrieval not in RETRIEVAL_MODES:
            return 400, {
                "error": (
                    f"retrieval must be one of {RETRIEVAL_CHOICES}, "
                    f"got {payload.retrieval!r}"),
            }
        try:
            sources = self.retriever.search(
                question, payload.k, retrieval=payload.retrieval)
        except Exception as e:  # the API must not crash the server
            return 500, {"error": f"{type(e).__name__}: {e}"}
        results = [MinimalSearchResults(
            question_id="api", question=question,
            retrieved_sources=sources)]
        if path == "/search":
            return 200, StudentSearchResults(
                search_results=results, k=payload.k).model_dump()
        try:
            answer = self.generator().answer(question, sources)
        except Exception as e:
            return 500, {"error": f"{type(e).__name__}: {e}"}
        return 200, StudentSearchResultsAndAnswer(search_results=[
            MinimalAnswer(question_id="api", question=question,
                          retrieved_sources=sources, answer=answer)],
            k=payload.k).model_dump()


class _Handler(BaseHTTPRequestHandler):
    """Traduce HTTP -> `Api.handle` -> HTTP, con CORS per i browser."""

    api: Api  # injected by `serve`

    def _reply(self, status: int, payload: dict[str, Any]) -> None:
        """Corpo JSON + CORS, senza mai far cadere la connessione."""
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        try:
            status, payload = self.api.handle(self.path.split("?")[0], b"{}")
        except Exception as e:
            status, payload = 500, {"error": f"{type(e).__name__}: {e}"}
        self._reply(status, payload)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length > 0 else b""
        try:
            status, payload = self.api.handle(self.path.split("?")[0], body)
        except Exception as e:
            status, payload = 500, {"error": f"{type(e).__name__}: {e}"}
        self._reply(status, payload)

    def log_message(self, format: str, *args: object) -> None:
        """Log di una riga per request (i progress bar restano leggibili)."""
        tqdm.write(f"{self.address_string()} {format % args}")


def serve(api: Api, host: str, port: int) -> None:
    """Avvia il server finché non viene fermato con Ctrl+C.

    `ThreadingHTTPServer`: una request lenta (il primo `/answer`) non
    blocca le altre.

    Raises:
        OSError: porta già occupata.
    """
    server = ThreadingHTTPServer((host, port), _Handler)
    _Handler.api = api
    print(f"Serving on http://{host}:{port}  (POST /search, /answer)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
