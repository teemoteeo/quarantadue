"""Interfaccia interattiva (`tui`, extra fuori subject) in `curses`.

Mostra la pipeline mentre lavora: ogni parola della domanda accende i
chunk che la contengono (una griglia braille, un punto per chunk), BM25
sceglie i top k, Qwen3 scrive la risposta in streaming.
"""

import curses
import os
import sys
import textwrap
import time
from collections import Counter
from threading import Thread
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from src.models import MinimalSource
from src.retriever import WORD_RE, Retriever, read_source, tokenize

if TYPE_CHECKING:
    from src.generator import Generator

QUESTIONS = (
    "What HTTP endpoint is used to dynamically load a LoRA adapter in vLLM?",
    "What command can be used to evaluate the accuracy of a quantized model"
    " using lm_eval with vLLM?",
    "What method does vLLM's LLM class provide for generating embedding "
    "vectors from prompts?",
    "What hardware platforms does vLLM support?",
    "What are the differences between mm_kwargs and tok_kwargs when using "
    "the _call_hf_processor method in vLLM multimodal processing?",
    "Where can I find information about using generative models in vLLM?",
    "How is the number of placeholder feature tokens for an image "
    "calculated in vLLM's multimodal implementation?",
    "What parallelism strategy does vLLM support for large-scale deployment"
    " of Mixture of Experts models?",
    "How do you achieve reproducible results in vLLM?",
    "Where can I find vLLM setup and installation instructions for Google "
    "TPU?",
    "What parameter does vLLM set according to different quantization "
    "schemes to support weight quantization in linear layers?",
    "What is the main configuration object that is passed around in vLLM's "
    "class hierarchy?",
    "How do you build and run a vLLM Docker image for s390x CPU "
    "architecture?",
    "What interface should a multimodal model class inherit from in vLLM?",
    "What is stored in the logits array during the qk_max calculation in "
    "vLLM's paged attention implementation?",
    "How do you use GPTQModel quantized models with vLLM's Python API?",
    "How can you manually set the attention backend in vLLM?",
    "What is the fastest matrix multiplication kernel in vLLM's torch "
    "compile autotuning for an 8x2048 by 2048x3072 matrix multiplication?",
    "How do you pass audio inputs to vLLM for multimodal inference?",
    "What are the key capabilities of Ray Serve LLM for vLLM deployment?",
    "How can you view Nsight Systems profiles in vLLM?",
    "What quantization parameter should be specified when loading a Quark "
    "quantized model in vLLM?",
    "How do you enable GPUDirect RDMA in vLLM using Docker?",
    "What git commit should I checkout when installing Triton flash "
    "attention for ROCm with vLLM?",
    "What is the purpose of vLLM's plugin system?",
    "What activation formats does the fused batched MoE layer return in "
    "vLLM?",
    "What are the default values for FP8_MIN and FP8_MAX constants in "
    "vLLM's triton_flash_attention module?",
    "What determines whether vLLM's sampler returns Pythonized results or "
    "deferred Pythonization arguments?",
    "What's the default value of trust_remote_code in vLLM's LLM class "
    "constructor?",
    "What determines the values in cudagraph_inputs_embeds when capturing "
    "CUDA graph shapes in vLLM's ModelRunner?",
    "What conditions must be met for vLLM's ModelRunner to use CUDA graphs "
    "instead of the regular model?",
    "What is the default timeout value for vLLM RPC operations?",
    "What does the Gemma3ForCausalLM constructor assert about the "
    "tie_word_embeddings configuration?",
    "What value is passed for ngroups when has_groups is False in the "
    "_bmm_chunk_fwd_kernel call?",
    "What is the default cudagraph_support value for "
    "TritonAttentionMetadataBuilder?",
    "What does the get_num_new_matched_tokens method in NIXLConnector "
    "return?",
    "What types are supported as containers in vLLM's JSONTree type "
    "definition?",
    "What value does _MAX_IMAGE_SIZE use in vLLM's keye model for "
    "determining the image size with most features?",
    "What is the default language value when None is passed to Whisper's "
    "validate_language method?",
    "What condition determines whether batch reordering is skipped in "
    "GPUModelRunner's update_batch_order method?",
    "What are the default values for tensor fields in vLLM's "
    "AiterMLAMetadata class?",
    "What error is raised when full attention group ids and other attention"
    " group ids interleave in HybridKVCacheCoordinator?",
    "What is the shape and structure of the array returned by the KV cache "
    "mapping metadata computation function in TPUModelRunner?",
    "What is the default value of the z parameter in the "
    "selective_state_update function call in vLLM's mamba_mixer2.py?",
    "What block size divisibility requirement does HybridKVCacheCoordinator"
    " enforce when caching is enabled?",
    "What is the default value for min_dynamic_patch parameter in "
    "NemotronVL model initialization?",
    "What exception is raised when pixel_values has incorrect number of "
    "channels in InternS1VisionEmbeddings forward method?",
    "What does the HunyuanA13BReasoningParser return when reasoning_content"
    " or response_content has zero length?",
    "What are the input tensor shapes and types used in "
    "MiddleAllReduceRMSNormPattern's get_inputs method?",
    "What are all the registered KV connector names in vLLM's "
    "KVConnectorFactory?",
)
KS = (1, 3, 5, 10)
STEP_MS = 300  # how long each question word stays lit
HELP = ("Enter run | Tab questions | Up/Down source | ^P words/source | "
        "PgUp/PgDn scroll | ^K k | ^U clear | Esc quit")
