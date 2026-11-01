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
  Only passages the reranker scores at **0.55 or higher** count. Each document is shown
  **once**, with its best passage and how many of its passages matched, best first, **10
  per page**; a query with nothing above the bar gets an explicit refusal.
- **Evaluate** — generate ground-truth Q&A from the corpus and score the RAG against
  it with deterministic retrieval metrics, and diff runs against a baseline.

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
| `backend`   | `backend/Dockerfile`     | 9000  | FastAPI: search / ask / check / labels / health |
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
  eurovoc.py              # resolve EUROVOC concept IDs → Greek/English names
  eurovoc_descriptors.json # bundled level_1/2/3 descriptor lookup
backend/                  # FastAPI app: routes, SSE streaming, schemas
mcp_server/               # MCP server exposing the backend as tools (search/ask/check/labels/health)
evals/                    # pydantic-evals dataset, evaluators, LLM judge, runner
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
- A **GGUF model file** for llama.cpp in a directory on the host. For this Greek/EU
  legal corpus a Greek-specialized model is recommended — e.g.
  [`llama-krikri-8b-instruct-q8_0.gguf`](https://huggingface.co/ilsp/Llama-Krikri-8B-Instruct-GGUF)
  (~8.7 GB, fits a 16 GB GPU at near-lossless Q8_0) — but any GGUF works.
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
| `RETRIEVAL_MIN_SCORE` | no       | Search keeps results scoring at least this (default `0.55`, range 0–1). |
| `SEARCH_POOL`         | no       | Candidates reranked per search query, which caps the result count (default `50`). |

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
python main.py eval-run [--no-rerank] [--name N] [--baseline R]  # run RAG + judge, save report
python main.py eval-compare REPORT BASELINE    # diff two saved reports
```

`ingest` calls `init-db` internally, so a standalone `init-db` is only needed to
create or wipe the schema without re-embedding. Use `stats` to confirm the store is
populated.

---

## Evaluation

The eval harness is built on [pydantic-evals](https://pydantic.dev/docs/ai/evals/evals/)
and is fully local: by default the same llama.cpp model generates ground truth,
answers, and judges.

```bash
# 1. Generate ground truth from ingested documents
python main.py eval-generate --sample 5 --seed 42
#    → writes eval_data/ground_truth.yaml (+ a JSON schema for editor autocomplete);
#      hand-edit it to fix or add cases. A legacy ground_truth.jsonl still loads.

# 2. Run the RAG against it and score each case
python main.py eval-run --name q6-rerank
#    → prints a per-case table and averages; saves eval_data/reports/q6-rerank.json

# 3. Compare against a baseline — another config, or a saved earlier run
python main.py eval-run --name q6-norerank --no-rerank --baseline eval_data/reports/q6-rerank.json
python main.py eval-compare eval_data/reports/q6-rerank.json eval_data/reports/q8-rerank.json

# Run each case N times to see whether a difference is real or run-to-run noise
python main.py eval-run --name q6-rerank-x3 --repeat 3
```

Per case it reports:

| Kind | Name | Source |
|------|------|--------|
| assertion | `retrieval_hit`, `hit@1` | ground-truth `celex_id` among / first in retrieved sources |
| score | `reciprocal_rank` | 1 / rank of the ground-truth document (0 if missed) |
| assertion | `greek_queries` | every planner search query is Greek script (the corpus and reranker are Greek-only) |
| score | `factual_correctness`, `completeness`, `citation_quality`, `no_hedging` | LLM judge |
| label | `verdict` | LLM judge (`correct` / `partially_correct` / `incorrect`, notes as reason) |
| metric | `searches`, `requests`, tokens | planner searches; model usage recorded by pydantic-ai |

The retrieval and `greek_queries` checks are deterministic and don't depend on the
local judge's quality — the most reliable numbers to track. Each report stores the
run settings (`rag_model`, `judge_model`, `rerank`, `reranker_device`, …), and the
diff header shows what changed between two runs.

**Comparing RAG models (e.g. Q8_0 vs Q6_K).** llama.cpp serves one model at a time, so
run one, swap `LLAMACPP_MODEL_FILE` and restart `llama`, run the other with
`--baseline` (or diff afterwards with `eval-compare`). Unless `JUDGE_LLAMACPP_URL` /
`JUDGE_LLAMACPP_MODEL` point at a separate, fixed judge server, the judge swaps along
with the RAG model; the comparison then warns that judge scores are not comparable,
and only the deterministic checks should be trusted.

**In Docker**, the backend image has no `eval_data` volume, so mount one (as your
user, so files aren't root-owned) and the current source:

```bash
docker compose --env-file .env.docker run --rm --no-deps --user "$(id -u):$(id -g)" \
  -e HOME=/tmp -e USER=eval -v "$PWD/eval_data:/app/eval_data" \
  backend python main.py eval-run --name q6-rerank
```

Rebuild `backend` first if you changed code. The eval container loads its own copy of
the embedder and reranker; add `-e RERANKER_DEVICE=cpu -e CUDA_VISIBLE_DEVICES=` if
the GPU has no headroom next to the running backend.

---

## MCP server

`mcp_server/server.py` exposes the backend as MCP tools (`search_legislation`,
`ask_legislation`, `check_document`, `list_legislation_labels`,
`check_service_health`) so any MCP client — Claude Desktop, Claude Code, etc. —
can query the corpus directly. It's a thin HTTP client of the FastAPI backend
(no model/DB loading in the MCP process), so the backend must already be
running (`docker compose ... up -d` or `uvicorn backend.main:app`).

Register it with Claude Code:

```bash
claude mcp add compliance-rag -- uv --directory /path/to/this/repo run python -m mcp_server.server
```

Or add it manually to a client's MCP config:

```json
{
  "mcpServers": {
    "compliance-rag": {
      "command": "uv",
      "args": ["--directory", "/path/to/this/repo", "run", "python", "-m", "mcp_server.server"]
    }
  }
}
```

If the backend isn't at `http://localhost:9000`, set `COMPLIANCE_RAG_BACKEND_URL`
(as an `env` entry in the MCP config, or in your shell before running it directly).

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

- **Dataset & labels** — `nlpaueb/multi_eurlex`, Greek (`el`) text with EUROVOC concept
  labels at all three granularities (level_1 domains, level_2 microthesauri, level_3
  concepts), resolved to Greek/English names via the bundled `agent/eurovoc_descriptors.json`.
  Documents without a Greek translation are skipped.
- **A schema/chunking change requires a re-ingest.** `reset_schema` drops and recreates
  the `chunk` table (including the HNSW and BM25 indexes), so re-running `ingest` fully
  replaces the corpus — no migration needed.
- **`ask` is single-turn** today.
- If SurrealDB logs `Permission denied` on `./data`, set `HOST_UID`/`HOST_GID` in
  `.env.docker` to your `id -u` / `id -g`.
