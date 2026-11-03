"""Media political alignment, editorial leaning and factuality ratings.
Derived from public media-monitoring registries (Media Bias/Fact Check, AllSides, Reuters Institute, local watchdog data).
"""
import re

# Comprehensive registry of international wires, major global broadcasters, and monitored domestic outlets.
# bias: left | center-left | center | center-right | right | state_aligned | unrated
# alignment: independent | public_broadcaster | state_controlled | pro_government | opposition | unrated
# factuality: very_high | high | mostly_factual | mixed | unrated

RATINGS = {
    # --- International News Agencies & Wires ---
    "reuters": {"bias": "center", "alignment": "independent", "factuality": "very_high"},
    "associated press": {"bias": "center", "alignment": "independent", "factuality": "very_high"},
    "ap news": {"bias": "center", "alignment": "independent", "factuality": "very_high"},
    "afp": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "agence france-presse": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "bloomberg": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "bloomberg.com": {"bias": "center", "alignment": "independent", "factuality": "high"},

    # --- Major Global & Regional Broadcasters ---
    "bbc": {"bias": "center-left", "alignment": "public_broadcaster", "factuality": "high"},
    "bbc news": {"bias": "center-left", "alignment": "public_broadcaster", "factuality": "high"},
    "bbc world": {"bias": "center-left", "alignment": "public_broadcaster", "factuality": "high"},
    "dw": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "dw.com": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "deutsche welle": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "france 24": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "al jazeera": {"bias": "center-left", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "euronews": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "euronews.com": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "radio free europe": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "rfe/rl": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "radio free asia": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "rfa": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "voice of america": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "voa": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},

    # --- Anglo-American Major Press ---
    "financial times": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "the guardian": {"bias": "left", "alignment": "independent", "factuality": "high"},
    "the new york times": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "the washington post": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "the wall street journal": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "wsj": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "politico": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "the economist": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "the times": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "the telegraph": {"bias": "right", "alignment": "independent", "factuality": "mostly_factual"},
    "cnn": {"bias": "center-left", "alignment": "independent", "factuality": "mostly_factual"},
    "abc news": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "cbs news": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "nbc news": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "fox news": {"bias": "right", "alignment": "independent", "factuality": "mixed"},

    # --- State Wires & Authoritarian State Media ---
    "tass": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mixed"},
    "ria novosti": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mixed"},
    "rt": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mixed"},
    "sputnik": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mixed"},
    "xinhua": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mixed"},
    "global times": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mixed"},
    "cgtn": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mixed"},
    "anadolu agency": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mixed"},
    "anadolu ajansı": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mixed"},
    "trt world": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},

    # --- Central Europe: Czechia, Slovakia, Hungary, Poland (V4) ---
    # Czechia
    "irozhlas": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "český rozhlas": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "čt24": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "česká televize": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "čtk": {"bias": "center", "alignment": "state_controlled", "factuality": "high"},
    "seznam zprávy": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "seznam zpravy": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "novinky.cz": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "novinky": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "deník n": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "denik n": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "respekt": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "hospodářské noviny": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "prague morning": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "echo24": {"bias": "center-right", "alignment": "independent", "factuality": "mostly_factual"},

    # Slovakia
    "aktuality.sk": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "aktuality": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "sme.sk": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "the slovak spectator": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "pravda": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "pravda.sk": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "tasr": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "high"},
    "teraz.sk": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "high"},
    "stvr": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "rtvs": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},

    # Hungary
    "telex": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "444": {"bias": "left", "alignment": "independent", "factuality": "high"},
    "444.hu": {"bias": "left", "alignment": "independent", "factuality": "high"},
    "hvg": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "24.hu": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "válasz online": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "átlátszó": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "the budapest times": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "budapest business journal": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "magyar nemzet": {"bias": "right", "alignment": "pro_government", "factuality": "mixed"},
    "origo": {"bias": "right", "alignment": "pro_government", "factuality": "mixed"},
    "mti": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "hirado.hu": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mixed"},
    "mandiner": {"bias": "right", "alignment": "pro_government", "factuality": "mixed"},
    "index": {"bias": "center-right", "alignment": "pro_government", "factuality": "mostly_factual"},

    # Poland
    "gazeta wyborcza": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "wyborcza": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "tvn24": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "onet": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "rzeczpospolita": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "pap": {"bias": "center", "alignment": "state_controlled", "factuality": "high"},
    "polska agencja prasowa": {"bias": "center", "alignment": "state_controlled", "factuality": "high"},
    "tvp world": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "do rzeczy": {"bias": "right", "alignment": "opposition", "factuality": "mostly_factual"},
    "wpolityce": {"bias": "right", "alignment": "opposition", "factuality": "mixed"},

    # --- Vietnam ---
    "vnexpress": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "vnexpress international": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "tuoi tre": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "tuổi trẻ": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "tuoi tre news": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "thanh nien": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "thanh niên": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "dan tri": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "dân trí": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "vietnamnet": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "vietnamplus": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "high"},
    "nhan dan": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "nhân dân": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "vietnam news": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "high"},
    "vietnam investment review": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "high"},
    "vietnam.vn": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "luật khoa tạp chí": {"bias": "center-left", "alignment": "opposition", "factuality": "high"},
    "the vietnamese magazine": {"bias": "center-left", "alignment": "opposition", "factuality": "high"},

    # --- Turkey ---
    "birgün": {"bias": "left", "alignment": "opposition", "factuality": "mostly_factual"},
    "cumhuriyet": {"bias": "center-left", "alignment": "opposition", "factuality": "mostly_factual"},
    "evrensel": {"bias": "left", "alignment": "opposition", "factuality": "mostly_factual"},
    "daily sabah": {"bias": "right", "alignment": "pro_government", "factuality": "mixed"},
    "yeni şafak": {"bias": "right", "alignment": "pro_government", "factuality": "mixed"},
    "hürriyet daily news": {"bias": "center-right", "alignment": "pro_government", "factuality": "mostly_factual"},

    # --- Japan, South Korea, Taiwan ---
    "the japan times": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "nikkei asia": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "asahi shimbun": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "mainichi shimbun": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "yonhap": {"bias": "center", "alignment": "state_controlled", "factuality": "high"},
    "yonhap news agency": {"bias": "center", "alignment": "state_controlled", "factuality": "high"},
    "the korea times": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "the korea herald": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "korea joongang daily": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "taipei times": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "taiwan news": {"bias": "center", "alignment": "independent", "factuality": "mostly_factual"},
    "liberty times": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "central news agency": {"bias": "center", "alignment": "state_controlled", "factuality": "high"},

    # --- South Africa & Africa ---
    "daily maverick": {"bias": "center-left", "alignment": "independent", "factuality": "very_high"},
    "mail & guardian": {"bias": "left", "alignment": "independent", "factuality": "high"},
    "news24": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "sabc": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "sanews": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "high"},
    "daily nation": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "the standard": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "premium times": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "the cable": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "punch": {"bias": "center", "alignment": "independent", "factuality": "mostly_factual"},
    "vanguard": {"bias": "center", "alignment": "independent", "factuality": "mostly_factual"},
    "addis standard": {"bias": "center-left", "alignment": "independent", "factuality": "high"},

    # --- Latin America: Argentina, Brazil, Colombia ---
    "infobae": {"bias": "center-right", "alignment": "independent", "factuality": "mostly_factual"},
    "la nación": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "la nacion": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "clarín": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "clarin": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "ámbito financiero": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "ambito financiero": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "el cronista": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "página 12": {"bias": "left", "alignment": "opposition", "factuality": "mostly_factual"},
    "pagina 12": {"bias": "left", "alignment": "opposition", "factuality": "mostly_factual"},
    "folha de s.paulo": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "folha": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "g1": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "o globo": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "globo": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "poder360": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "cartacapital": {"bias": "left", "alignment": "independent", "factuality": "mostly_factual"},
    "nexo jornal": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "el tiempo": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "el espectador": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "semana": {"bias": "right", "alignment": "opposition", "factuality": "mostly_factual"},
    "la silla vacía": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "la silla vacia": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "insight crime": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "el país": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "el pais": {"bias": "center-left", "alignment": "independent", "factuality": "high"},

    # --- Balkans & South Caucasus ---
    "oslobođenje": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "oslobodjenje": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "istraga.ba": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "klix.ba": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "klix": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "danas": {"bias": "center-left", "alignment": "opposition", "factuality": "high"},
    "n1": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "nova.rs": {"bias": "center-left", "alignment": "opposition", "factuality": "mostly_factual"},
    "b92": {"bias": "center-right", "alignment": "pro_government", "factuality": "mostly_factual"},
    "politika": {"bias": "center-right", "alignment": "pro_government", "factuality": "mostly_factual"},
    "koha ditore": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "kallxo": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "hetq": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "civilnet": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "factor.am": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "oc media": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "jamnews": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "meydan tv": {"bias": "center-left", "alignment": "opposition", "factuality": "high"},

    # --- Southeast Asia (Regional) ---
    "camboja news": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "vod khmer": {"bias": "center-left", "alignment": "opposition", "factuality": "high"},
    "bangkok post": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "the nation": {"bias": "center-right", "alignment": "independent", "factuality": "mostly_factual"},
    "prachatai": {"bias": "center-left", "alignment": "opposition", "factuality": "high"},
    "malaysiakini": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "the star": {"bias": "center-right", "alignment": "pro_government", "factuality": "mostly_factual"},
    "free malaysia today": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "the jakarta post": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "kompas": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "tempo": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "antaranews": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "high"},
    "rappler": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "philippine daily inquirer": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "inquirer": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "philstar": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "the straits times": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "straits times": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "philippine news agency": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "pna": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "bernama": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "khmer times": {"bias": "state_aligned", "alignment": "pro_government", "factuality": "mixed"},
    "global new light of myanmar": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mixed"},

    # --- Regional & Aggregator Wires (Central Asia, Caucasus, Balkans, Africa) ---
    "радио-телевизија војводине": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "rtv vojvodina": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "rtv": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "акиpress": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "akipress": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "gazeta express": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "kossev": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "kosovapress": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "radio slobodna evropa": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "rtrs": {"bias": "right", "alignment": "state_controlled", "factuality": "mixed"},
    "armenpress": {"bias": "center", "alignment": "state_controlled", "factuality": "high"},
    "1tv": {"bias": "center", "alignment": "public_broadcaster", "factuality": "high"},
    "moldpres": {"bias": "center", "alignment": "state_controlled", "factuality": "high"},
    "cotidianul": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "g4media": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "vlast": {"bias": "center-left", "alignment": "independent", "factuality": "high"},
    "qazinform": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "high"},
    "kazinform": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "high"},
    "uza": {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"},
    "uzdaily": {"bias": "center", "alignment": "independent", "factuality": "mostly_factual"},
    "trend news agency": {"bias": "state_aligned", "alignment": "pro_government", "factuality": "mostly_factual"},
    "trend": {"bias": "state_aligned", "alignment": "pro_government", "factuality": "mostly_factual"},
    "apa": {"bias": "state_aligned", "alignment": "pro_government", "factuality": "mostly_factual"},
    "report": {"bias": "state_aligned", "alignment": "pro_government", "factuality": "mostly_factual"},
    "azernews": {"bias": "state_aligned", "alignment": "pro_government", "factuality": "mostly_factual"},
    "news agency of nigeria": {"bias": "center", "alignment": "state_controlled", "factuality": "high"},
    "nan": {"bias": "center", "alignment": "state_controlled", "factuality": "high"},
    "the eastafrican": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "iol": {"bias": "center-left", "alignment": "independent", "factuality": "mostly_factual"},
    "turkish minute": {"bias": "center-left", "alignment": "opposition", "factuality": "high"},
    "kyodo": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "kyodo news": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "focus taiwan": {"bias": "center", "alignment": "state_controlled", "factuality": "high"},
    "chosun": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "chosunbiz": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "chosun ilbo": {"bias": "center-right", "alignment": "independent", "factuality": "high"},
    "portfolio": {"bias": "center", "alignment": "independent", "factuality": "high"},
    "világgazdaság": {"bias": "right", "alignment": "pro_government", "factuality": "mixed"},
    "vilaggazdasag": {"bias": "right", "alignment": "pro_government", "factuality": "mixed"},
    "rtvc noticias": {"bias": "center-left", "alignment": "public_broadcaster", "factuality": "high"},
}