MIN_H, MIN_W = 20, 80
# chunk states; the highest one wins when chunks share a braille cell
OFF, SEEN, NOW, TOP, SEL = 0, 1, 2, 3, 4
LABEL_W = 20  # group names left of the grid
GRID_MAX = 82  # grid cells per row; wider only to keep 1 dot = 1 chunk
SRC_MIN = 40  # sources column never narrower than this
ANSWER_MIN = 7  # rows always left to the answer box, borders included
TITLE = "RAG AGAINST THE MACHINE"
# 4-pixel-high font for the title: two pixel rows per text row
FONT = {
    "A": ".#.|#.#|###|#.#", "C": ".##|#..|#..|.##", "E": "###|##.|#..|###",
    "G": ".##|#..|#.#|.##", "H": "#.#|###|#.#|#.#", "I": "###|.#.|.#.|###",
    "M": "#...#|##.##|#.#.#|#...#", "N": "#..#|##.#|#.##|#..#",
    "R": "##.|#.#|##.|#.#", "S": ".##|##.|..#|##.", "T": "###|.#.|.#.|.#.",
    " ": "..|..|..|..",
}
HALF = {(False, False): " ", (True, False): "\u2580",
        (False, True): "\u2584", (True, True): "\u2588"}
# braille dot bit for the j-th chunk of a cell, filled left-right, top-down
DOT_BITS = np.array([0x01, 0x08, 0x02, 0x10, 0x04, 0x20, 0x40, 0x80])


def wrap(text: str, width: int) -> list[str]:
    """Va a capo a `width` tenendo righe vuote e indentazione."""
    lines: list[str] = []
    for line in text.expandtabs(4).splitlines():
        lines += textwrap.wrap(line, width, replace_whitespace=False,
                               drop_whitespace=False) or [""]
    return lines


