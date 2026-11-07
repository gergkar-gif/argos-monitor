"""Stage 6a: English machine translation of the headlines shown on the dashboard (decision D11).

Runs offline on CPU via MarianMT (Helsinki-NLP/opus-mt-*) models.
Translations are strictly reading aids: the dashboard always shows or links to the original headline.
Cached in the SQLite `translation` table so no headline is ever translated twice.
"""
import re
from .rank import dashboard_story_ids

# Map language codes to dedicated Marian MT models
MODELS = {
    "vi": "Helsinki-NLP/opus-mt-vi-en",
    "hu": "Helsinki-NLP/opus-mt-hu-en",
    "uk": "Helsinki-NLP/opus-mt-uk-en",
    "ru": "Helsinki-NLP/opus-mt-ru-en",
    "es": "Helsinki-NLP/opus-mt-es-en",
    "de": "Helsinki-NLP/opus-mt-de-en",
    "fr": "Helsinki-NLP/opus-mt-fr-en",
    "it": "Helsinki-NLP/opus-mt-it-en",
    "id": "Helsinki-NLP/opus-mt-id-en",
    "ar": "Helsinki-NLP/opus-mt-ar-en",
}

# Post-processing glossary to fix known archaic/Sino-Vietnamese mappings in Marian
GLOSSARY = {
    "vi": [
        (r"\bSong Lin\b", "To Lam"),
        (r"\bPresident Song Lin\b", "General Secretary To Lam"),
        (r"\bGeneral Secretary of the State President\b", "General Secretary and State President"),
        (r"\bPham Minh Zheng\b", "Pham Minh Chinh"),
        (r"\bZheng\b", "Chinh"),
        (r"\bNguyen Phu Focus\b", "Nguyen Phu Trong"),
        (r"\bTran Thanh Man\b", "Tran Thanh Man"),
        (r"\bLuang Cuong\b", "Luong Cuong"),
        (r"\bBao Gia\b", "Gia Lai"),
    ],
    "uk": [
        (r"\b(\w\.\s*){3,}", ""),
    ]
}

_LOADED_MODELS = {}


def get_translator(lang):
    model_name = MODELS.get(lang)
    if not model_name:
        return None
    if lang not in _LOADED_MODELS:
        try:
            from transformers import MarianMTModel, MarianTokenizer
            tok = MarianTokenizer.from_pretrained(model_name)
            model = MarianMTModel.from_pretrained(model_name)
            _LOADED_MODELS[lang] = (tok, model, model_name)
        except Exception as e:
            print(f"translate: could not load model {model_name} for {lang}: {e}")
            _LOADED_MODELS[lang] = None
    return _LOADED_MODELS[lang]


def translate_batch(texts, lang):
    translator = get_translator(lang)
    if not translator or not texts:
        return [None] * len(texts)
    tok, model, model_name = translator
    try:
        batch = tok(texts, return_tensors="pt", padding=True, truncation=True, max_length=128)
        gen = model.generate(**batch, max_length=128, num_beams=2)
        outputs = tok.batch_decode(gen, skip_special_tokens=True)
    except Exception as e:
        print(f"translate: batch generation failed for {lang}: {e}")
        return [None] * len(texts)

    cleaned = []
    glossary_rules = GLOSSARY.get(lang, [])
    for out in outputs:
        res = out.strip()
        for pat, repl in glossary_rules:
            res = re.sub(pat, repl, res)
        if len(res) < 5 or re.search(r"[　-鿿가-힯]", res):
            cleaned.append(None)
        else:
            cleaned.append(res)
    return cleaned


def run(db):
    ids = dashboard_story_ids(db)
    if not ids:
        return
    rows = []
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        rows.extend(db.execute(
            "SELECT a.id, a.title, a.language FROM story s JOIN article a ON a.id=s.representative_article_id "
            f"WHERE s.id IN ({','.join('?' * len(chunk))}) AND a.language != 'en' "
            "AND a.id NOT IN (SELECT article_id FROM translation)", chunk).fetchall())

    todo = [r for r in rows if r["language"] in MODELS]
    print(f"translate: {len(todo)} non-English headlines to translate across {len(set(r['language'] for r in todo))} languages")
    if not todo:
        return

    by_lang = {}
    for r in todo:
        by_lang.setdefault(r["language"], []).append(r)

    total_translated = 0
    for lang, items in by_lang.items():
        translator = get_translator(lang)
        if not translator:
            continue
        _, _, model_name = translator
        for i in range(0, len(items), 16):
            chunk = items[i:i + 16]
            titles = [c["title"] for c in chunk]
            translations = translate_batch(titles, lang)
            inserts = []
            for c, tr in zip(chunk, translations):
                if tr:
                    inserts.append((c["id"], tr, model_name))
            if inserts:
                db.executemany("INSERT OR REPLACE INTO translation VALUES (?,?,?)", inserts)
                db.commit()
                total_translated += len(inserts)
        print(f"translate: {lang}: {len(items)} headlines processed")

    print(f"translate: {total_translated} translations saved in database")
