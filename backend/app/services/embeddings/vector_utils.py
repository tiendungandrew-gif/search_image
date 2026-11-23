"""Stable vector byte fingerprint shared by indexing and retrieval."""

import hashlib

import numpy as np


def vector_hash(value):
    return hashlib.sha256(np.asarray(value, dtype="<f4").tobytes()).hexdigest()
