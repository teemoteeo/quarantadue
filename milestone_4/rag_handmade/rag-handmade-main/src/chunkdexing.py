""" Primo passo del processo: la libreria vLLM viene tagliata in chunk
("pezzi") da massimo 2000 caratteri come specificato nel subject.
Vengono usate due strategie diverse per file Python e file Markdown.
Per i file python utilizzo regole ast, secondo cui vado a cercare
dichiarazioni di primo livello(funzioni e classi) come limiti dei
vari chunk, in modo da tenere integre le strutture principali e non
tagliare funzioni a meta', mentre per i file markdown taglio i file
a quando incontro '#' che indicano titoli o sottotitoli."""

import ast
import sys
import json

from tqdm import tqdm
from pathlib import Path
from dataclasses import dataclass, asdict

OVERLAP_RATIO = 0.1
ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "data" / "processed" / "index.json"


@dataclass(frozen=True)
class Chunk:
    """Pezzo di un file."""

    content: str
    file_path: str
    first_index: int
    last_index: int


def markdown_chunking(
        content: str,
        max_size: int,
        path: str) -> list[Chunk]:
    """Funzione per il chunking di .md e .txt. Taglio all'ultimo '#' prima
    di max_size. Torna una lista di Chunk."""
    chunks: list[Chunk] = []
    start = 0
    overlap = int(max_size * OVERLAP_RATIO)
    while start < len(content):
        if start + max_size >= len(content):
            chunks.append(Chunk(content[start:len(content)],
                                path, start, len(content)))
            break
        end = content.rfind("\n#", start, start + max_size) + 1
        # +1: end punta al '#' (dopo il \n), fine di questo
        # chunk e inizio del prossimo.
        if end == 0:
            chunks.append(Chunk(content[start:start+max_size], path,
                                start, start + max_size))
            start = start + max_size - overlap
        else:
            chunks.append(Chunk(content[start:end], path, start, end))
            start = end
    return chunks


def py_chunking(
        content: str,
        max_size: int,
        path: str) -> list[Chunk]:
    """Funzione per il chunking di .py. Cerca, attraverso 'ast' tutti i nodi
    delimitati da dichiarazioni di primo livello. Taglio tutti i chunk alla
    dichiarazione piu' vicina possibile a max_size. Torna una lista di Chunk"""
    try:
        tree = ast.parse(content).body
    except (SyntaxError, ValueError):
        tree = []
    line_starts = [0]
    chunks: list[Chunk] = []
    bounds: list[int] = [0]
    char_index = 0
    overlap = int(max_size * OVERLAP_RATIO)
    for line in content.split("\n"):
        char_index += len(line) + 1
        line_starts.append(char_index)
    for node in tree:
        decorators = getattr(node, "decorator_list", [])
        lineno = min([node.lineno] + [d.lineno for d in decorators]) - 1
        bounds.append(line_starts[lineno])
    bounds.append(len(content))
    start = 0
    while start < len(content):
        if start + max_size >= len(content):
            chunks.append(Chunk(content[start:len(content)], path,
                                start, len(content)))
            break
        end = max((x for x in bounds if start < x <= start + max_size),
                  default=None)
        if end is None:
            chunks.append(Chunk(content[start:start + max_size], path,
                                start, start+max_size))
            start = start + max_size - overlap
        else:
            chunks.append(Chunk(content[start:end], path, start, end))
            start = end
    return chunks


CHUNKERS = {".py": py_chunking, ".md": markdown_chunking,
            ".txt": markdown_chunking}


def chunker(path: Path, max_size: int) -> list[Chunk]:
    """Router per capire quale funzione usare, legge i suffissi
    di ogni file e decreta se e' .py o .md/.txt e applica la
    funzione designata"""
    chunk = CHUNKERS.get(path.suffix)
    if chunk is None:
        return []
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"SKIP {path}: {e!r}", file=sys.stderr)
        return []
    return chunk(content, max_size, str(path.relative_to(ROOT)))


def indexer(chunks: list[Chunk]) -> None:
    """Crea index.json nel path indicato sul subject"""
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    index = [asdict(chunk) for chunk in chunks]
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def index(max_chunk_size: int = 2000) -> None:
    """Funzione index pronta per l'utilizzo CLI nel main"""
    path = ROOT/"data"/"raw"
    if not path.is_dir():
        raise FileNotFoundError("Path data/raw invalid!")
    if not isinstance(max_chunk_size, int) or max_chunk_size <= 0:
        raise ValueError("Chunk size is invalid!")
    chunks: list[Chunk] = []
    for f in tqdm(sorted(path.rglob("*"))):
        if f.is_file() and f.suffix in CHUNKERS:
            chunks += chunker(f, max_chunk_size)
    indexer(chunks)
    print(f"Indexing complete: {len(chunks)} chunks!"
          f"\nIndex saved in data/processed/index.json")