def braille(state: NDArray[np.int8],
            per: int) -> tuple[str, NDArray[np.int8]]:
    """Stati dei chunk -> caratteri braille (8 punti, `per` chunk a punto).

    Restituisce anche lo stato più alto di ogni carattere, per il colore.
    """
    dots = np.maximum.reduceat(state, np.arange(0, len(state), per))
    cells = np.full(-(-len(dots) // 8) * 8, -1, dtype=np.int8)
    cells[:len(dots)] = dots
    grid = cells.reshape(-1, 8)
    level = grid.max(axis=1)
    bits = np.where(level > OFF, ((grid > OFF) * DOT_BITS).sum(axis=1),
                    ((grid >= OFF) * DOT_BITS).sum(axis=1))
    return "".join(chr(0x2800 + int(b)) for b in bits), level


def banner(text: str) -> list[str]:
    """`text` in `FONT`, due righe di pixel per riga di testo (▀ ▄ █)."""
    rows = [""] * 4
    for ch in text:
        for r, bits in enumerate(FONT[ch].split("|")):
            rows[r] += bits + "."
    return ["".join(HALF[(a == "#", b == "#")] for a, b in zip(top, bot))
            .rstrip() for top, bot in zip(rows[::2], rows[1::2])]


def grid_rows(sizes: list[int], width: int, per: int) -> int:
    """Righe occupate dalla griglia: ogni gruppo parte su una riga nuova."""
    def ceil(a: int, b: int) -> int:
        return -(-a // b)

    return sum(ceil(ceil(ceil(n, per), 8), width) for n in sizes)


def fit_per(sizes: list[int], width: int, rows: int) -> int:
    """Il minimo di chunk per punto che fa stare la griglia in `rows`."""
    per = 1
    # each group needs a row whatever per is: stop there on tiny screens
    while grid_rows(sizes, width, per) > max(rows, len(sizes)):
        per += 1
    return per


def group_chunks(paths: list[str], split: float = 0.25,
                 keep: float = 0.02) -> list[tuple[str, NDArray[np.intp]]]:
    """Raggruppa i chunk per cartella, per le righe della griglia.

    Una cartella con più di `split` dei chunk si divide nelle sue
    sottocartelle; i gruppi sotto `keep` finiscono in "other".
    """
    dirs = [os.path.dirname(p) for p in paths]
    root = os.path.commonpath(dirs)
    parts = [os.path.relpath(d, root).split(os.sep) for d in dirs]
    top = [p[0] if p[0] != "." else "(root)" for p in parts]
    big = {k for k, n in Counter(top).items() if n > split * len(paths)}
    keys = [f"{t}/{p[1]}" if t in big and len(p) > 1 else t
            for t, p in zip(top, parts)]
    sizes = Counter(keys)
    keys = [k if sizes[k] >= keep * len(paths)
            else f"{t}/other" if t in big else "other"
            for k, t in zip(keys, top)]
    sizes = Counter(keys)
    names = sorted(sizes, key=lambda k: (k.endswith("other"), -sizes[k]))
    arr = np.array(keys)
    return [(k, np.flatnonzero(arr == k)) for k in names]


class App:
    """Stato della TUI, disegno e tasti. Un'istanza per sessione."""

    def __init__(self, scr: "curses.window", retriever: Retriever) -> None:
        self.scr = scr
        self.retriever = retriever
        self.generator: "Generator | None" = None
        self.worker: Thread | None = None  # streams the answer
        self.error: Exception | None = None
        self.pieces = 0
        self.started = 0.0
        self.chunk_of = {s: i for i, s in enumerate(retriever.sources)}
        paths = [p for p, _, _ in retriever.sources]
        self.root = os.path.commonpath([os.path.dirname(p) for p in paths])
        self.groups = group_chunks(paths)
        self.group_of = np.zeros(len(paths), dtype=np.intp)
        self.pos_of = np.zeros(len(paths), dtype=np.intp)  # in its group
        for g, (_, ix) in enumerate(self.groups):
            self.group_of[ix], self.pos_of[ix] = g, np.arange(len(ix))
        self.state = np.zeros(len(retriever.sources), dtype=np.int8)
        self.query = ""
        self.marks: list[tuple[int, int, int]] = []  # query spans + attr
        self.words: list[tuple[str, int]] = []  # chunks per word, -1 = skip
        self.k = 5
        self.sources: list[MinimalSource] = []
        self.scores: list[float] = []  # BM25 score of each source
        self.sel = 0
        self.answer = ""
        self.loading = False  # Qwen3 weights being loaded
        self.show_source = False  # beside the grid: source text, not words
        self.src_scroll = 0
        self.scroll = 0
        self.follow = True  # keep the streaming answer's tail in view
        self.picking = False
        self.pick = 0
        self.status = f"Index loaded: {len(retriever.sources)} chunks"
        grey = curses.has_colors() and curses.COLORS >= 256
        if curses.has_colors():
            curses.use_default_colors()
            # 1 off, 2 seen: dark and mid grey, or plain dim/normal
            for pair, color in enumerate((237 if grey else -1,
                                          250 if grey else -1,
                                          curses.COLOR_YELLOW,
                                          curses.COLOR_GREEN,
                                          curses.COLOR_MAGENTA), 1):
                curses.init_pair(pair, color, -1)
        self.attr = {OFF: curses.color_pair(1) if grey else curses.A_DIM,
                     SEEN: curses.color_pair(2),
                     NOW: curses.color_pair(3) | curses.A_BOLD,
                     TOP: curses.color_pair(4) | curses.A_REVERSE
                     | curses.A_BOLD,
                     SEL: curses.color_pair(5) | curses.A_REVERSE
                     | curses.A_BOLD}
        # the word being read has the color of the chunks it lights up
        self.word_attr = self.attr[NOW] | curses.A_REVERSE
        self.title = banner(TITLE)

    def put(self, y: int, x: int, text: str, attr: int = 0) -> None:
        h, w = self.scr.getmaxyx()
        if 0 <= y < h and 0 <= x < w:
            try:
                self.scr.addnstr(y, x, text, w - x, attr)
            except curses.error:  # writing the bottom-right cell raises
                pass

    def rule(self, y: int, x: int, width: int, title: str) -> None:
        self.put(y, x, f"-- {title} ".ljust(width, "-")[:width],
                 curses.A_DIM)

    def draw(self) -> None:
        self.scr.erase()
        h, w = self.scr.getmaxyx()
        if h < MIN_H or w < MIN_W:
            self.put(0, 0, f"Terminal too small (min {MIN_W}x{MIN_H})")
            self.scr.refresh()
            return
        top = self.draw_title(w)
        cursor = self.draw_query(top, w)
        self.put(top + 4, 0, self.status[:w - 1], curses.A_DIM)
        self.put(h - 1, 0, HELP[:w - 1], curses.A_DIM)
        # grid on the left, sources on its right, answer below both. The
        # grid is exactly as tall as it needs; it widens past GRID_MAX
        # (squeezing the sources) only to keep 1 dot = 1 chunk
        y = top + 6  # first grid row
        sizes = [len(ix) for _, ix in self.groups]
        widest = w - LABEL_W - 1 - SRC_MIN
        for grid_w in (min(GRID_MAX, widest), widest):
            grid_w = max(24, grid_w)
            per = fit_per(sizes, grid_w, h - y - 1 - ANSWER_MIN)
            if per == 1:
                break
        mid_h = grid_rows(sizes, grid_w, per)
        self.draw_grid(y, grid_w, per)
        x = LABEL_W + grid_w
        for row in range(y - 1, y + mid_h):
            self.put(row, x, "|", curses.A_DIM)
        self.draw_sources(y - 1, x + 2, w - x - 2, mid_h + 1)
        self.draw_panel(y + mid_h, h - 1 - y - mid_h, w)
        if self.picking:
            self.draw_picker(y, h - 1 - y, w)
        self.scr.move(*cursor)
        self.scr.refresh()

    def draw_title(self, w: int) -> int:
        info = f"k={self.k}  BM25 + Qwen3-0.6B"
        if len(self.title[0]) + len(info) + 4 > w:  # no room: one-row bar
            self.put(0, 0, f" RAG against the machine  {info} ".ljust(w),
                     curses.A_REVERSE)
            return 2  # title + a blank row
        for i, line in enumerate(self.title):
            self.put(i, 1, line, self.attr[NOW])
        self.put(len(self.title) - 1, w - len(info) - 1, info, curses.A_DIM)
        return len(self.title) + 1  # title + a blank row

    def draw_query(self, y: int, w: int) -> tuple[int, int]:
        x = 0
        self.put(y + 2, x + 2, " Tab ", curses.A_REVERSE)
        self.put(y + 2, x + 8, "to browse 50 sample questions",
                 self.attr[SEEN])
        if not self.query:
            self.put(y, x, ">", curses.A_BOLD)
            self.put(y, x + 2, "Type a question about vLLM and press Enter",
                     self.attr[OFF])
            return y, x + 2
        width = w - x - 3
        start = max(0, len(self.query) - 2 * width)  # keep the tail
        attrs = [curses.A_BOLD] * len(self.query)
        for a, b, attr in self.marks:
            attrs[a:b] = [attr] * (b - a)
        self.put(y, x, ">", curses.A_BOLD)
        for i in range(start, len(self.query)):
            j = i - start
            self.put(y + j // width, x + 2 + j % width, self.query[i],
                     attrs[i])
        j = min(len(self.query) - start, 2 * width - 1)
        return y + j // width, x + 2 + j % width

    def draw_grid(self, y: int, width: int, per: int) -> None:
        state = self.state.copy()
        top = [self.chunk_of[(s.file_path, s.first_character_index,
                              s.last_character_index)]
               for s in self.sources]
        if top:
            state[top[self.sel]] = SEL
        scale = "1 dot = 1 chunk" if per == 1 else f"1 dot = {per} chunks"
        self.rule(y - 1, 0, LABEL_W + width,
                  f"retrieval: {len(state)} chunks in "
                  f"{len(self.groups)} folders, {scale}")
        first_row = []
        row = y
        for name, ix in self.groups:
            chars, level = braille(state[ix], per)
            self.put(row, 0, name[-(LABEL_W - 1):].rjust(LABEL_W - 1),
                     self.attr[int(level.max())])
            for i, ch in enumerate(chars):
                self.put(row + i // width, LABEL_W + i % width, ch,
                         self.attr[int(level[i])])
            first_row.append(row)
            row += -(-len(chars) // width)
        # winners sharing or touching a cell spill right, "/"-separated:
        # "2/3/4/5", never "2345"
        spots = sorted((int(self.group_of[i]),
                        int(self.pos_of[i]) // per // 8, rank)
                       for rank, i in enumerate(top))
        last = (-1, -1)  # group and last cell written
        for g, cell, rank in spots:
            text = str(rank + 1)
            attr = self.attr[SEL if rank == self.sel else TOP]
            if g == last[0] and cell <= last[1] + 1:
                cell, text = last[1] + 1, "/" + text
            for j, ch in enumerate(text):  # "10" may wrap to the next row
                c = cell + j
                self.put(first_row[g] + c // width, LABEL_W + c % width, ch,
                         self.attr[TOP] if ch == "/" else attr)
            last = (g, cell + len(text) - 1)

    def draw_sources(self, y: int, x: int, width: int, rows: int) -> None:
        self.rule(y, x, width, "sources: span, chars, BM25 (Up/Down)")
        rows -= 1
        if not self.sources:
            self.put(y + 1, x, "none yet", curses.A_DIM)
        # sources first; the words, or the selected source, fill the rest
        n = min(len(self.sources), rows)
        if self.show_source and self.sources:
            self.draw_source(y + 1 + n, x, width, rows - n)
        else:
            self.draw_words(y + 1 + n, x, width, rows - n)
        rows = n
        top = max(0, self.sel - rows + 1)
        for i, s in enumerate(self.sources[top:top + rows], top):
            spec = (f"{os.path.relpath(s.file_path, self.root)}"
                    f" [{s.first_character_index}:"
                    f"{s.last_character_index}]")
            size = (f" {s.last_character_index - s.first_character_index:>4}"
                    f" {self.scores[i]:>5.1f}")
            room = max(1, width - 3 - len(size))
            if len(spec) > room:  # cut the path's head, keep span + size
                spec = "…" + spec[-(room - 1):]
            self.put(y + 1 + i - top, x,
                     f"{i + 1:>2} {spec.ljust(room)}{size}"[:width],
                     self.attr[SEL if i == self.sel else TOP])

    def draw_words(self, y: int, x: int, width: int, rows: int) -> None:
        if not self.words or rows < 3:
            return
        self.rule(y + 1, x, width, "chunks containing each word (^P source)")
        for i, (word, n) in enumerate(self.words[:rows - 2]):
            count = "stopword, skipped" if n < 0 else f"{n:>6} chunks"
            self.put(y + 2 + i, x,
                     f"{word[:width - len(count) - 1]:<{width - len(count)}}"
                     f"{count}"[:width],
                     curses.A_DIM if n < 0 else self.attr[SEEN])

    def draw_source(self, y: int, x: int, width: int, rows: int) -> None:
        if rows < 3:
            return
        s = self.sources[self.sel]
        try:
            lines = wrap(read_source(s), width)
        except OSError as e:
            lines = [f"Cannot read source: {e}"]
        inner = rows - 2
        self.src_scroll = max(0, min(self.src_scroll, len(lines) - inner))
        shown = lines[self.src_scroll:self.src_scroll + inner]
        self.rule(y + 1, x, width,
                  f"source {self.sel + 1}, lines {self.src_scroll + 1}-"
                  f"{self.src_scroll + len(shown)}/{len(lines)} (^P words)")
        for i, line in enumerate(shown):
            self.put(y + 2 + i, x, line[:width])

    def draw_panel(self, y: int, rows: int, w: int) -> None:
        inner, text_w = rows - 2, w - 4  # inside the box borders
        attr, text_attr = self.attr[TOP] & ~curses.A_REVERSE, 0
        title = "Answer"
        hint = ("Loading Qwen3..." if self.loading else
                "Qwen3 is reading the sources, the answer starts soon..."
                if self.worker else "Press Enter to retrieve sources, "
                "then Qwen3 answers from them.")
        if not self.answer:
            text_attr = self.attr[SEEN]
        lines = wrap(self.answer or hint, text_w)
        if self.follow:
            self.scroll = len(lines)
        self.scroll = max(0, min(self.scroll, len(lines) - inner))
        shown = lines[self.scroll:self.scroll + inner]
        if len(lines) > inner:
            title += (f"  lines {self.scroll + 1}-"
                      f"{self.scroll + len(shown)} of {len(lines)}")
        self.put(y, 0, "\u250c" + "\u2500" * (w - 2) + "\u2510", attr)
        self.put(y, 2, f" {title} "[:w - 4], attr | curses.A_BOLD)
        for i in range(inner):
            self.put(y + 1 + i, 0, "\u2502", attr)
            self.put(y + 1 + i, w - 1, "\u2502", attr)
        for i, line in enumerate(shown):
            self.put(y + 1 + i, 2, line, text_attr)
        self.put(y + rows - 1, 0, "\u2514" + "\u2500" * (w - 2) + "\u2518",
                 attr)

    def draw_picker(self, y: int, rows: int, w: int) -> None:
        self.rule(y, 0, w, "pick a question (Enter run, Esc back)")
        rows -= 1
        top = max(0, self.pick - rows + 1)
        for i in range(rows):
            n = top + i
            text = (f"    {n + 1:>2}. {QUESTIONS[n]}" if n < len(QUESTIONS)
                    else "")
            self.put(y + 1 + i, 0, text[:w - 1].ljust(w - 1),
                     curses.A_REVERSE if n == self.pick else 0)

    def retrieve(self) -> bool:
        query = self.query.strip()
        self.query, self.answer, self.show_source = query, "", False
        self.state[:] = OFF
        self.sources, self.scores, self.marks, self.sel = [], [], [], 0
        self.words = []
        self.scroll, self.follow = 0, True
        if not query:
            self.status = "Empty query"
            return False
        docs = self.retriever.bm25.doc_freqs  # one term->count per chunk
        for m in WORD_RE.finditer(query):
            terms = tokenize(m.group())
            if not terms:  # stopword: BM25 ignores it, so dim it
                self.marks.append((m.start(), m.end(), curses.A_DIM))
                self.words.append((m.group(), -1))
                continue
            self.state[self.state == NOW] = SEEN
            hit = np.fromiter((any(t in d for t in terms) for d in docs),
                              bool, len(docs))
            self.state[hit] = NOW
            self.marks = self.seen_marks()
            self.marks.append((m.start(), m.end(), self.word_attr))
            self.words.append((m.group(), int(hit.sum())))
            self.status = f"'{m.group()}' is in {int(hit.sum())} chunks"
            self.draw()
            curses.napms(STEP_MS)
        self.state[self.state == NOW] = SEEN
        self.marks = self.seen_marks()
        self.sources = self.retriever.search(query, self.k)
        # ponytail: scores BM25 twice (here + search), ~ms on this corpus
        scores = self.retriever.bm25.get_scores(tokenize(query))
        for s in self.sources:
            i = self.chunk_of[(s.file_path, s.first_character_index,
                               s.last_character_index)]
            self.state[i] = TOP
            self.scores.append(float(scores[i]))
        self.status = (f"{int((self.state > OFF).sum())} chunks share a word"
                       f" with the question, BM25 kept the top "
                       f"{len(self.sources)}" if self.sources
                       else "No chunk shares a word with the question")
        return bool(self.sources)

    def seen_marks(self) -> list[tuple[int, int, int]]:
        # a read word stays yellow, minus the reverse of the current one;
        # dimmed stopwords stay dim
        return [(a, b, self.attr[NOW] if attr == self.word_attr else attr)
                for a, b, attr in self.marks]

    def generate(self) -> None:
        if self.generator is None:
            self.status = "Loading Qwen3 (first time can take a while)..."
            self.loading = True
            self.draw()
            from src.generator import Generator  # torch import is slow
            try:
                self.generator = Generator()
            finally:
                self.loading = False
        generator, query, sources = self.generator, self.query, self.sources
        self.error, self.pieces = None, 0
        self.started = time.monotonic()

        def work() -> None:
            try:
                for piece in generator.stream(query, sources):
                    self.answer += piece
                    self.pieces += 1
            except Exception as e:  # shown by tick()
                self.error = e

        self.worker = Thread(target=work, daemon=True)
        self.worker.start()

    def tick(self) -> None:
        if self.worker is None:
            return
        if self.worker.is_alive():
            self.status = (f"Qwen3 is writing... {self.pieces} pieces "
                           "(you can browse the sources meanwhile)")
            return
        self.worker = None
        self.answer = self.answer.strip()
        self.status = (f"Error: {type(self.error).__name__}: {self.error}"
                       if self.error else
                       f"Answered in {time.monotonic() - self.started:.1f} s"
                       f" ({self.pieces} pieces)")

    def run(self) -> None:
        if self.worker is not None:
            return  # one answer at a time
        if self.retrieve():
            self.draw()
            curses.napms(4 * STEP_MS)  # let the top k sink in
            self.generate()

    def handle_picker(self, key: "str | int") -> None:
        if key in ("\x1b", "\t"):
            self.picking = False
        elif key == curses.KEY_UP:
            self.pick = max(0, self.pick - 1)
        elif key == curses.KEY_DOWN:
            self.pick = min(len(QUESTIONS) - 1, self.pick + 1)
        elif key in ("\n", "\r", curses.KEY_ENTER):
            self.picking, self.query = False, QUESTIONS[self.pick]
            self.run()

    def handle(self, key: "str | int") -> bool:
        if self.picking:
            self.handle_picker(key)
        elif key == "\x1b":
            return False
        elif key in ("\n", "\r", curses.KEY_ENTER):
            self.run()
        elif key == "\t" and self.worker is None:
            self.picking = True
        elif key == "\x10":
            self.show_source, self.src_scroll = not self.show_source, 0
        elif key == "\x0b":
            self.k = KS[(KS.index(self.k) + 1) % len(KS)]
            self.status = f"k = {self.k}, press Enter to run again"
        elif key == "\x15":
            self.query, self.marks = "", []
        elif key in ("\x7f", "\b", curses.KEY_BACKSPACE):
            self.query, self.marks = self.query[:-1], []
        elif key == curses.KEY_UP and self.sel > 0:
            self.sel, self.src_scroll = self.sel - 1, 0
        elif key == curses.KEY_DOWN and self.sel < len(self.sources) - 1:
            self.sel, self.src_scroll = self.sel + 1, 0
        elif key == curses.KEY_NPAGE and self.show_source:
            self.src_scroll += 10  # draw_source clamps it
        elif key == curses.KEY_PPAGE and self.show_source:
            self.src_scroll = max(0, self.src_scroll - 10)
        elif key == curses.KEY_NPAGE:
            self.scroll += 10  # draw_panel clamps it
        elif key == curses.KEY_PPAGE:
            self.scroll, self.follow = max(0, self.scroll - 10), False
        elif isinstance(key, str) and key.isprintable():
            self.query, self.marks = self.query + key, []
        return True

    def loop(self) -> None:
        while True:
            self.tick()
            self.draw()
            # poll while streaming so the answer keeps flowing in
            self.scr.timeout(50 if self.worker else -1)
            try:
                key = self.scr.get_wch()
            except curses.error:  # timeout, no key
                continue
            try:
                if not self.handle(key):
                    return
            except Exception as e:  # keep the TUI alive on any failure
                self.status = f"Error: {type(e).__name__}: {e}"


def run_tui(processed_dir: str) -> None:
    """Carica l'indice e avvia `App` in curses, con stderr silenziato."""
    retriever = Retriever(processed_dir)  # fail before touching the tty

    def main(scr: "curses.window") -> None:
        curses.set_escdelay(25)
        App(scr, retriever).loop()

    # libraries (HF Hub warnings, tqdm bars) write to stderr, which would
    # land on top of the screen: silence fd 2 while curses owns it
    sys.stderr.flush()
    saved = os.dup(2)
    with open(os.devnull, "w") as null:
        os.dup2(null.fileno(), 2)
    try:
        curses.wrapper(main)
    finally:
        os.dup2(saved, 2)
        os.close(saved)


if __name__ == "__main__":
    assert len(QUESTIONS) == 50 == len(set(QUESTIONS))
    assert wrap("ab\n\ncdef", 2) == ["ab", "", "cd", "ef"]
    chars, level = braille(np.array([OFF] * 9 + [NOW], dtype=np.int8), 1)
    assert (chars, level.tolist()) == ("\u28ff\u2808", [OFF, NOW])
    chars, level = braille(np.zeros(20, dtype=np.int8), 3)
    assert chars == "\u287f"  # 7 dots of 3 chunks each
    assert grid_rows([800, 8], 10, 1) == 11 and grid_rows([800], 10, 2) == 5
    assert banner("A ") == ["\u2584\u2580\u2584", "\u2588\u2580\u2588"]
    assert fit_per([800, 8], 10, 11) == 1 and fit_per([800, 8], 10, 6) == 2
    assert fit_per([800, 8], 10, 1) == 10  # one row per group at least
    paths = ["r/a/x/f.py"] * 60 + ["r/a/y/f.py"] * 30 + ["r/b/f.py"] * 9 \
        + ["r/c.md"]
    assert [(n, len(ix)) for n, ix in group_chunks(paths, keep=0.05)] == [
        ("a/x", 60), ("a/y", 30), ("b", 9), ("other", 1)]
    print("ok")
