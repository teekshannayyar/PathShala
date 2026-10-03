"""A deterministic, offline stand-in for the sentence-transformers embedder.

Used when EMBEDDING_BACKEND=fake (offline development) and by the test suite.
Each word token is hashed with SHA-256 into a few signed buckets of a
384-dimension vector (the size all-MiniLM-L6-v2 produces), and the result is
L2-normalised. Identical text gives identical vectors and texts that share
words get a positive cosine similarity, so retrieval still behaves sensibly.
"""
import hashlib
import math
import re

DIMENSIONS = 384
# Buckets per token: more than one smooths out hash collisions between words.
BUCKETS_PER_TOKEN = 4

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class FakeEmbedder:
    dimensions = DIMENSIONS

    def _encode_one(self, text: str) -> list[float]:
        vector = [0.0] * DIMENSIONS
        for token in _tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for i in range(BUCKETS_PER_TOKEN):
                chunk = digest[i * 4 : i * 4 + 4]
                index = int.from_bytes(chunk[:3], "big") % DIMENSIONS
                sign = 1.0 if chunk[3] & 1 else -1.0
                vector[index] += sign

        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0.0:
            # No tokens: return a fixed unit vector so cosine distance is defined.
            vector[0] = 1.0
            return vector
        return [v / norm for v in vector]

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self._encode_one(text) for text in texts]
