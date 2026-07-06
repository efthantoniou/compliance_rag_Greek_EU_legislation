# Compliance RAG — Greek & EU Legislation

A fully local Retrieval-Augmented Generation system over Greek translations of EU
legislation. It ingests the [MultiEURLEX](https://huggingface.co/datasets/nlpaueb/multi_eurlex)
corpus, stores chunks in **SurrealDB** (vector + BM25 full-text indexes), retrieves
with a **hybrid search + cross-encoder reranker**, and answers questions through
**pydantic-ai** agents backed by a local **llama.cpp** server. A **FastAPI** backend
streams answers to a **Next.js** frontend, and a CLI-driven **eval harness** measures
retrieval and answer quality.

Nothing leaves your machine: the LLM, embeddings, reranker, and vector store all run
locally.

---

## What it does

- **Ask** — natural-language questions about Greek/EU legislation, answered with
  `[celex_id]` citations. If nothing relevant is retrieved, the agent says so rather
  than guessing.
- **Check** — paste a policy document; the agent extracts its topics and surfaces the
  closest matching regulation(s) for each. It surfaces relevant law only — it never
  declares a document compliant or non-compliant.
- **Search** — raw hybrid retrieval, no LLM, for inspecting what the index returns.
- **Evaluate** — generate ground-truth Q&A from the corpus and score the RAG against
  it, including a deterministic retrieval-hit-rate metric.

### How retrieval works

1. **Chunking** — documents are split on paragraph boundaries and packed to a
   480-token budget (the embedding model truncates at 512), preserving structure.
2. **Embedding** — `intfloat/multilingual-e5-base` (768-dim), stored in SurrealDB
   with an HNSW index.
3. **Hybrid retrieval** — a vector KNN search and a Greek-analyzer **BM25 full-text**
   search run in parallel and are fused with **Reciprocal Rank Fusion** (RRF). This
   catches both semantic matches and exact tokens (CELEX ids, regulation numbers)
   that pure cosine similarity misses.
4. **Reranking** — a `BAAI/bge-reranker-v2-m3` cross-encoder reorders the fused
   candidates and keeps the top `k`, so the LLM sees fewer, better passages.

---

## Architecture

```
MultiEURLEX (HuggingFace)
  └─► load Greek docs ─► token-aware chunking ─► e5-base embeddings
        └─► SurrealDB: chunk table (HNSW vector index + BM25 FTS index)

Query
  └─► embed query
        ├─► vector KNN  ┐
        └─► BM25 FTS    ┴─► RRF fusion ─► cross-encoder rerank ─► top-k chunks
              └─► pydantic-ai agent (llama.cpp) ─► answer with [celex_id] citations
```

Services (Docker Compose):

| Service     | Image / build            | Port  | Role                                   |
|-------------|--------------------------|-------|----------------------------------------|
| `surrealdb` | `surrealdb/surrealdb`    | 8000* | Vector + full-text store               |
| `llama`     | `llama.cpp:server-cuda`  | 8080* | Local LLM (OpenAI-compatible API, GPU) |
| `backend`   | `backend/Dockerfile`     | 9000  | FastAPI: search / ask / check / health |
| `frontend`  | `frontend/Dockerfile`    | 3000  | Next.js UI                             |
| `ingest`    | `backend/Dockerfile`     | —     | One-shot corpus ingestion (profile)    |

\* Internal-only by default; uncomment their `ports:` in `docker-compose.yml` to reach them from the host.

---

## Project structure

```
config.py                 # environment configuration (all tunables + secrets)
main.py                   # CLI entrypoint (ingest, search, ask, check, eval-*)
models/                   # shared pydantic models: Document, Chunk
agent/
  core/                   # prompts, AgentDeps + search tool, agent factory
  retrieval/              # hybrid search + RRF fusion, cross-encoder reranker
  ingestion/              # corpus loader, chunking, embeddings
  storage/                # SurrealDB layer (schema, inserts, vector/FTS search)
backend/                  # FastAPI app: routes, SSE streaming, schemas
evals/                    # ground-truth generation + LLM judge + eval runner
frontend/                 # Next.js UI
tests/                    # pytest suite (unit + integration + backend)
```

---

## Prerequisites

- **Docker** + **Docker Compose**.
- **NVIDIA GPU** with the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
  (llama.cpp runs on CUDA):
  ```bash
  sudo nvidia-ctk runtime configure --runtime=docker
  sudo systemctl restart docker
  docker run --rm --gpus all ubuntu nvidia-smi   # verify the GPU is visible
  ```
- A **GGUF model file** for llama.cpp (e.g. `Qwen3.5-9B-Q4_K_M.gguf`) in a directory
  on the host.
- Free host ports **3000** and **9000** (and 8000/8080 if you expose them).

For local (non-Docker) development you additionally need **Python 3.11+**,
[**uv**](https://docs.astral.sh/uv/), and **Node.js 20+**.

---

## Quick start (Docker — recommended)

### 1. Configure

```bash
cp .env.docker.example .env.docker
```

Edit `.env.docker` and set the paths for your machine:

| Variable              | Required | Description                                                        |
|-----------------------|----------|--------------------------------------------------------------------|
| `LLAMA_MODELS_DIR`    | yes      | Host directory containing your GGUF model(s).                      |
| `LLAMACPP_MODEL_FILE` | yes      | GGUF filename inside that directory.                              |
| `HF_CACHE_DIR`        | yes      | Host HuggingFace cache (reuses downloaded embedding model + data). |
| `HOST_UID` / `HOST_GID` | yes    | User that owns `./data`; SurrealDB runs as this uid. Use `id -u`/`id -g`. |
| `LOGFIRE_TOKEN`       | no       | Send agent traces to Logfire; otherwise they print to backend logs. |
| `RERANKER_MODEL`      | no       | Cross-encoder model (default `BAAI/bge-reranker-v2-m3`).           |
| `RERANKER_DEVICE`     | no       | `cpu` (default) or `cuda` if you have VRAM headroom next to llama. |

### 2. Ingest the corpus

The vector store starts empty and `./data` is not committed, so a first ingest is
**required**. This drops/recreates the schema and embeds the corpus:

```bash
# Build the images (needed after any code change)
docker compose --env-file .env.docker build backend ingest

# Smoke test: ingest a small sample (~300 docs)
docker compose --env-file .env.docker --profile ingest run --rm ingest

# Or ingest the entire Greek corpus (~55k docs → hundreds of thousands of chunks)
docker compose --env-file .env.docker --profile ingest run --rm ingest python main.py ingest --all
```

The reranker model (~2 GB) downloads into the mounted HF cache the first time it is
used, not during ingest.

### 3. Run

```bash
docker compose --env-file .env.docker up -d
curl -s localhost:9000/api/health        # {"surrealdb": true, "llamacpp": true}
```

Open **http://localhost:3000**. The first `ask` request pulls and loads the reranker,
so it lags before streaming; later requests are fast.

```bash
docker compose --env-file .env.docker down   # stop everything
```

> After changing any Python code, rebuild the affected image(s) — `backend` serves the
> API and `ingest` runs the pipeline; both use `backend/Dockerfile`:
> `docker compose --env-file .env.docker build backend ingest && docker compose --env-file .env.docker up -d backend`.

---

## CLI

All commands run through `main.py` (inside the container: `docker compose ... exec backend python main.py ...`).

```bash
python main.py init-db [--force]               # create schema + indexes (wipes chunks)
python main.py ingest [--limit N | --all]      # build the corpus (default limit 300)
python main.py stats                           # total chunks + distinct documents
python main.py search "φορολογία ακινήτων"     # raw hybrid retrieval, no LLM
python main.py ask "Ποιες είναι οι υποχρεώσεις;"  # agent answer with citations
python main.py check policy.txt                # surface relevant law for a document
python main.py eval-generate --sample 5 --seed 42   # make ground-truth Q&A
python main.py eval-run [--no-rerank]          # run RAG + judge; prints metrics
```

`ingest` calls `init-db` internally, so a standalone `init-db` is only needed to
create or wipe the schema without re-embedding. Use `stats` to confirm the store is
populated.

---

## Evaluation

The eval harness is fully local — the same llama.cpp model both generates ground-truth
Q&A and judges answers.

```bash
# 1. Generate ground truth from ingested documents
python main.py eval-generate --sample 5 --seed 42
#    → writes eval_data/ground_truth.jsonl

# 2. Run the RAG against it and score each answer
python main.py eval-run
#    → prints verdicts, mean scores, and retrieval hit rate; writes eval_data/results-*.jsonl

# 3. Compare hybrid+rerank vs. hybrid-only to quantify the reranker
python main.py eval-run --no-rerank
```

`retrieval_hit` (did the ground-truth document's `celex_id` appear in a tool result?)
is deterministic and doesn't depend on the local judge's quality — the most reliable
number to track.

---

## Local development (without Docker)

You need a running SurrealDB and llama.cpp server reachable via the URLs in your
environment.

```bash
uv sync                                   # install Python dependencies

# Configure via a local .env (see the env vars in config.py); LLAMACPP_MODEL is required.
export LLAMACPP_MODEL=your-model-name

uv run python main.py ingest --limit 100  # ingest a small sample
uv run uvicorn backend.main:app --port 9000   # run the API

# Frontend (separate terminal)
cd frontend && npm install && npm run dev # http://localhost:3000
```

Configuration lives in [`config.py`](config.py); every value has an environment-variable
override (`SURREALDB_URL`, `LLAMACPP_URL`, `INGEST_LIMIT`, `RERANKER_DEVICE`, …). Only
`LLAMACPP_MODEL` is mandatory.

---

## Testing

```bash
uv run pytest                 # unit tests (integration tests are deselected by default)
uv run pytest -m integration  # requires a live SurrealDB at SURREALDB_URL
```

---

## Notes

- **Dataset & labels** — `nlpaueb/multi_eurlex`, Greek (`el`) text with level-1 EUROVOC
  concept labels. Documents without a Greek translation are skipped.
- **A schema/chunking change requires a re-ingest.** `reset_schema` drops and recreates
  the `chunk` table (including the HNSW and BM25 indexes), so re-running `ingest` fully
  replaces the corpus — no migration needed.
- **`ask` is single-turn** today.
- If SurrealDB logs `Permission denied` on `./data`, set `HOST_UID`/`HOST_GID` in
  `.env.docker` to your `id -u` / `id -g`.
