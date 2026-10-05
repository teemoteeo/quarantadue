*This project has been created as part of the 42 curriculum by tcostant.*

## Description

A Retrieval-Augmented Generation (RAG) system that answers questions about the vLLM 0.10.1 codebase. It chunks and indexes the repository with BM25, retrieves the source spans most relevant to a question, and has `Qwen/Qwen3-0.6B` answer from those spans only. Retrieval quality is measured with recall@k against ground-truth source locations.

## System Architecture

```
                    index                                     search / answer
data/raw/ ──► walker ──► chunker ──► tokenize ──► BM25 ──► data/processed/index.pkl
                                                                  │
question ──► tokenize ──► BM25 scores ──► top-k MinimalSource ◄───┘
                                                  │
                        re-read file[first:last] ─┴─► prompt ──► Qwen3-0.6B ──► answer
```

| File | Role |
|------|------|
| `src/indexer.py` | Finds every `.py` / `.md` / `.txt` file under `data/raw/`, reads it with exact character offsets, cuts it with one of the two chunking strategies (below) |
| `src/retriever.py` | Tokenizer, index build + pickle (full or incremental), `Retriever.search()` in bm25 / embeddings / hybrid mode, query cache |
| `src/embedder.py` | all-MiniLM-L6-v2 sentence embeddings for the vector index (bonus) |
| `src/generator.py` | Prompt building and generation with Qwen3-0.6B (`transformers`, CPU) |
| `src/models.py` | Pydantic models exchanged between stages and written as JSON |
| `src/__main__.py` | Python Fire CLI, recall@k evaluation, top-level error handling |
| `src/api.py` | Local HTTP API (`/healthz`, `/search`, `/answer`) on the stdlib `http.server` (bonus) |
| `src/tui.py` | Interactive curses interface (extra, not in the subject): shows which chunks each question word hits, the top-k sources and the streamed answer |

The index stores `(file_path, first, last)` per chunk, the BM25 statistics, and each chunk's terms plus each file's `(mtime, size)`; the last two let `index --incremental` skip unchanged files. Chunk text is re-read from disk when the generator needs it. Measured sizes at `--max_chunk_size 2000`: `index.pkl` 39.0 MB, `embeddings.pkl` 21.3 MB (only with `--embeddings`). If the corpus changes, re-run `index`, or `index --incremental` to re-chunk only the changed files.

## Chunking Strategy

Two strategies, both producing contiguous slices of the file (`content == file[first:last]`, span ≤ `max_chunk_size`):

- **Python** — `ast.parse` gives the line of every top-level statement (a decorator counts as the start of its function/class). Those lines are the split points.
- **Markdown / text** — every `#`…`######` header line is a split point. `.txt` goes through this strategy too (the docs dataset cites `CMakeLists.txt`).

Adjacent segments are then packed greedily until the next one would exceed `max_chunk_size`, so small functions and the imports between them share a chunk. A segment larger than the limit (e.g. the ~150K-char `GPUModelRunner` class) is cut with a sliding window that ends on a newline and overlaps the previous window by 200 chars. Unparsable Python falls back to the sliding window.

Files are read with `newline=""`: Python's default newline translation turns `\r\n` into `\n` and would shift every offset in the 4 CRLF files of the corpus.

## Retrieval Method

Okapi BM25 (`rank-bm25`, default `k1=1.5`, `b=0.75`) over the chunk text **prefixed with its file path**. Tokenizer (`src/retriever.py`):

1. Extract `[A-Za-z0-9_]+` words.
2. Keep each identifier **whole** (matches a question that quotes `get_kv_cache_spec` verbatim) **and** add its `snake_case` / `camelCase` parts (matches a question that says "KV cache spec").
3. Lowercase, drop a short stopword list (including "vllm", which is in nearly every question).

A query goes through the same tokenizer; chunks are ranked by BM25 score and the top k with a non-zero score are returned.

## Performance Analysis

Measured on the public datasets with this repo's `evaluate` command (same rule as the moulinette: same file and IoU ≥ 0.05).

**Recall at `--max_chunk_size 2000` (default):**

