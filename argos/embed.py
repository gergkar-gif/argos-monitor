"""Stage 4a: embed title + lead of each article with multilingual-e5-small (ONNX, CPU)."""
import numpy as np

from .config import DATA_DIR

MODEL_DIR = DATA_DIR / "models" / "multilingual-e5-small"
MAX_TOKENS = 128
BATCH = 32
DIM = 384


def article_text(row):
    # e5 models expect a "passage: " prefix
    return "passage: " + (row["title"] + ". " + (row["lead"] or ""))[:800]


class Embedder:
    def __init__(self):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.tok = Tokenizer.from_file(str(MODEL_DIR / "tokenizer.json"))
        self.tok.enable_truncation(MAX_TOKENS)
        self.tok.enable_padding()
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 4
        self.sess = ort.InferenceSession(str(MODEL_DIR / "model.onnx"), opts, providers=["CPUExecutionProvider"])
        self.input_names = {i.name for i in self.sess.get_inputs()}

    def encode(self, texts):
        enc = self.tok.encode_batch(texts)
        ids = np.array([e.ids for e in enc], dtype=np.int64)
        mask = np.array([e.attention_mask for e in enc], dtype=np.int64)
        feeds = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self.input_names:
            feeds["token_type_ids"] = np.zeros_like(ids)
        hidden = self.sess.run(None, feeds)[0]                       # (batch, tokens, 384)
        m = mask[:, :, None].astype(np.float32)
        pooled = (hidden * m).sum(1) / m.sum(1)                      # mean pooling over real tokens
        return (pooled / np.linalg.norm(pooled, axis=1, keepdims=True)).astype(np.float32)


def run(db):
    rows = db.execute("SELECT a.id, a.title, a.lead FROM article a LEFT JOIN embedding e ON e.article_id=a.id "
                      "WHERE e.article_id IS NULL").fetchall()
    print(f"embed: {len(rows)} articles to embed")
    if not rows:
        return
    emb = Embedder()
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        vecs = emb.encode([article_text(r) for r in chunk])
        db.executemany("INSERT OR REPLACE INTO embedding VALUES (?,?)",
                       [(r["id"], v.tobytes()) for r, v in zip(chunk, vecs)])
        if (i // BATCH) % 20 == 0:
            db.commit()
            print(f"  {i + len(chunk)}/{len(rows)}")
    db.commit()
