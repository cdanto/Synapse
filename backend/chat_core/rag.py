#!/usr/bin/env python3
import re
from pathlib import Path
from typing import List, Dict

from .core import WORKDIR, config

# ----- Tiny local KB (for RAG) -----
# Use colocated KB next to retriever (backend/chat_core/kb)
from pathlib import Path as _P
KB_DIR = _P(__file__).resolve().parent / "kb"
KB_DIR.mkdir(parents=True, exist_ok=True)

KB_INDEX: List[Dict[str, str]] = []


def _iter_kb_files():
    for p in KB_DIR.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".txt", ".md"}:
            yield p


def _chunk_text(text: str, max_len: int = 600) -> List[str]:
    text = text.strip()
    if not text:
        return []
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[str] = []
    buf = ""
    for p in paras:
        if len(buf) + len(p) + 2 <= max_len:
            buf = (buf + "\n\n" + p).strip() if buf else p
        else:
            if buf:
                chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)
    return chunks


def _index_kb() -> int:
    KB_INDEX.clear()
    for f in _iter_kb_files():
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for ch in _chunk_text(txt):
            KB_INDEX.append({"text": ch, "source": f.name})
    return len(KB_INDEX)


_STOP = set("""a an and are as at be by for from has have in is it its of on or that the this to was were will with you your""".split())


def _score_chunk(query: str, chunk: str) -> int:
    q = [w for w in re.findall(r"[A-Za-z0-9]+", query.lower()) if w not in _STOP]
    if not q:
        return 0
    c = chunk.lower()
    score = 0
    for w in q:
        score += c.count(w)
    return score


def build_context_block(user_query: str) -> str:
    """Build a context block using the advanced FAISS retriever when available,
    falling back to the lightweight local KB if needed.

    Respects rag_top_k and rag_max_chars from config.
    """
    top_k = int(config.get("rag_top_k", 4))
    max_chars = int(config.get("rag_max_chars", 1800))

    # 1) Prefer advanced retriever (semantic + BM25 hybrid)
    try:
        from .kb.retriever import Retriever  # type: ignore
        retr = Retriever(top_k=top_k)
        hits = retr.search(user_query, top_k=top_k)
        if hits:
            out_lines = ["Relevant context (KB):"]
            used = 0
            for h in hits:
                title = (h.get("title") or "").strip() or Path(h.get("doc", "")).name
                snippet = (h.get("text") or "").strip()
                if not snippet:
                    continue
                block = f"\n---\nSource: {title}\n{snippet}\n"
                if used + len(block) > max_chars:
                    break
                out_lines.append(block)
                used += len(block)
            if len(out_lines) > 1:
                return "\n".join(out_lines).strip()
    except Exception as e:
        # Log the error for debugging
        print(f"RAG retriever error: {e}")
        # silently fall back to local KB below
        pass

    # 2) Fallback: lightweight local KB (txt/md under workdir/kb)
    if not KB_INDEX:
        _index_kb()
    ranked = sorted(KB_INDEX, key=lambda ch: _score_chunk(user_query, ch["text"]), reverse=True)
    ranked = [r for r in ranked if _score_chunk(user_query, r["text"]) > 0][:max(1, top_k)]
    if not ranked:
        return ""
    out_lines = ["Relevant context (local KB):"]
    used = 0
    for r in ranked:
        snippet = r["text"].strip()
        block = f"\n---\nSource: {r['source']}\n{snippet}\n"
        if used + len(block) > max_chars:
            break
        out_lines.append(block)
        used += len(block)
    return "\n".join(out_lines).strip()


def get_retriever():
    # Thin wrapper to use advanced retriever when available
    try:
        from .kb.retriever import Retriever  # type: ignore
        return Retriever(top_k=int(config.get("rag_top_k", 4)))
    except Exception as e:
        print(f"RAG retriever import error: {e}")
        return None