| Dataset | @1 | @3 | @5 | @10 | Required @5 |
|---------|----|----|----|-----|-------------|
| docs (100 q) | 66.0% | 82.0% | **86.0%** | 89.0% | 80% ✅ |
| code (99 q)  | 49.5% | 73.7% | **82.8%** | 87.9% | 50% ✅ |

**Effect of chunk size on recall@5:**

| max_chunk_size | chunks | docs | code |
|----------------|--------|------|------|
| 500  | 69,996 | 82.0% | 75.8% |
| 1000 | 28,111 | 85.0% | 78.8% |
| 1500 | 18,408 | 85.0% | 80.8% |
| 2000 | 13,885 | **86.0%** | **82.8%** |

Smaller chunks split answers across chunks and dilute BM25 statistics; 2000 wins on both sets.

**What each tokenizer choice is worth (recall@5, one change at a time):**

| Variant | docs | code |
|---------|------|------|
| Shipped tokenizer | 86.0% | 82.8% |
| without file path in the chunk text | 85.0% | 76.8% |
| without identifier splitting | 84.0% | 63.6% |
| without stopword removal | 84.0% | 75.8% |
| naive `text.lower().split()` | 72.0% | 15.2% |

**Speed** (42 campus machine: Intel i7-10700, 8 cores, CPU only):

| Step | Time | Limit |
|------|------|-------|
| `index` (1,969 files → 13,885 chunks) | ~5 s | 5 min |
| `search_dataset`, docs (100 q) + code (99 q), cold start each | 3.0 s + 3.9 s | 90 s |
| `answer_dataset`, first 10 docs questions, k=10 results | 4 min 41 s (~28 s/question, model load excluded), context capped at 12,000 chars | — |

Bonus timings, measured on a different machine (Apple M5 Pro laptop, CPU only), so not comparable with the campus table above:

| Step | Time | Limit |
|------|------|-------|
| `index` (BM25 only) | 2.6 s | 5 min |
| `index --embeddings` (BM25 + 13,885 MiniLM vectors) | 19.5 s / 20.6 s (two runs) | 5 min |
| `index --embeddings --incremental`, 1 file touched (1 re-indexed, 1,846 reused) | 5.1 s | — |
| `search_dataset`, docs + code, `--no_cache` | 1.6 s + 2.1 s | 90 s |
| `search_dataset`, docs + code, same questions again (query cache hit) | 0.10 s + 0.10 s | 90 s |
| `search` one query, bm25: 1st run / 2nd run (separate processes) | 0.31 s / 0.10 s | — |
| `search` one query, `--retrieval hybrid`: 1st run / 2nd run | 2.73 s / 0.10 s | — |

## Bonus Features

Each bonus is opt-in: without its flag, the default `bm25` search returns exactly the results of the mandatory version (checked by diffing `search_dataset` outputs).

| # | Bonus | What it is | Demo |
|---|-------|------------|------|
| 1 | Semantic embeddings | `all-MiniLM-L6-v2` (CPU) vectors for every chunk, saved as `data/processed/embeddings.pkl` next to the BM25 index; cosine similarity search | `uv run python -m src index --embeddings` then `uv run python -m src search "How do I load a LoRA adapter?" --retrieval embeddings` |
| 2 | Hybrid retrieval | BM25 and embedding rankings fused with weighted Reciprocal Rank Fusion (BM25 weight 2, `LEXICAL_WEIGHT`) | `uv run python -m src search "How do I load a LoRA adapter?" --retrieval hybrid` (also on `search_dataset` and `answer`) |
| 3 | Incremental indexing | Files with unchanged `(mtime, size)` reuse their chunks, terms and vectors; only new or changed files are re-chunked and re-embedded. The result equals a full rebuild (same sources, terms and embedding matrix) | `touch data/raw/vllm-0.10.1/docs/features/lora.md && uv run python -m src index --embeddings --incremental` → `Incremental: re-indexed 1 file(s), reused 1846` |
| 4 | Caching | The index is built once and persisted (`index.pkl`), loaded only on a cache miss; query results are cached in memory and on disk in `data/processed/query_cache.json`, keyed by mode, whitespace-normalised query and k, and tied to the `(mtime, size)` of the index files, so any re-index invalidates it. Atomic writes, at most 1000 entries, a corrupt file is ignored | Run the same `search` twice (2nd run: 0.10 s, see Speed); `--no_cache` bypasses it on `search`, `search_dataset`, `answer` and `api` |
| 5 | Local HTTP API | `uv run python -m src api [--port 8000] [--retrieval hybrid]`: `GET /healthz`, `POST /search`, `POST /answer`; bodies are the subject's pydantic models, bad input gets a 4xx JSON error | see below |

