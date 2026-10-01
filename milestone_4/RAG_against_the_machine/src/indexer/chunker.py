"""Come tagliare un file in chunk da indicizzare.

Un chunk è un pezzo continuo: `content == file[first:last]` e
`last - first <= max_chunk_size` (la moulinette rifiuta fonti > 2000).
1. `python_bounds` / `markdown_bounds` trovano i confini naturali
   (funzioni, classi, titoli);
2. `chunk_at` unisce sezioni vicine finché ci stanno;
3. `_sub_chunk` spezza a finestre quelle troppo lunghe.
"""

import ast
import re
from dataclasses import dataclass

HEADER_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)


@dataclass(frozen=True)
class Chunk:
    """Pezzo di un file. `content` serve solo a tokenizzare, non si salva."""

    content: str
    file_path: str
    first_character_index: int
    last_character_index: int


def _sub_chunk(
    content: str,
    file_path: str,
    start_offset: int,
    end_offset: int,
    max_chunk_size: int,
    overlap: int,
) -> list[Chunk]:
    """Copre `content[start_offset:end_offset]` con finestre sovrapposte.

    Riserva di `chunk_at` per sezioni troppo lunghe.
    - Ogni finestra finisce su un a capo, se ce n'è uno oltre `overlap`
      (prima non avanzerebbe: ciclo infinito).
    - `overlap` caratteri in comune tra finestre: una frase tagliata al
      bordo è intera in una delle due. Limitato a metà finestra, sempre
      per garantire che si avanzi.
    - Finestre di soli spazi saltate.

    Raises:
        ValueError: Se `max_chunk_size < 1`.
    """
    if max_chunk_size < 1:
        raise ValueError(f"max_chunk_size must be >= 1, got {max_chunk_size}")
    # an overlap >= the window would never move forward
    overlap = min(overlap, max_chunk_size // 2)
    chunks: list[Chunk] = []
    pos = start_offset
    while pos < end_offset:
        chunk_end = min(pos + max_chunk_size, end_offset)
        if chunk_end < end_offset:
            cut = content.rfind("\n", pos, chunk_end)
            # cut past the overlap, otherwise the window would not advance
            if cut > pos + overlap:
                chunk_end = cut + 1
        text = content[pos:chunk_end]
        if text.strip():
            chunks.append(Chunk(text, file_path, pos, chunk_end))
        if chunk_end == end_offset:
            break
        pos = chunk_end - overlap
    return chunks


def chunk_at(
    content: str,
    file_path: str,
    bounds: list[int],
    max_chunk_size: int,
    overlap: int,
) -> list[Chunk]:
    """Taglia il file ai confini `bounds` e unisce le sezioni piccole.

    Chiamata da `walk`. Tiene aperto un chunk e ci aggiunge sezioni finché
    resta sotto `max_chunk_size`, poi lo chiude. Unire serve perché chunk
    di poche righe danno poche parole a BM25 e poco contesto a Qwen3.
    Una sezione troppo lunga da sola va a `_sub_chunk`.

    Returns:
        Chunk che coprono tutto il file, in ordine.
    """
    edges = sorted({0, len(content), *bounds})
    chunks: list[Chunk] = []
    start = end = 0
    for edge in edges[1:]:
        if edge - start > max_chunk_size:
            chunks += _sub_chunk(content, file_path, start, end,
                                 max_chunk_size, overlap)
            start = end
            if edge - start > max_chunk_size:
                chunks += _sub_chunk(content, file_path, start, edge,
                                     max_chunk_size, overlap)
                start = edge
        end = edge
    chunks += _sub_chunk(content, file_path, start, end,
                         max_chunk_size, overlap)
    return chunks


def python_bounds(content: str) -> list[int]:
    """Indici dove inizia ogni istruzione di primo livello di un .py.

    Usa `ast` e non una regex: è sicuro anche con `def` dentro stringhe.
    I decoratori restano con la loro funzione. `ast` dà righe, quindi
    `line_starts` le traduce in indici (split su `"\n"`: `\r\n` vale 2,
    come nel file vero).

    Returns:
        Indici, o [] se non è Python valido (si taglia solo a finestre).
    """
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError):
        return []
    line_starts = [0]
    for line in content.split("\n"):
        line_starts.append(line_starts[-1] + len(line) + 1)
    bounds = []
    for node in tree.body:
        decorators = getattr(node, "decorator_list", [])
        lineno = min([node.lineno] + [d.lineno for d in decorators])
        bounds.append(line_starts[lineno - 1])
    return bounds


def markdown_bounds(content: str) -> list[int]:
    """Indici delle righe di titolo Markdown (da `#` a `######`).

    Ogni titolo apre una sezione: buon punto di taglio. Usata per .md e .txt.
    """
    return [m.start() for m in HEADER_RE.finditer(content)]


if __name__ == "__main__":
    src = "import os\n\n@dec\ndef f():\n    pass\n" + "x = 1\n" * 1000
    md = "# a\n" + "b\n" * 3000
    assert python_bounds(src)[:2] == [0, 11]
    for text, bounds in ((src, python_bounds(src)), (md, markdown_bounds(md))):
        cs = chunk_at(text, "t", bounds, 200, 20)
        assert cs[0].first_character_index == 0
        assert cs[-1].last_character_index == len(text)
        for c in cs:
            assert c.content == text[c.first_character_index:
                                     c.last_character_index]
            assert len(c.content) <= 200
        for a, b in zip(cs, cs[1:]):
            assert b.first_character_index <= a.last_character_index
    # a long line right after a newline must not loop forever
    assert chunk_at("a\n" + "x" * 5000, "t", [], 2000, 200)
    # neither must a window smaller than the overlap
    assert chunk_at("x" * 5000, "t", [], 100, 200)
    # CRLF: offsets must index the raw text, not a newline-translated one
    crlf = "import os\r\n\r\ndef f():\r\n    pass\r\n"
    assert crlf[python_bounds(crlf)[1]:].startswith("def f")
    print("ok")
