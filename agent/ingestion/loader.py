import json
import zipfile

from huggingface_hub import hf_hub_download

from models import Document

REPO_ID = "nlpaueb/multi_eurlex"
ZIP_FILENAME = "multi_eurlex_translated.zip"
LANGUAGE = "el"
LABEL_LEVEL = "level_1"


def load_documents(limit: int | None) -> list[Document]:
    zip_path = hf_hub_download(repo_id=REPO_ID, filename=ZIP_FILENAME, repo_type="dataset")
    documents: list[Document] = []
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open("train.jsonl") as f:
            for raw_line in f:
                if limit is not None and len(documents) >= limit:
                    break
                row = json.loads(raw_line)
                text = row["text"].get(LANGUAGE)
                if not text:
                    continue
                documents.append(Document(
                    celex_id=row["celex_id"],
                    text=text,
                    labels=row["eurovoc_concepts"][LABEL_LEVEL],
                ))
    return documents
