import json
import zipfile

from huggingface_hub import hf_hub_download

from models import Document

REPO_ID = "nlpaueb/multi_eurlex"
ZIP_FILENAME = "multi_eurlex_translated.zip"
LANGUAGE = "el"


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
                concepts = row["eurovoc_concepts"]
                documents.append(Document(
                    celex_id=row["celex_id"],
                    text=text,
                    labels=concepts.get("level_1", []),
                    labels_l2=concepts.get("level_2", []),
                    labels_l3=concepts.get("level_3", []),
                ))
    return documents
