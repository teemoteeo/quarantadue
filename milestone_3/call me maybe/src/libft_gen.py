"""Genera le funzioni di libft (primo progetto 42) tramite LM Studio.

Per ogni funzione del catalogo invia una richiesta al server locale di
LM Studio e salva il file ``.c`` risultante in ``data/libft/``. Il modello
viene rilevato automaticamente tra quelli caricati sul server.

Uso:
    uv run python src/libft_gen.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, NamedTuple

# --------------------------------------------------------------------------
# Configurazione: modifica qui per cambiare server, parametri o percorsi.
# --------------------------------------------------------------------------
BASE_URL = "http://127.0.0.1:1234/v1"
TEMPERATURE = 0.1
MAX_TOKENS = 512
TIMEOUT_SECONDS = 300

OUTPUT_DIR = Path("data/libft")

SYSTEM_PROMPT = (
    "You are implementing the 42 School libft project in C. Rules: C99, "
    "norminette compliant (max 25 lines per function body, no for loops, "
    "no variable declarations after first instruction block, max 80 "
    "chars/line), no forbidden functions, no main(), no test code. Output "
    "ONLY the raw .c file content, no markdown, no backticks, no "
    "explanation. Start the file with the #include directives the code "
    "needs (e.g. <stddef.h> for size_t/NULL, <stdlib.h> for malloc, "
    "<unistd.h> for write); omit them only if nothing is needed."
)
# --------------------------------------------------------------------------

T_LIST = (
    "There is no libft.h: define the struct at the top of the file as "
    "'typedef struct s_list { void *content; struct s_list *next; } "
    "t_list;'."
)


class FunctionSpec(NamedTuple):
    """Una funzione di libft da generare."""

    name: str
    signature: str
    description: str
    allowed: str


FUNCTIONS: list[FunctionSpec] = [
    # ------------------------------------------------------------- Part 1
    FunctionSpec(
        "ft_isalpha", "int ft_isalpha(int c);",
        "Return non-zero if c is an alphabetic character, 0 otherwise.",
        "none",
    ),
    FunctionSpec(
        "ft_isdigit", "int ft_isdigit(int c);",
        "Return non-zero if c is a decimal digit, 0 otherwise.",
        "none",
    ),
    FunctionSpec(
        "ft_isalnum", "int ft_isalnum(int c);",
        "Return non-zero if c is alphanumeric, 0 otherwise.",
        "none",
    ),
    FunctionSpec(
        "ft_isascii", "int ft_isascii(int c);",
        "Return non-zero if c fits in the ASCII set (0-127), 0 otherwise.",
        "none",
    ),
    FunctionSpec(
        "ft_isprint", "int ft_isprint(int c);",
        "Return non-zero if c is printable including space, 0 otherwise.",
        "none",
    ),
    FunctionSpec(
        "ft_strlen", "size_t ft_strlen(const char *s);",
        "Return the length of the string s (excluding the terminating "
        "NUL).",
        "none",
    ),
    FunctionSpec(
        "ft_memset", "void *ft_memset(void *b, int c, size_t len);",
        "Fill the first len bytes of b with the byte c; return b.",
        "none",
    ),
    FunctionSpec(
        "ft_bzero", "void ft_bzero(void *s, size_t n);",
        "Set the first n bytes of s to zero.",
        "none",
    ),
    FunctionSpec(
        "ft_memcpy", "void *ft_memcpy(void *dst, const void *src, "
        "size_t n);",
        "Copy n bytes from src to dst (areas must not overlap); return "
        "dst.",
        "none",
    ),
    FunctionSpec(
        "ft_memmove", "void *ft_memmove(void *dst, const void *src, "
        "size_t len);",
        "Copy len bytes from src to dst, handling overlapping areas "
        "correctly; return dst.",
        "none",
    ),
    FunctionSpec(
        "ft_strlcpy", "size_t ft_strlcpy(char *dst, const char *src, "
        "size_t dstsize);",
        "Copy up to dstsize-1 chars from src to dst, NUL-terminate when "
        "dstsize > 0; return the length of src.",
        "none",
    ),
    FunctionSpec(
        "ft_strlcat", "size_t ft_strlcat(char *dst, const char *src, "
        "size_t dstsize);",
        "Append src to dst using at most dstsize bytes in total, "
        "NUL-terminating the result; return the total length it tried "
        "to create.",
        "none",
    ),
    FunctionSpec(
        "ft_toupper", "int ft_toupper(int c);",
        "Return c converted to uppercase if it is a lowercase letter, "
        "otherwise c unchanged.",
        "none",
    ),
    FunctionSpec(
        "ft_tolower", "int ft_tolower(int c);",
        "Return c converted to lowercase if it is an uppercase letter, "
        "otherwise c unchanged.",
        "none",
    ),
    FunctionSpec(
        "ft_strchr", "char *ft_strchr(const char *s, int c);",
        "Return a pointer to the first occurrence of c in s (the "
        "terminating NUL counts), or NULL if not found.",
        "none",
    ),
    FunctionSpec(
        "ft_strrchr", "char *ft_strrchr(const char *s, int c);",
        "Return a pointer to the last occurrence of c in s (the "
        "terminating NUL counts), or NULL if not found.",
        "none",
    ),
    FunctionSpec(
        "ft_strncmp", "int ft_strncmp(const char *s1, const char *s2, "
        "size_t n);",
        "Compare at most n chars of s1 and s2 as unsigned chars; return "
        "the difference at the first mismatch or 0.",
        "none",
    ),
    FunctionSpec(
        "ft_memchr", "void *ft_memchr(const void *s, int c, size_t n);",
        "Scan the first n bytes of s for the byte c; return a pointer "
        "to it or NULL.",
        "none",
    ),
    FunctionSpec(
        "ft_memcmp", "int ft_memcmp(const void *s1, const void *s2, "
        "size_t n);",
        "Compare the first n bytes of s1 and s2 as unsigned chars; "
        "return the difference at the first mismatch or 0.",
        "none",
    ),
    FunctionSpec(
        "ft_strnstr", "char *ft_strnstr(const char *haystack, const char "
        "*needle, size_t len);",
        "Locate needle in haystack searching at most len chars; return "
        "a pointer to its start, haystack if needle is empty, or NULL.",
        "none",
    ),
    FunctionSpec(
        "ft_atoi", "int ft_atoi(const char *str);",
        "Convert the initial portion of str to int: skip whitespace, "
        "accept one optional sign, then digits.",
        "none",
    ),
    FunctionSpec(
        "ft_calloc", "void *ft_calloc(size_t count, size_t size);",
        "Allocate count*size bytes set to zero; return the pointer or "
        "NULL on failure (including multiplication overflow).",
        "malloc",
    ),
    FunctionSpec(
        "ft_strdup", "char *ft_strdup(const char *s1);",
        "Return a newly allocated copy of s1, or NULL on allocation "
        "failure.",
        "malloc",
    ),
    # ------------------------------------------------------------- Part 2
    FunctionSpec(
        "ft_substr", "char *ft_substr(char const *s, unsigned int start, "
        "size_t len);",
        "Return a newly allocated substring of s starting at index "
        "start, at most len chars long; empty string if start is past "
        "the end; NULL on allocation failure.",
        "malloc",
    ),
    FunctionSpec(
        "ft_strjoin", "char *ft_strjoin(char const *s1, char const *s2);",
        "Return a newly allocated string that is the concatenation of "
        "s1 and s2, or NULL on allocation failure.",
        "malloc",
    ),
    FunctionSpec(
        "ft_strtrim", "char *ft_strtrim(char const *s1, char const "
        "*set);",
        "Return a newly allocated copy of s1 with characters from set "
        "removed from its beginning and end, or NULL on allocation "
        "failure.",
        "malloc",
    ),
    FunctionSpec(
        "ft_split", "char **ft_split(char const *s, char c);",
        "Split s by the delimiter c into a newly allocated "
        "NULL-terminated array of newly allocated strings; return NULL "
        "on allocation failure (free everything already allocated).",
        "malloc, free",
    ),
    FunctionSpec(
        "ft_itoa", "char *ft_itoa(int n);",
        "Return a newly allocated string representing n (handle "
        "INT_MIN and negative numbers), or NULL on allocation failure.",
        "malloc",
    ),
    FunctionSpec(
        "ft_strmapi", "char *ft_strmapi(char const *s, char (*f)("
        "unsigned int, char));",
        "Return a newly allocated string built by applying f to each "
        "char of s with its index, or NULL on allocation failure.",
        "malloc",
    ),
    FunctionSpec(
        "ft_striteri", "void ft_striteri(char *s, void (*f)(unsigned "
        "int, char *));",
        "Apply f to each char of s, passing its index and the address "
        "of the char.",
        "none",
    ),
    FunctionSpec(
        "ft_putchar_fd", "void ft_putchar_fd(char c, int fd);",
        "Write the char c to the file descriptor fd.",
        "write",
    ),
    FunctionSpec(
        "ft_putstr_fd", "void ft_putstr_fd(char *s, int fd);",
        "Write the string s to the file descriptor fd.",
        "write",
    ),
    FunctionSpec(
        "ft_putendl_fd", "void ft_putendl_fd(char *s, int fd);",
        "Write the string s followed by a newline to the file "
        "descriptor fd.",
        "write",
    ),
    FunctionSpec(
        "ft_putnbr_fd", "void ft_putnbr_fd(int n, int fd);",
        "Write the integer n to the file descriptor fd (handle "
        "INT_MIN).",
        "write",
    ),
    # -------------------------------------------------------------- Bonus
    FunctionSpec(
        "ft_lstnew", "t_list *ft_lstnew(void *content);",
        "Return a newly allocated node with the given content and a "
        "NULL next pointer. " + T_LIST,
        "malloc",
    ),
    FunctionSpec(
        "ft_lstadd_front", "void ft_lstadd_front(t_list **lst, t_list "
        "*new);",
        "Add the node new at the beginning of the list. " + T_LIST,
        "none",
    ),
    FunctionSpec(
        "ft_lstsize", "int ft_lstsize(t_list *lst);",
        "Return the number of nodes in the list. " + T_LIST,
        "none",
    ),
    FunctionSpec(
        "ft_lstlast", "t_list *ft_lstlast(t_list *lst);",
        "Return the last node of the list, or NULL if empty. " + T_LIST,
        "none",
    ),
    FunctionSpec(
        "ft_lstadd_back", "void ft_lstadd_back(t_list **lst, t_list "
        "*new);",
        "Add the node new at the end of the list. " + T_LIST,
        "none",
    ),
    FunctionSpec(
        "ft_lstdelone", "void ft_lstdelone(t_list *lst, void (*del)("
        "void *));",
        "Free the content of the node with del, then free the node "
        "(do not touch next). " + T_LIST,
        "free",
    ),
    FunctionSpec(
        "ft_lstclear", "void ft_lstclear(t_list **lst, void (*del)("
        "void *));",
        "Delete and free every node of the list with del, then set "
        "*lst to NULL. " + T_LIST,
        "free",
    ),
    FunctionSpec(
        "ft_lstiter", "void ft_lstiter(t_list *lst, void (*f)(void *));",
        "Apply f to the content of every node of the list. " + T_LIST,
        "none",
    ),
    FunctionSpec(
        "ft_lstmap", "t_list *ft_lstmap(t_list *lst, void *(*f)(void "
        "*), void (*del)(void *));",
        "Return a new list built by applying f to the content of every "
        "node; on allocation failure clear the new list with del and "
        "return NULL. " + T_LIST,
        "malloc, free",
    ),
]


def _get_json(url: str) -> Any:
    """Esegue una GET e restituisce il corpo JSON decodificato."""
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
        return json.load(response)


def _detect_model() -> str:
    """Rileva il modello caricato sul server di LM Studio.

    Preferisce l'endpoint nativo ``/api/v0/models`` (che espone lo stato
    di caricamento); ripiega su ``/v1/models`` scartando gli embedding.
    """
    root = BASE_URL.rsplit("/v1", 1)[0]
    try:
        body = _get_json(f"{root}/api/v0/models")
        for entry in body.get("data", []):
            if entry.get("state") == "loaded" and entry.get("type") == "llm":
                return str(entry["id"])
    except (urllib.error.URLError, KeyError, ValueError):
        pass
    body = _get_json(f"{BASE_URL}/models")
    for entry in body.get("data", []):
        model_id = str(entry.get("id", ""))
        if model_id and "embed" not in model_id:
            return model_id
    raise RuntimeError("no usable model found on the server")


def _generate(model: str, spec: FunctionSpec) -> str:
    """Chiede al modello il contenuto del file ``.c`` per ``spec``."""
    user_prompt = (
        f"Implement: {spec.name}\n"
        f"Prototype: {spec.signature}\n"
        f"Description: {spec.description}\n"
        f"Allowed libc: {spec.allowed}\n"
        f"Filename: {spec.name}.c"
    )
    payload = {
        "model": model,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    request = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as resp:
        body = json.load(resp)
    message = body["choices"][0]["message"]
    content = message.get("content") or message.get("reasoning_content")
    return _strip_fences(str(content or ""))


def _strip_fences(text: str) -> str:
    """Rimuove eventuali recinzioni markdown nonostante le istruzioni."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _looks_like_c(content: str, name: str) -> bool:
    """Controlla che la risposta contenga la definizione della funzione.

    Non si richiede un ``#include``: molte funzioni di libft (es.
    ``ft_isalpha``) non ne hanno legittimamente bisogno.
    """
    return f"{name}(" in content and "{" in content and "}" in content


