"""Stage 6a: English machine translation of the headlines shown on the dashboard (decision D11).

Runs offline on CPU via MarianMT (Helsinki-NLP/opus-mt-*) models.
Translations are strictly reading aids: the dashboard always shows or links to the original headline.
Cached in the SQLite `translation` table so no headline is ever translated twice.
"""
import gc
import os
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

# Post-processing glossary to fix known archaic/Sino-Vietnamese and literal Hungarian mappings in Marian
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
    "hu": [
        (r"\b(?:Hungarian|Magyar)\s+P(?:eter|éter)\b", "Péter Magyar"),
        (r"\bP(?:eter|éter)\s+Hungarian\b", "Péter Magyar"),
        (r"\bTisza\s+[Pp]arty\b", "Tisza Party"),
        (r"\bFriendship\s+(?:oil\s+)?pipeline\b", "Druzhba oil pipeline"),
        (r"\bSovereignty\s+Protection\s+Office\b", "Sovereignty Protection Office"),
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
        import torch
        batch = tok(texts, return_tensors="pt", padding=True, truncation=True, max_length=128)
        with torch.inference_mode():
            gen = model.generate(**batch, max_length=128, num_beams=1)
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
    per_lang_limit = int(os.environ.get("ARGOS_TRANSLATE_LIMIT", "150"))
    rows = db.execute(
        "SELECT a.id, a.title, a.language, MAX(COALESCE(s.score, 0.0)) AS max_score "
        "FROM story s JOIN article a ON a.id=s.representative_article_id "
        "WHERE a.language != 'en' AND a.id NOT IN (SELECT article_id FROM translation) "
        "GROUP BY a.id ORDER BY max_score DESC"
    ).fetchall()

    by_lang = {}
    for r in rows:
        lang = r["language"]
        if lang in MODELS and len(by_lang.get(lang, ())) < per_lang_limit:
            by_lang.setdefault(lang, []).append(r)

    total_todo = sum(len(v) for v in by_lang.values())
    print(f"translate: {total_todo} non-English headlines to translate across {len(by_lang)} languages")
    if not total_todo:
        return

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
        # Release one language's MarianMT weights before loading the next to stay within CI RAM limits.
        _LOADED_MODELS.pop(lang, None)
        del translator
        gc.collect()

    print(f"translate: {total_translated} translations saved in database")
