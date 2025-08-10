#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced KB indexer for RAG (with title embeddings)
- Reads: txt, md, markdown, pdf, docx, html, htm, rtf (optional), csv, json, xml, pptx (optional)
- Robust text extraction with graceful fallbacks
- Paragraph-aware chunking with overlap + dedup
- Saves FAISS index + metadata (+ titles.npy) to workdir/kb
- Prints a summary report
"""

import os
import json
import re
import csv
from pathlib import Path
from typing import List, Dict, Any
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
from docx import Document as DocxDocument
import markdown as md
from bs4 import BeautifulSoup

# Optional deps (loaded lazily if present)
def _try_import(name: str):
    try:
        return __import__(name, fromlist=["*"])
    except Exception:
        return None

striprtf = _try_import("striprtf.striprtf")
pptx     = _try_import("pptx")  # python-pptx

# ── Paths ──────────────────────────────────────────────────────────────────────
# This file lives in backend/chat_core/, project root is parents[3]
THIS_DIR = Path(__file__).resolve().parent
# Project root is two levels up from this file: backend/chat_core -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Documents continue to come from workdir/docs
DOCS = PROJECT_ROOT / "workdir" / "docs"
DOCS.mkdir(parents=True, exist_ok=True)

# KB index files should live under backend/chat_core/kb
KB = THIS_DIR / "kb"
KB.mkdir(parents=True, exist_ok=True)

INDEX_PATH       = KB / "faiss.index"
META_PATH        = KB / "meta.json"
TITLES_NPY_PATH  = KB / "titles.npy"           # <— new: title embedding matrix

# Strong default embeddings: use BGE base v1.5 (768-dim) to match retriever/FAISS
MODEL_NAME = os.environ.get("EMB_MODEL", "BAAI/bge-base-en-v1.5")

# ── Supported extensions ───────────────────────────────────────────────────────
SUPPORTED_EXTS = {
    ".txt", ".md", ".markdown", ".pdf", ".docx", ".html", ".htm",
    ".rtf", ".csv", ".json", ".xml", ".pptx"
}

# ── Chunking ───────────────────────────────────────────────────────────────────
CHUNK_SIZE = 1600     # characters per chunk (balanced for detail + context)
CHUNK_OVERLAP = 300   # sliding window overlap (optimized for continuity)
MAX_FILE_CHARS = 2_000_000  # avoid pathological files

# ── Helpers ───────────────────────────────────────────────────────────────────
def sha1(s: str) -> str:
    import hashlib as _h
    return _h.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def _clean_ws(s: str) -> str:
    s = s.replace("\x00", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def _flatten_json(obj: Any, prefix: str = "") -> str:
    pieces = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            pieces.append(_flatten_json(v, key))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            key = f"{prefix}[{i}]"
            pieces.append(_flatten_json(v, key))
    else:
        pieces.append(f"{prefix}: {obj}")
    return "\n".join(p for p in pieces if p)

def _paragraphs(text: str) -> List[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return paras or [text.strip()]

def chunk_text(body: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Smart paragraph-aware chunking with better context preservation."""
    if not body:
        return []
    
    # Try to preserve logical sections by looking for headers and structure
    paras = _paragraphs(body)
    chunks, buf = [], ""

    for i, p in enumerate(paras):
        # Check if this paragraph looks like a header/section start or important technical term
        is_header = bool(re.match(r'^(#+\s|[0-9]+\.\s|[A-Z][A-Za-z0-9 ]{2,}:|\*\*[^*]+\*\*)', p.strip()))
        is_technical_section = bool(re.search(r'\b(IQ|OQ|PQ|Installation|Operational|Performance|Qualification|Validation|Testing|Verification)\b', p, re.IGNORECASE))
        
        if not buf:
            buf = p
        elif len(buf) + 1 + len(p) <= size:
            buf = f"{buf}\n{p}"
        else:
            # If current paragraph is a header/technical section and we're not too small, start new chunk
            if (is_header or is_technical_section) and len(buf) > size // 3:
                chunks.append(buf)
                buf = p
            else:
                chunks.append(buf)
                # Better overlap strategy: try to include complete sentences
                if overlap > 0 and len(buf) > overlap:
                    tail = buf[-overlap:]
                    # Try to start overlap at sentence boundary
                    sentences = re.split(r'[.!?]+\s+', tail)
                    if len(sentences) > 1:
                        tail = '. '.join(sentences[-2:]) if len(sentences) >= 2 else tail
                    buf = f"{tail}\n{p}"
                else:
                    buf = p

    if buf:
        chunks.append(buf)

    # Split any monster chunk defensively but preserve structure
    out = []
    for c in chunks:
        if len(c) <= size * 1.5:  # Allow slightly larger chunks for context
            out.append(c)
        else:
            # Split at sentence boundaries when possible
            sentences = re.split(r'([.!?]+\s+)', c)
            current_chunk = ""
            
            for j in range(0, len(sentences), 2):
                sentence = sentences[j] + (sentences[j+1] if j+1 < len(sentences) else "")
                if len(current_chunk) + len(sentence) <= size * 1.5:
                    current_chunk += sentence
                else:
                    if current_chunk:
                        out.append(current_chunk.strip())
                    current_chunk = sentence
            
            if current_chunk:
                out.append(current_chunk.strip())
    
    return [chunk for chunk in out if chunk.strip()]

# ── Loaders ───────────────────────────────────────────────────────────────────
def load_text_file(p: Path) -> str:
    return p.read_text("utf-8", errors="ignore")

def load_markdown(p: Path) -> str:
    html = md.markdown(p.read_text("utf-8", errors="ignore"))
    return BeautifulSoup(html, "html.parser").get_text(" ")