def clean_name(name):
    n = re.split(r"\s+[|\-–—·]\s+|\s*\(", str(name or "").lower())[0].strip()
    n = re.sub(r"^(the|báo|gazeta)\s+", "", n).strip()
    return re.sub(r"\.(hu|sk|cz|kz|uz|md|ge|az|rs|vn|com|org|net|tv|ro|pl|kg)$", "", n).strip()


_COMPILED_PATTERNS = [
    (re.compile(r"\b" + re.escape(pat) + r"\b"), r)
    for pat, r in RATINGS.items()
    if len(pat) >= 4
]


def lookup_rating(name, state_affiliated=False, kind="media"):
    """Lookup media rating by name with normalization and intelligent fallback."""
    nl = str(name or "").lower().strip()
    cl = clean_name(nl)
    if nl in RATINGS:
        return RATINGS[nl]
    if cl in RATINGS:
        return RATINGS[cl]
    for reg, r in _COMPILED_PATTERNS:
        if reg.search(nl) or reg.search(cl):
            return r

    # Government portal domain patterns (.gov, .gob)
    if re.search(r"\.(gov|gob)(\.[a-z]{2})?$", nl) or nl.endswith(".gov") or nl.endswith(".gob"):
        return {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "high"}

    # Fallback heuristics based on structural properties
    if state_affiliated or kind == "official":
        return {"bias": "state_aligned", "alignment": "state_controlled", "factuality": "mostly_factual"}
    return {"bias": "unrated", "alignment": "independent", "factuality": "unrated"}