def main() -> int:
    """Genera tutte le funzioni; restituisce il codice di uscita."""
    try:
        model = _detect_model()
    except (urllib.error.URLError, RuntimeError) as exc:
        print(
            f"error: cannot reach LM Studio at {BASE_URL}: {exc}",
            file=sys.stderr,
        )
        return 4

    print(f"Server: {BASE_URL}  modello: {model!r}")
    print(f"Genero {len(FUNCTIONS)} funzioni in {OUTPUT_DIR}/")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    failed: list[str] = []
    total_started = time.perf_counter()
    for index, spec in enumerate(FUNCTIONS, start=1):
        started = time.perf_counter()
        print(f"[{index}/{len(FUNCTIONS)}] {spec.name} ... ", end="")
        sys.stdout.flush()
        try:
            content = _generate(model, spec)
        except Exception as exc:
            print(f"errore ({exc})")
            failed.append(spec.name)
            _save_error(spec, model, f"request failed: {exc}")
            continue
        elapsed = time.perf_counter() - started
        if not _looks_like_c(content, spec.name):
            print(f"FALLITO in {elapsed:.1f}s (non sembra un file C)")
            failed.append(spec.name)
            _save_error(spec, model, content)
            continue
        path = OUTPUT_DIR / f"{spec.name}.c"
        path.write_text(content + "\n", encoding="utf-8")
        print(f"ok in {elapsed:.1f}s")

    total = time.perf_counter() - total_started
    done = len(FUNCTIONS) - len(failed)
    print(f"\nGenerate {done}/{len(FUNCTIONS)} funzioni in {total:.0f}s.")
    if failed:
        print(f"Fallite: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


def _save_error(spec: FunctionSpec, model: str, response: str) -> None:
    """Salva la risposta non utilizzabile accanto ai file generati."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"name": spec.name, "model": model, "response": response}
    path = OUTPUT_DIR / f"{spec.name}.error.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrotto dall'utente.", file=sys.stderr)
        raise SystemExit(1)
