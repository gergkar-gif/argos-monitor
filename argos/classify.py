"""Stage 5a: give each story a category (decision D8: section feeds first, then embeddings).

1. If most of a story's articles come from an economics, foreign-policy or defence-security section
   feed, the story gets that category. Those sections are reliable.
2. Otherwise (Thời sự, Pháp luật, Xã hội and other catch-all sections, or no section) the story is
   compared with a short description of each category, using the same embedding model.
3. If nothing is close enough, the category is 'other'.
"""
from collections import Counter

import numpy as np

from .embed import DIM, Embedder

RELIABLE = ("economics", "foreign_policy", "defence_security")
SECTION_SHARE = 0.5     # share of a story's articles needed for a section hint to decide
MIN_SIMILARITY = 0.80   # below this, a story fits no category description

# Several short descriptions per category; their embeddings are averaged.
DESCRIPTIONS = {
    "internal_politics": [
        "Đảng, Quốc hội, Chính phủ, Bộ Chính trị, Ban Chấp hành Trung ương",
        "nhân sự, bổ nhiệm, kỷ luật cán bộ, chống tham nhũng, khởi tố quan chức",
        "luật, nghị quyết, chính sách của Nhà nước, bầu cử, đại hội Đảng",
        "Tổng Bí thư chỉ đạo, Ủy ban Kiểm tra Trung ương, thi hành kỷ luật Đảng viên",
        "Vietnam Communist Party, National Assembly, government personnel, anti-corruption, legislation",
    ],
    "economics": [
        "kinh tế, tăng trưởng GDP, lạm phát, lãi suất, ngân hàng",
        "giá vàng, giá xăng dầu, chứng khoán, tỷ giá",
        "doanh nghiệp, đầu tư, xuất nhập khẩu, thương mại, thuế",
        "hạ tầng giao thông, cao tốc, sân bay, dự án đầu tư công, bất động sản",
        "Vietnam economy, GDP growth, exports, banks, business, investment, trade, infrastructure projects",
    ],
    "foreign_policy": [
        "quan hệ ngoại giao, thăm cấp nhà nước, hội đàm, hiệp định, đối tác chiến lược",
        "Biển Đông, ASEAN, Liên Hợp Quốc, Trung Quốc, Hoa Kỳ quan hệ với Việt Nam",
        "Thủ tướng tiếp Bộ trưởng nước ngoài, tiếp đại sứ, chuyến thăm chính thức, hợp tác song phương",
        "Vietnam foreign relations, diplomacy, visit, bilateral cooperation, ASEAN, South China Sea",
    ],
    "defence_security": [
        "quân đội, quốc phòng, tập trận, lực lượng vũ trang, biên phòng",
        "an ninh mạng, tình báo, khủng bố, an ninh quốc gia, chiến tranh",
        "Quân ủy Trung ương, Bộ Quốc phòng, Bộ Công an, Quân đội nhân dân Việt Nam",
        "Vietnam military, defence, national security, armed forces, cybersecurity",
    ],
    "society": [
        "giáo dục, học sinh, trường học, thi cử, giáo viên",
        "y tế, bệnh viện, dịch bệnh, vaccine, sức khỏe",
        "tai nạn giao thông, thiên tai, bão lũ, thời tiết, môi trường",
        "vụ án, xét xử, bắt giữ, lừa đảo, tội phạm, đời sống người dân",
        "Vietnam society, education, health, weather, disasters, crime, culture, sports",
    ],
}


def _prototypes():
    emb = Embedder()
    names, vecs = [], []
    for cat, texts in DESCRIPTIONS.items():
        v = emb.encode(["passage: " + t for t in texts]).mean(0)
        names.append(cat)
        vecs.append(v / np.linalg.norm(v))
    return names, np.array(vecs)


def run(db, min_similarity=MIN_SIMILARITY):
    names, protos = _prototypes()
    stories = [r[0] for r in db.execute("SELECT id FROM story")]
    counts, sims = Counter(), []
    for sid in stories:
        rows = db.execute("SELECT f.category_hint, e.vec FROM story_article sa JOIN article a ON a.id=sa.article_id "
                          "JOIN embedding e ON e.article_id=a.id LEFT JOIN feed f ON f.id=a.feed_id "
                          "WHERE sa.story_id=?", (sid,)).fetchall()
        hints = Counter(r["category_hint"] for r in rows if r["category_hint"] in RELIABLE)
        top, n = hints.most_common(1)[0] if hints else (None, 0)
        if top and n / len(rows) >= SECTION_SHARE:
            cat = top
        else:
            centroid = np.frombuffer(b"".join(r["vec"] for r in rows), dtype=np.float32).reshape(len(rows), DIM).mean(0)
            centroid /= np.linalg.norm(centroid)
            s = protos @ centroid
            best = int(np.argmax(s))
            sims.append(float(s[best]))
            cat = names[best] if s[best] >= min_similarity else "other"
        db.execute("UPDATE story SET category=? WHERE id=?", (cat, sid))
        counts[cat] += 1
    db.commit()
    print("classify:", dict(counts))
    if sims:
        print(f"  embedding-classified stories: {len(sims)}, similarity to best category: "
              f"median {np.median(sims):.3f}, 10th percentile {np.percentile(sims, 10):.3f}")
