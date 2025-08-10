#!/usr/bin/env python3
import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
import faiss

from sentence_transformers import SentenceTransformer
try:
    from rank_bm25 import BM25Okapi  # optional
except Exception:  # pragma: no cover
    BM25Okapi = None
try:
    from sentence_transformers import CrossEncoder  # optional
except Exception:  # pragma: no cover
    CrossEncoder = None

# --- Paths ---
# KB index files now live alongside this module: backend/chat_core/kb
KB   = Path(__file__).resolve().parent
INDEX_PATH = KB / "faiss.index"
META_PATH  = KB / "meta.json"
TITLES_NPY = KB / "titles.npy"                    # optional (added by index_kb.py)

# IMPORTANT: Must match the model used by index_kb.py when the index was built.
# Default to base (768-dim) to align with current FAISS index
MODEL_NAME = os.environ.get("EMB_MODEL", "BAAI/bge-base-en-v1.5")

class Retriever:
    def __init__(self, top_k: int = 4):
        # knobs (env overrides)
        self.top_k: int = int(top_k)
        self.alpha_hybrid: float = float(os.environ.get("RAG_ALPHA", 0.6))  # vec vs bm25 mix
        self.vec_k: int = int(os.environ.get("RAG_VEC_K", max(self.top_k * 5, 50)))
        self.bm25_k: int = int(os.environ.get("RAG_BM25_K", max(self.top_k * 5, 50)))
        self.mmr_lambda: float = float(os.environ.get("RAG_MMR_LAMBDA", 0.6))
        self.mmr_pool: int = int(os.environ.get("RAG_MMR_POOL", max(self.top_k * 3, 15)))
        self.reranker_model_name: Optional[str] = os.environ.get("RAG_RERANKER", "").strip() or None
        self.rerank_from: int = int(os.environ.get("RAG_RERANK_FROM", max(self.top_k * 5, 20)))

        # Title boost knobs
        self.title_boost: float = float(os.environ.get("RAG_TITLE_BOOST", 0.25))  # weight for title sim
        self.title_k: int = int(os.environ.get("RAG_TITLE_K", 64))                # cap for title retrieval (efficiency)
        self.use_titles: bool = os.environ.get("RAG_USE_TITLES", "1") not in ("0","false","False")

        # load models and index
        if not INDEX_PATH.is_file() or not META_PATH.is_file():
            raise FileNotFoundError(f"Missing KB files. Expected:\n  {INDEX_PATH}\n  {META_PATH}")

        self.model = SentenceTransformer(MODEL_NAME)
        self.index = faiss.read_index(str(INDEX_PATH))
        # FAISS is inner-product; ensure query vectors are normalized too
        self.normalize = True

        self.meta: List[Dict] = json.loads(META_PATH.read_text("utf-8"))
        self._texts: List[str] = [m.get("text", "") for m in self.meta]

        # Build doc-title table (order = first appearance of each title in meta)
        self._titles_list: List[str] = []
        self._title_to_row: Dict[str, int] = {}
        if self.use_titles and TITLES_NPY.is_file():
            # collect titles in first-seen order
            for m in self.meta:
                t = (m.get("title") or "").strip()
                if not t:
                    continue
                if t not in self._title_to_row:
                    self._title_to_row[t] = len(self._titles_list)
                    self._titles_list.append(t)
            try:
                self._titles_vecs = np.load(TITLES_NPY)
                # Safety: shapes must align
                if self._titles_vecs.shape[0] != len(self._titles_list):
                    # titles.npy came from a different index; disable title boost
                    self._titles_vecs = None
                    self.use_titles = False
            except Exception:
                self._titles_vecs = None
                self.use_titles = False
        else:
            self._titles_vecs = None
            self.use_titles = False

        # Optional BM25 over chunk texts
        if self._texts and BM25Okapi is not None:
            self._bm25 = BM25Okapi([t.lower().split() for t in self._texts])
        else:
            self._bm25 = None

        # Optional cross-encoder reranker
        self._reranker: Optional[object] = None
        if self.reranker_model_name and CrossEncoder is not None:
            try:
                self._reranker = CrossEncoder(self.reranker_model_name)
            except Exception:
                self._reranker = None

    # ---- utilities ----
    def _encode_query(self, query: str) -> np.ndarray:
        q = self.model.encode([query], convert_to_numpy=True)
        if self.normalize:
            q = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-12)
        return q.astype(np.float32)

    @staticmethod
    def _minmax(arr: np.ndarray) -> np.ndarray:
        if arr.size == 0:
            return arr
        mn = float(np.min(arr)); mx = float(np.max(arr))
        if mx - mn < 1e-12:
            return np.zeros_like(arr)
        return (arr - mn) / (mx - mn + 1e-12)

    # ---- title similarity (optional) ----
    def _title_sim(self, query_vec: np.ndarray) -> Dict[str, float]:
        """Return mapping title -> similarity in [0,1] (min-max scaled),
        optionally limiting to top-K titles for efficiency."""
        if not self.use_titles or self._titles_vecs is None or len(self._titles_list) == 0:
            return {}
        q = query_vec[0]  # (d,)
        sims = (self._titles_vecs @ q)  # cosine since normalized
        # take top-K
        if self.title_k and self.title_k < sims.shape[0]:
            top_idx = np.argpartition(-sims, self.title_k)[: self.title_k]
            sims_small = sims[top_idx]
            sims_norm = self._minmax(sims_small)
            out = { self._titles_list[int(i)]: float(sims_norm[j]) for j, i in enumerate(top_idx) }
            return out
        # otherwise min-max all
        sims_norm = self._minmax(sims)
        return { self._titles_list[i]: float(sims_norm[i]) for i in range(len(self._titles_list)) }

    # ---- hybrid rank (vector + BM25 + title boost) ----
    def _hybrid_rank(self, query: str) -> List[Tuple[int, float, float, float, float, float]]:
        """
        Returns list of tuples:
          (chunk_idx, vec_norm, bm25_norm, fused_hybrid, title_sim_norm, total_score)
        sorted by total_score desc.
        """
        if not self.meta:
            return []

        # Vector search
        q = self._encode_query(query)
        vec_k = min(self.vec_k, len(self.meta))
        D, I = self.index.search(q, vec_k)
        vec_ids = [int(i) for i in I[0] if i >= 0]
        vec_scores = [float(s) for s in D[0][:len(vec_ids)]]
        vec_map = dict(zip(vec_ids, vec_scores))

        # BM25
        bm25_ids: List[int] = []
        bm25_map: Dict[int, float] = {}
        if self._bm25 is not None:
            bm = np.array(self._bm25.get_scores(query.lower().split()), dtype=np.float32)
            top_bm = np.argsort(-bm)[:min(self.bm25_k, len(bm))]
            bm25_ids = [int(i) for i in top_bm]
            bm25_map = {int(i): float(bm[int(i)]) for i in top_bm}

        # Candidate union
        cand_list = sorted(set(vec_map.keys()).union(bm25_ids))
        if not cand_list:
            return []

        # Normalize vec+bm25 -> fused hybrid
        v_arr = np.array([vec_map.get(i, 0.0) for i in cand_list], dtype=np.float32)
        b_arr = np.array([bm25_map.get(i, 0.0) for i in cand_list], dtype=np.float32)
        v_norm = self._minmax(v_arr)
        b_norm = self._minmax(b_arr)
        fused = self.alpha_hybrid * v_norm + (1.0 - self.alpha_hybrid) * b_norm

        # Title boost: compute query->title sims, map per chunk via meta["title"]
        title_boosts = np.zeros_like(fused)
        if self.use_titles and self._titles_vecs is not None:
            tmap = self._title_sim(q)  # title -> [0,1]
            if tmap:
                for j, ci in enumerate(cand_list):
                    t = (self.meta[ci].get("title") or "").strip()
                    if t and t in tmap:
                        title_boosts[j] = tmap[t] * self.title_boost

        total = fused + title_boosts

        ranked = list(zip(
            cand_list,
            v_norm.tolist(),
            b_norm.tolist(),
            fused.tolist(),
            title_boosts.tolist(),
            total.tolist(),
        ))
        ranked.sort(key=lambda t: t[5], reverse=True)
        return ranked

    # ---- optional cross-encoder rerank ----
    def _rerank(self, query: str, candidates: List[int], limit: int) -> List[int]:
        if not candidates or not self._reranker:
            return candidates[:limit]
        pairs = [(query, self._texts[i]) for i in candidates]
        try:
            scores = self._reranker.predict(pairs)
            order = np.argsort(-np.array(scores))
            return [candidates[int(i)] for i in order[:limit]]
        except Exception:
            return candidates[:limit]

    # ---- MMR selection ----
    def _mmr(self, query_vec: np.ndarray, candidate_ids: List[int], k: int, lambda_mult: float) -> List[int]:
        if not candidate_ids:
            return []
        k = max(1, min(k, len(candidate_ids)))

        # Embed candidates (small pool)
        cand_texts = [self._texts[i] for i in candidate_ids]
        cand_vecs = self.model.encode(cand_texts, convert_to_numpy=True)
        if self.normalize:
            cand_vecs = cand_vecs / (np.linalg.norm(cand_vecs, axis=1, keepdims=True) + 1e-12)

        qv = query_vec[0]
        sim_q = cand_vecs @ qv                    # (N,)
        sim_dd = cand_vecs @ cand_vecs.T          # (N,N)

        selected: List[int] = []
        selected_mask = np.zeros(len(candidate_ids), dtype=bool)

        for _ in range(k):
            best_i, best_score = -1, -1e9
            for i in range(len(candidate_ids)):
                if selected_mask[i]:
                    continue
                div_pen = 0.0
                if selected:
                    sel_idx = np.where(selected_mask)[0]
                    div_pen = float(np.max(sim_dd[i, sel_idx]))
                mmr = lambda_mult * float(sim_q[i]) - (1.0 - lambda_mult) * div_pen
                if mmr > best_score:
                    best_score, best_i = mmr, i
            if best_i == -1:
                break
            selected_mask[best_i] = True
            selected.append(candidate_ids[best_i])

        return selected

    # ---- public search ----
    def search(self, query: str, *, top_k: Optional[int] = None) -> List[Dict]:
        k_final = int(top_k) if top_k is not None else self.top_k

        # 1) hybrid rank (+ title boost)
        ranked = self._hybrid_rank(query)
        if not ranked:
            return []

        # Candidate pool for rerank/MMR
        pool = [idx for idx, *_ in ranked[: max(self.mmr_pool, self.rerank_from)]]

        # 2) optional rerank
        if self._reranker and pool:
            pool = self._rerank(query, pool, limit=len(pool))

        # 3) MMR diversity on the pool
        qv = self._encode_query(query)
        final_ids = self._mmr(qv, pool, k=k_final, lambda_mult=self.mmr_lambda)

        # 4) build results; include scores for transparency
        hybrid_map = {i: (v, b, h, t, tot) for i, v, b, h, t, tot in ranked}
        out: List[Dict] = []
        for idx in final_ids:
            m = dict(self.meta[idx])
            v, b, h, t, tot = hybrid_map.get(idx, (0.0, 0.0, 0.0, 0.0, 0.0))
            m["score_vec_norm"] = v
            m["score_bm25_norm"] = b
            m["score_hybrid"] = h
            m["score_title"] = t
            m["score_total"] = tot
            out.append(m)
        return out