```bash
uv run python -m src api --port 8000
curl -s localhost:8000/healthz
# {"status": "ok"}
curl -s -X POST localhost:8000/search -d '{"question": "How do I load a LoRA adapter?", "k": 2}'
# {"search_results": [{"question_id": "<uuid>", "question": "...", "retrieved_sources": [{"file_path": "data/raw/vllm-0.10.1/docs/features/lora.md", "first_character_index": 4695, "last_character_index": 6100}, ...]}], "k": 2}
curl -s -X POST localhost:8000/answer -d '{"question": "What HTTP endpoint loads a LoRA adapter?", "k": 3}'
# {..., "answer": "The HTTP endpoint that loads a LoRA adapter is `/v1/load_lora_adapter`."}
```

**Trade-offs (measured with `evaluate`, `--max_chunk_size 2000`):**

| Mode | docs @1 / @3 / @5 / @10 | code @1 / @3 / @5 / @10 |
|------|-------------------------|-------------------------|
| `bm25` (default) | 66.0 / 82.0 / **86.0** / 89.0 | 49.5 / 73.7 / **82.8** / 87.9 |
| `embeddings` | 37.0 / 55.0 / 60.0 / 67.0 | 18.2 / 30.3 / 32.3 / 39.4 |
| `hybrid`, equal weights | 54.0 / 76.0 / 82.0 / 91.0 | 35.4 / 61.6 / 72.7 / 85.9 |
| `hybrid`, BM25 weight 2 (shipped) | 59.0 / 80.0 / **87.0** / 90.0 | 33.3 / 63.6 / **78.8** / 88.9 |

- BM25 stays the default: hybrid gains 1 point on docs @5 and on code @10 but loses 4 points on code @5 and a lot at @1. Equal-weight RRF was worse at @5 on both sets.
- The weight was chosen among 1, 2 and 3 on the same public questions reported here, so the hybrid row is optimistic. 2 and 3 give identical results: with any BM25 weight above 75/61, every chunk in BM25's top 15 outranks every chunk found only by embeddings, so the semantic ranking just reorders BM25's candidates. That is a structural effect, not a fine-tuned value.
- `EMBED_CHARS = 500`: only the first 500 characters of a chunk are embedded, which truncates 12,818 of the 13,885 chunks. On a sample of 278 chunks, a 500-char prefix is 146 tokens (median, max 228), under MiniLM's 256-token limit, so a longer prefix is possible but untested. The truncation likely explains part of the low embedding-only recall.
- The query cache is tied to the index files and to `src/retriever.py` itself (mtime, size), not to the corpus: after editing `data/raw/`, re-run `index` before trusting cached results (it is invalidated as soon as the index is rewritten).

## Design Decisions