def load_html(p: Path) -> str:
    soup = BeautifulSoup(p.read_text("utf-8", errors="ignore"), "html.parser")
    for tag in soup(["script", "style"]):
        tag.extract()
    return soup.get_text(" ")

def load_pdf(p: Path) -> str:
    out = []
    r = PdfReader(str(p))
    for page in r.pages:
        out.append(page.extract_text() or "")
    return "\n".join(out)

def load_docx(p: Path) -> str:
    d = DocxDocument(str(p))
    return "\n".join([para.text for para in d.paragraphs])

def load_rtf(p: Path) -> str:
    if not striprtf:
        return p.read_text("utf-8", errors="ignore")
    return striprtf.rtf_to_text(p.read_text("utf-8", errors="ignore"))

def load_csv(p: Path) -> str:
    out = []
    with p.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            out.append(" ".join(str(x) for x in row))
    return "\n".join(out)

def load_json_file(p: Path) -> str:
    try:
        obj = json.loads(p.read_text("utf-8", errors="ignore"))
        return _flatten_json(obj)
    except Exception:
        return p.read_text("utf-8", errors="ignore")

def load_xml(p: Path) -> str:
    try:
        soup = BeautifulSoup(p.read_text("utf-8", errors="ignore"), "xml")
        return soup.get_text(" ")
    except Exception:
        return p.read_text("utf-8", errors="ignore")

def load_pptx(p: Path) -> str:
    if not pptx:
        return p.read_text("utf-8", errors="ignore")
    texts = []
    prs = pptx.Presentation(str(p))
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text:
                texts.append(shape.text)
    return "\n".join(texts)

LOADERS = {
    ".txt": load_text_file,
    ".md": load_markdown,
    ".markdown": load_markdown,
    ".pdf": load_pdf,
    ".docx": load_docx,
    ".html": load_html,
    ".htm": load_html,
    ".rtf": load_rtf,
    ".csv": load_csv,
    ".json": load_json_file,
    ".xml": load_xml,
    ".pptx": load_pptx,
}

def load_text(p: Path) -> str:
    ext = p.suffix.lower()
    fn = LOADERS.get(ext, load_text_file)
    try:
        return fn(p)
    except Exception as e:
        print(f"[WARN] Error reading {p.name}: {e}")
        try:
            return p.read_text("utf-8", errors="ignore")
        except Exception:
            return ""

# ── Title extraction ───────────────────────────────────────────────────────────
_heading_pat = re.compile(r"^(#+\s.+|[0-9]+\.\s.+|[A-Z][A-Za-z0-9 _-]{2,}\:)$")

def guess_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if _heading_pat.match(s) or len(s.split()) >= 2:
            return s[:160]
    return fallback[:160]

# ── Indexing ───────────────────────────────────────────────────────────────────
def main():
    files = [p for p in DOCS.rglob("*")
             if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]

    if not files:
        print(f"No files found in {DOCS}")
        return

    model = SentenceTransformer(MODEL_NAME)

    embeddings_texts: List[str] = []
    meta: List[Dict[str, Any]] = []
    titles_ordered: List[str] = []         # order of first appearance (for titles.npy)
    title_for_doc: Dict[str, str] = {}     # doc path -> title text

    per_file_counts: Dict[str, int] = {}
    seen_chunk_hashes = set()
    total_chars = 0

    for f in sorted(files):
        raw = load_text(f)
        if not raw:
            print(f"[SKIP] {f.name}: no text extracted.")
            continue

        raw = raw[:MAX_FILE_CHARS]
        text = _clean_ws(raw)
        if not text:
            print(f"[SKIP] {f.name}: empty after cleaning.")
            continue

        # title per file
        title = guess_title(text, f.stem.replace("_", " "))
        title_for_doc[str(f)] = title
        if title not in titles_ordered:
            titles_ordered.append(title)

        chunks = chunk_text(text)
        added = 0
        for idx, ch in enumerate(chunks):
            ch_norm = ch.strip()
            if not ch_norm:
                continue
            h = sha1(ch_norm)
            if h in seen_chunk_hashes:
                continue
            seen_chunk_hashes.add(h)

            meta.append({
                "doc": str(f),
                "title": title,       # <— include title in meta for retriever mapping
                "chunk_id": idx,
                "text": ch_norm,
                "id": h[:16]
            })
            embeddings_texts.append(ch_norm)
            added += 1
            total_chars += len(ch_norm)

        per_file_counts[str(f)] = added
        print(f"[OK] {f.name}: {added} chunks")

    if not embeddings_texts:
        print("No text extracted.")
        return

    print(f"\nEmbedding {len(embeddings_texts)} chunks with {MODEL_NAME} …")
    vecs = model.encode(
        embeddings_texts,
        convert_to_numpy=True,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    # Build FAISS IP index
    index = faiss.IndexFlatIP(vecs.shape[1])
    index.add(vecs)

    # Title embeddings matrix (order == titles_ordered)
    print(f"Embedding {len(titles_ordered)} titles …")
    title_vecs = model.encode(
        titles_ordered,
        convert_to_numpy=True,
        show_progress_bar=False,
        normalize_embeddings=True
    )

    # Persist
    faiss.write_index(index, str(INDEX_PATH))
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    np.save(TITLES_NPY_PATH, title_vecs)

    # Summary
    print("\n──────────────── Summary ────────────────")
    print(f"Files indexed   : {len(per_file_counts)}")
    print(f"Total chunks    : {len(meta)}")
    print(f"Total characters: {total_chars:,}")
    print("Per-file chunks :")
    for k, v in per_file_counts.items():
        print(f"  - {Path(k).name}: {v}")
    print(f"\n-> {INDEX_PATH}")
    print(f"-> {META_PATH}")
    print(f"-> {TITLES_NPY_PATH}")

if __name__ == "__main__":
    main()