import urllib.error
import urllib.request
from pathlib import Path

import click

from agent import AgentDeps, build_ask_agent, build_check_agent, eurovoc
from agent.ingestion.chunking import chunk_document
from agent.ingestion.embeddings import Embedder
from agent.ingestion.loader import load_documents
from agent.retrieval import search
from agent.storage.surreal import (
    count_chunks,
    insert_chunks,
    list_celex_ids,
    reset_schema,
)
from config import load_config
from evals.ground_truth import generate_ground_truth
from evals.runner import run_eval


@click.group()
def cli():
    pass


@cli.command()
@click.option("--limit", default=None, type=int, help="Number of documents to ingest.")
@click.option("--all", "ingest_all", is_flag=True, default=False,
              help="Ingest the entire Greek corpus (overrides --limit and the config default).")
def ingest(limit, ingest_all):
    config = load_config()
    doc_limit = None if ingest_all else (limit if limit is not None else config.ingest_limit)
    scope = "all" if doc_limit is None else f"up to {doc_limit}"
    click.echo(f"Loading {scope} Greek documents from multi_eurlex...")
    documents = load_documents(limit=doc_limit)
    click.echo(f"Loaded {len(documents)} documents. Chunking...")
    embedder = Embedder.from_pretrained()
    chunks = [
        chunk for doc in documents for chunk in chunk_document(doc, embedder.count_tokens)
    ]
    click.echo(f"Produced {len(chunks)} chunks. Embedding...")
    embeddings = embedder.embed_passages([chunk.text for chunk in chunks])
    click.echo("Writing to SurrealDB...")
    reset_schema(config)
    insert_chunks(config, chunks, embeddings)
    click.echo(f"Ingest complete: {len(chunks)} chunks stored.")


@cli.command(name="init-db")
@click.option("--force", is_flag=True, default=False, help="Skip the confirmation prompt.")
def init_db(force):
    """Create the SurrealDB schema (table + vector/FTS indexes). Wipes existing chunks."""
    config = load_config()
    if not force:
        click.confirm(
            "This drops and recreates the 'chunk' table, deleting all ingested data. Continue?",
            abort=True,
        )
    reset_schema(config)
    click.echo("Schema initialized: 'chunk' table with HNSW vector and BM25 full-text indexes.")


@cli.command()
def stats():
    """Show corpus stats: total chunks and distinct documents in SurrealDB."""
    config = load_config()
    chunk_count = count_chunks(config)
    doc_count = len(list_celex_ids(config))
    click.echo(f"Chunks: {chunk_count}")
    click.echo(f"Distinct documents (celex_id): {doc_count}")


@cli.command(name="search")
@click.argument("query")
@click.option("--top-k", default=5, type=int)
@click.option("--label", default=None, type=str)
def search_command(query, top_k, label):
    config = load_config()
    embedder = Embedder.from_pretrained()
    results = search(config, embedder, query, top_k=top_k, label_filter=label)
    if not results:
        click.echo("No relevant passages found.")
        return
    for i, chunk in enumerate(results, start=1):
        domains = ", ".join(c["el"] for c in eurovoc.concepts(chunk.labels))
        click.echo(f"\n[{i}] celex_id={chunk.celex_id} [{domains}]")
        click.echo(chunk.text[:300])


def _check_llamacpp_reachable(config) -> None:
    try:
        urllib.request.urlopen(f"{config.llamacpp_url}/models", timeout=3)
    except (urllib.error.URLError, OSError) as exc:
        raise click.ClickException(
            f"Could not reach llama.cpp server at {config.llamacpp_url}: {exc}"
        )


@cli.command()
@click.argument("question")
def ask(question):
    config = load_config()
    _check_llamacpp_reachable(config)
    embedder = Embedder.from_pretrained()
    deps = AgentDeps(config=config, embedder=embedder)
    agent = build_ask_agent(config)
    result = agent.run_sync(question, deps=deps)
    click.echo(result.output)


@cli.command(name="eval-generate")
@click.option("--sample", default=5, type=int, help="Number of documents to sample.")
@click.option("--questions", default=3, type=int, help="Q&A pairs per document.")
@click.option("--seed", default=None, type=int, help="Random seed for reproducible sampling.")
@click.option("--output", default="eval_data/ground_truth.jsonl", type=click.Path(dir_okay=False))
def eval_generate(sample, questions, seed, output):
    config = load_config()
    _check_llamacpp_reachable(config)
    written = generate_ground_truth(
        config,
        sample_size=sample,
        questions_per_doc=questions,
        output_path=Path(output),
        seed=seed,
    )
    click.echo(f"Wrote {written} Q&A pairs to {output}")


@cli.command(name="eval-run")
@click.option("--ground-truth", default="eval_data/ground_truth.jsonl",
              type=click.Path(exists=True, dir_okay=False))
@click.option("--limit", default=None, type=int, help="Evaluate only the first N pairs.")
@click.option("--no-rerank", is_flag=True, default=False,
              help="Disable cross-encoder reranking (hybrid-only baseline).")
def eval_run(ground_truth, limit, no_rerank):
    config = load_config()
    _check_llamacpp_reachable(config)
    embedder = Embedder.from_pretrained()
    path = run_eval(config, embedder, Path(ground_truth), limit=limit, rerank=not no_rerank)
    click.echo(f"Results written to {path}")


@cli.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
def check(file):
    config = load_config()
    _check_llamacpp_reachable(config)
    with open(file, encoding="utf-8") as f:
        document_text = f.read()
    embedder = Embedder.from_pretrained()
    deps = AgentDeps(config=config, embedder=embedder)
    agent = build_check_agent(config)
    result = agent.run_sync(document_text, deps=deps)
    click.echo(result.output)


if __name__ == "__main__":
    cli()
