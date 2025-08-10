#!/usr/bin/env python3
import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

# Paths
ROOT = Path(__file__).resolve().parents[1]  # adjust if needed
KB = ROOT / "kb"
META_PATH = KB / "meta.json"
TITLES_NPY = KB / "titles.npy"

MODEL_NAME = "BAAI/bge-small-en-v1.5"  # must match retriever.py

# Load meta.json
meta = json.loads(META_PATH.read_text("utf-8"))

# Extract unique titles in first-seen order
title_to_row = {}
titles_list = []
for m in meta:
    t = (m.get("title") or "").strip()
    if not t:
        continue
    if t not in title_to_row:
        title_to_row[t] = len(titles_list)
        titles_list.append(t)

print(f"[INFO] Found {len(titles_list)} unique titles.")

# Encode and normalize
model = SentenceTransformer(MODEL_NAME)
embs = model.encode(titles_list, convert_to_numpy=True)
embs = embs / (np.linalg.norm(embs, axis=1, keepdims=True) + 1e-12)

# Save to titles.npy
np.save(TITLES_NPY, embs)
print(f"[OK] Saved {TITLES_NPY} with shape {embs.shape}")