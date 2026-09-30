"""Stage 6a: English machine translation of the headlines shown on the dashboard (decision D11).

Runs locally through Ollama and is cached in the `translation` table. The translation is a reading aid
only: the dashboard always shows the original headline next to it and labels it as machine translation.
"""
import json
import re
import urllib.request

from .rank import dashboard_story_ids

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:3b-instruct"
PROMPT = ("Translate this news headline from {lang} into short, natural English. "
          "Reply with the English headline only: no quotes, no explanation, and do not add words such as 'Headlines'. "
          "Keep every name and number exactly. Use this glossary:\n"
          "Tổng Bí thư = General Secretary; Chủ tịch nước = State President; Thủ tướng = Prime Minister; "
          "Quốc hội = National Assembly; Bộ Chính trị = Politburo; Chính phủ = Government; Thứ trưởng = Deputy Minister; "
          "nghìn = thousand; triệu = million; tỷ = billion (tỷ đồng = billion dong); TP.HCM / TP HCM = Ho Chi Minh City; "
          "bị đề nghị N năm tù = prosecutors seek N years in prison.\n\n"
          "Example: 'Tổng Bí thư, Chủ tịch nước Tô Lâm dự Lễ khởi công dự án' -> "
          "'General Secretary and State President To Lam attends project groundbreaking'\n"
          "Example: 'Chi 1,4 tỷ đồng chạy án' -> 'Pays 1.4 billion dong to fix a case'\n\n"
          "Headline: {title}")


def translate_one(title, lang):
    body = json.dumps({"model": MODEL, "stream": False, "keep_alive": "5m",
                       "options": {"temperature": 0},
                       "prompt": PROMPT.format(lang="Vietnamese" if lang == "vi" else lang, title=title)}).encode()
    req = urllib.request.Request(OLLAMA_URL, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        text = json.loads(r.read())["response"].strip().strip('"').split("\n")[0]
    if re.search(r"[　-鿿가-힯]", text):    # small models sometimes slip into Chinese mid-sentence
        return None
    return text


def run(db):
    ids = dashboard_story_ids(db)
    rows = db.execute(
        "SELECT a.id, a.title, a.language FROM story s JOIN article a ON a.id=s.representative_article_id "
        f"WHERE s.id IN ({','.join('?' * len(ids))}) AND a.language != 'en' "
        "AND a.id NOT IN (SELECT article_id FROM translation)", ids).fetchall()
    print(f"translate: {len(rows)} headlines to translate ({len(ids)} dashboard stories)")
    try:
        for i, r in enumerate(rows, 1):
            en = translate_one(r["title"], r["language"])
            if en is None:
                continue                                       # rejected: shows no translation rather than a broken one
            db.execute("INSERT OR REPLACE INTO translation VALUES (?,?,?)", (r["id"], en, MODEL))
            db.commit()
            if i % 10 == 0:
                print(f"  {i}/{len(rows)}")
    except OSError as e:
        print(f"translate: could not reach Ollama at {OLLAMA_URL} ({e}). Start Ollama and run this stage again.")