1. **BM25 over TF-IDF** — saturates term frequency and normalises by chunk length, so a 2000-char chunk repeating a word does not beat a focused 300-char one.
2. **Split identifiers but keep them whole** — the subject's hint: questions either paraphrase or quote code. Both forms are indexed, so both match (+19 pts code recall).
3. **File path in the indexed text** — file names are the best summary of their content (`docs/features/lora.md`); +6 pts code recall.
4. **Contiguous, packed chunks** — nothing between functions (imports, constants) is lost, and every chunk is a valid source span for the grader.
5. **Pickle for the index** — one `pickle.dump` of the BM25 object; loads in about a second. It is only ever read from `data/processed/`, which only `index` writes.
6. **Qwen3 in float32, thinking disabled** — bfloat16 matmuls are ~6× slower on CPU; `enable_thinking=False` stops the model spending its token budget on a hidden reasoning trace. Greedy decoding, 256 new tokens, a 12,000-char context budget (~3-4k tokens, well within Qwen3's window).
7. **One error boundary** — every command validates its inputs; `main()` turns any remaining exception into a one-line `Error: …` and exit code 1, so the CLI never prints a traceback.

## Challenges

- **Chunk spans vs. the 2000-char limit** — segments must be packed without ever crossing the limit, and oversized classes need a window that always moves forward (a window smaller than the overlap used to loop forever; the overlap is now capped at half the window).
- **Byte-exact offsets** — newline translation silently shifted offsets in CRLF files; fixed by reading with `newline=""`.
- **Vocabulary mismatch** — questions say "KV cache", code says `kv_cache_manager`; identifier splitting bridged it (code recall 63.6% → 82.8%).
- **CPU generation speed** — `dtype="auto"` loads Qwen3 in bfloat16, about 6× slower per answer on CPU than float32.
- **Linting the corpus** — `flake8 .` / `mypy .` also scanned the vLLM sources; `data/` is excluded in `.flake8` and `pyproject.toml`.

## Instructions

Requirements: Python ≥ 3.10, [`uv`](https://docs.astral.sh/uv/). The first `answer` downloads Qwen3-0.6B (~1.5 GB) from Hugging Face. On Linux, torch comes from the CPU-only PyTorch index.

```bash
make install      # uv sync --extra dev
make lint         # flake8 + mypy with the subject's flags
make lint-strict  # flake8 + mypy --strict
make clean        # remove caches
make run CMD='search "How do I load a LoRA adapter?" --k 5'
make debug CMD='index'   # same, under pdb
make tui                 # interactive interface (needs the index)
```

Expected layout: corpus in `data/raw/vllm-0.10.1/`, datasets in `data/datasets/{AnsweredQuestions,UnansweredQuestions}/`.

## Example Usage

```bash
# 1. Index (writes data/processed/index.pkl)
uv run python -m src index --max_chunk_size 2000

# Single query: top-k sources
uv run python -m src search "What HTTP endpoint loads a LoRA adapter?" --k 5
# data/raw/vllm-0.10.1/docs/features/lora.md [4695:6100]
# ...

# 2. Search a whole dataset (output keeps the dataset's file name)
uv run python -m src search_dataset \
    --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json \
    --k 10 \
    --save_directory data/output/search_results/UnansweredQuestions

# 3. Recall@k against the ground truth (the moulinette gives the official one)
uv run python -m src evaluate \
    --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \
    --dataset_path data/datasets/AnsweredQuestions/dataset_docs_public.json

# Single query: sources + generated answer
uv run python -m src answer "What HTTP endpoint loads a LoRA adapter?" --k 5
# ...
# The HTTP endpoint used to dynamically load a LoRA adapter in vLLM is `/v1/load_lora_adapter`.

# 4. Answer a whole search results file
uv run python -m src answer_dataset \
    --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \
    --save_directory data/output/search_results_and_answer/UnansweredQuestions
```

Optional flags: `--processed_dir` (index location: `index`, `search`, `search_dataset`, `answer`, `api`), `--raw_dir` (corpus: `index`), and for the bonuses `--embeddings` / `--incremental` (`index`), `--retrieval bm25|hybrid|embeddings` and `--no_cache` (`search`, `search_dataset`, `answer`, `api`).

## Resources

- Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (2020): https://arxiv.org/abs/2005.11401
- Robertson & Zaragoza, *The Probabilistic Relevance Framework: BM25 and Beyond* (2009)
- Manning, Raghavan, Schütze, *Introduction to Information Retrieval*, ch. 6 (tf-idf, scoring) and 11 (probabilistic IR / BM25): https://nlp.stanford.edu/IR-book/
- `rank-bm25`: https://github.com/dorianbrown/rank_bm25
- Qwen3 model card (chat template, `enable_thinking`): https://huggingface.co/Qwen/Qwen3-0.6B
- Python `ast` module: https://docs.python.org/3/library/ast.html
- Python Fire: https://github.com/google/python-fire

### AI usage

Claude Code was used to audit the code against the subject, to write the retriever, generator, CLI and the bonus features, and to run the measurements reported above (chunk-size sweep, tokenizer ablations, float32 vs bfloat16 timing). The chunking design was developed with AI assistance as well.
