"""Primo passo di `index`: trova i file del corpus e li taglia in chunk."""

from pathlib import Path

from tqdm import tqdm

from src.indexer.chunker import (
    Chunk, chunk_at, markdown_bounds, python_bounds,
)

# .txt goes through the text strategy: the docs dataset cites CMakeLists.txt
BOUNDS = {
    ".py": python_bounds, ".md": markdown_bounds, ".txt": markdown_bounds,
}


def walk(
    raw_dir: str | Path,
    max_chunk_size: int,
    overlap: int = 200,
) -> list[Chunk]:
    """Taglia in chunk ogni file .py/.md/.txt sotto `raw_dir`.

    Chiamata da `build_index`. `BOUNDS` sceglie i confini per tipo di
    file, `chunk_at` crea i chunk.
    - `file_path` resta relativo alla cartella di lancio: va lanciato dalla
      radice, la moulinette vuole percorsi `data/raw/...`.
    - `newline=""` tiene i `\r\n`: gli indici coincidono col file su disco.
    - `errors="replace"`: un byte non UTF-8 non ferma tutto.

    Args:
        raw_dir: Cartella del corpus.
        max_chunk_size: Lunghezza massima di un chunk.
        overlap: Sovrapposizione delle finestre (vedi `_sub_chunk`).

    Returns:
        Tutti i chunk, file in ordine alfabetico. File illeggibili saltati.
    """
    chunks: list[Chunk] = []
    files = [p for p in sorted(Path(raw_dir).rglob("*"))
             if p.suffix.lower() in BOUNDS and p.is_file()]
    for path in tqdm(files, desc="Chunking", unit="file"):
        try:
            # newline="" keeps \r\n, so offsets index the file on disk
            with open(path, encoding="utf-8", errors="replace",
                      newline="") as f:
                content = f.read()
        except OSError as e:
            tqdm.write(f"skipping {path}: {e}")
            continue
        bounds = BOUNDS[path.suffix.lower()](content)
        chunks += chunk_at(content, str(path), bounds,
                           max_chunk_size, overlap)
    return chunks
