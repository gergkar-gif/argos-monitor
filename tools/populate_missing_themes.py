"""Populate native-language themes.yaml for the 27 desks identified in the quality audit.
Adheres strictly to the pattern established in countries/hungary/themes.yaml and countries/france/themes.yaml.
"""
import pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
COUNTRIES_DIR = ROOT / "countries"

DESK_THEMES = {
    "algeria": {
        "themes": [
            {"id": "elections", "keywords": ["élection", "présidentielle", "vote", "scrutin", "انتخابات", "اقتراع", "تصويت"]},
            {"id": "diplomacy", "keywords": ["visite d'état", "partenariat", "ambassadeur", "attaf", "tebboune", "sahara occidental", "زيارة دولة", "دبلوماسية", "سفير", "عطاف"]},
            {"id": "econ_policy", "keywords": ["hydrocarbures", "sonatrach", "gaz naturel", "pétrole", "budget", "dinar", "محروقات", "سوناطراك", "غاز", "نفط", "دينار"]},
            {"id": "party_gov", "keywords": ["conseil des ministres", "apn", "assemblée populaire nationale", "gouvernement", "مجلس الوزراء", "المجلس الشعبي الوطني", "حكومة"]},
            {"id": "security", "keywords": ["anp", "armée nationale populaire", "frontières", "terrorisme", "الجيش الوطني الشعبي", "مكافحة الإرهاب"]},
        ]
    },
    "austria": {
        "themes": [
            {"id": "elections", "keywords": ["nationalratswahl", "bundesrat", "wahl", "stimmen", "kickl", "nehammer", "koalition"]},
            {"id": "party_gov", "keywords": ["nationalrat", "bundeskanzler", "övp", "fpö", "spö", "neos", "grüne", "ministerrat"]},
            {"id": "econ_policy", "keywords": ["inflation", "budgetdefizit", "oenb", "zinsen", "schulden", "steuern", "wifo"]},
            {"id": "diplomacy", "keywords": ["neutralität", "eu-ratspräsidentschaft", "osze", "wien-diplomatie", "botschafter"]},
            {"id": "security", "keywords": ["bundesheer", "staatsvertrag", "neutralität", "sicherheitsstrategie"]},
        ]
    },
    "baltics": {
        "themes": [
            {"id": "elections", "keywords": ["riigikogu", "saeima", "seimas", "election", "parliamentary poll", "valimised", "vēlēšanas", "rinkimai"]},
            {"id": "security", "keywords": ["nato eastern flank", "suwalki gap", "baltic air policing", "defence spending", "border security", "kaitsevägi", "aizsardzības spēki", "kariuomenė"]},
            {"id": "diplomacy", "keywords": ["baltic assembly", "nordic-baltic eight", "nb8", "ukraine aid", "eu sanctions"]},
            {"id": "econ_policy", "keywords": ["rail baltica", "energy synchronization", "inflation", "lng klaipeda", "desynchronization"]},
            {"id": "party_gov", "keywords": ["prime minister", "coalition", "tallinn", "riga", "vilnius", "valitsus", "valdība", "vyriausybė"]},
        ]
    },
    "bangladesh": {
        "themes": [
            {"id": "elections", "keywords": ["election roadmap", "interim poll", "voter list", "electoral reform", "নির্বাচন", "ভোট"]},
            {"id": "party_gov", "keywords": ["interim government", "chief adviser", "muhammad yunus", "advisory council", "awami league", "bnp", "অন্তর্বর্তী সরকার", "ইউনূস"]},
            {"id": "econ_policy", "keywords": ["rmg", "garments", "forex reserves", "bangladesh bank", "imf loan", "inflation", "রেমিট্যান্স", "মুদ্রাস্ফীতি"]},
            {"id": "security", "keywords": ["law and order", "bgb", "rapid action battalion", "police reform", "সীমান্ত নিরাপত্তা"]},
            {"id": "diplomacy", "keywords": ["rohingya repatriation", "teesta river", "india-bangladesh ties", "diplomatic mission"]},
        ]
    },
    "belgium": {
        "themes": [
            {"id": "elections", "keywords": ["élections fédérales", "verkiezingen", "scrutin", "arizona coalition", "formateur"]},
            {"id": "party_gov", "keywords": ["gouvernement fédéral", "chambre des représentants", "de wever", "premier ministre", "vlaamse regering", "wallonie", "bruxelles"]},
            {"id": "econ_policy", "keywords": ["déficit budgétaire", "dette publique", "ue procédure", "begroting", "inflatie", "pension reform"]},
            {"id": "diplomacy", "keywords": ["otan", "union européenne", "siège otan", "diplomatie belge", "eu presidency"]},
            {"id": "security", "keywords": ["défense belge", "armée", "sécurité portuaire", "anvers drogue", "lutte contre le terrorisme"]},
        ]
    },
    "caribbean": {
        "themes": [
            {"id": "elections", "keywords": ["general election", "electoral commission", "ballot", "parliamentary majority", "caricom election"]},
            {"id": "diplomacy", "keywords": ["caricom", "heads of government", "cuba-caribbean ties", "haiti transitional council", "un general assembly"]},
            {"id": "econ_policy", "keywords": ["climate finance", "loss and damage", "debt relief", "imf program", "tourism revenue", "petrocaribe"]},
            {"id": "security", "keywords": ["regional security system", "rss", "arms trafficking", "haiti security mission", "coast guard"]},
            {"id": "party_gov", "keywords": ["prime minister", "cabinet", "house of assembly", "kingston", "port of spain", "nassau"]},
        ]
    },
    "central_america": {
        "themes": [
            {"id": "elections", "keywords": ["elecciones", "comicios", "tribunal electoral", "segunda vuelta", "votos"]},
            {"id": "party_gov", "keywords": ["bukele", "arévalo", "asamblea legislativa", "congreso nacional", "régimen de excepción", "gabinete"]},
            {"id": "econ_policy", "keywords": ["remesas", "canal de panamá", "inflación", "banco central", "tlc", "inversión extranjera"]},
            {"id": "security", "keywords": ["maras", "pandillas", "seguridad fronteriza", "crimen organizado", "narcotráfico", "policía nacional"]},
            {"id": "diplomacy", "keywords": ["sica", "migración irregular", "relaciones con eeuu", "cumbre regional", "cancillería"]},
        ]
    },
    "chile": {
        "themes": [
            {"id": "elections", "keywords": ["elección presidencial", "plebiscito", "servel", "votos", "congreso nacional", "municipales"]},
            {"id": "party_gov", "keywords": ["boric", "gabriel boric", "la moneda", "senado", "cámara de diputadas y diputados", "gabinete"]},
            {"id": "econ_policy", "keywords": ["litio", "cobre", "codelco", "reforma previsional", "banco central", "ipc", "pacto fiscal"]},
            {"id": "security", "keywords": ["estado de excepción", "macrozona sur", "crimen organizado", "tren de aragua", "carabineros"]},
            {"id": "diplomacy", "keywords": ["cancillería", "van klaveren", "acuerdo unión europea", "alianza del pacífico", "antártica"]},
        ]
    },
    "denmark": {
        "themes": [
            {"id": "elections", "keywords": ["folketingsvalg", "stemmer", "valg", "partileder", "regeringsdannelse"]},
            {"id": "party_gov", "keywords": ["folketinget", "mette frederiksen", "regeringen", "statsministeriet", "svm-regeringen"]},
            {"id": "econ_policy", "keywords": ["novo nordisk", "nationalbanken", "inflation", "finanslov", "rente", "danske bank"]},
            {"id": "security", "keywords": ["forsvarsforlig", "forsvaret", "nato-mål", "værnepligt", "arktisk kommando", "grønland"]},
            {"id": "diplomacy", "keywords": ["rigsfællesskabet", "grønland", "færøerne", "udenrigsministeriet", "larskøkke"]},
        ]
    },
    "east_africa": {
        "themes": [
            {"id": "elections", "keywords": ["general election", "iebc", "electoral commission", "ballot", "uchaguzi"]},
            {"id": "party_gov", "keywords": ["ruto", "museveni", "suluhu", "kagame", "national assembly", "serikali"]},
            {"id": "econ_policy", "keywords": ["eac integration", "shilling", "central bank", "inflation", "kenya revenue authority", "drought relief"]},
            {"id": "security", "keywords": ["al-shabaab", "amison", "atmis", "drc peacekeeping", "sudan peace talks", "somalia security"]},
            {"id": "diplomacy", "keywords": ["east african community", "intergovernmental authority", "igad", "state visit", "african union"]},
        ]
    },
    "ecuador": {
        "themes": [
            {"id": "elections", "keywords": ["elecciones generales", "cne", "votos", "segunda vuelta", "papeleta"]},
            {"id": "party_gov", "keywords": ["daniel noboa", "noboa", "asamblea nacional", "carondelet", "decreto ejecutivo"]},
            {"id": "security", "keywords": ["conflicto armado interno", "estado de excepción", "fuerzas armadas", "cárceles", "bandas terroristas", "bloque de seguridad"]},
            {"id": "econ_policy", "keywords": ["crisis energética", "apagones", "cortes de luz", "fmi", "dolarización", "banco central"]},
            {"id": "diplomacy", "keywords": ["relaciones diplomáticas", "cancillería", "cooperación en seguridad", "comunidad andina"]},
        ]
    },
    "greece": {
        "themes": [
            {"id": "elections", "keywords": ["εκλογές", "βουλή", "ψηφοφορία", "κάλπη", "δημοσκόπηση", "νέα δημοκρατία", "πασοκ", "συριζα"]},
            {"id": "party_gov", "keywords": ["κυβέρνηση", "μητσοτάκης", "υπουργικό συμβούλιο", "βουλή των ελλήνων", "νομοσχέδιο"]},
            {"id": "diplomacy", "keywords": ["ελληνοτουρκικά", "αιγαίο", "κυπριακό", "υπουργείο εξωτερικών", "γεραπετρίτης", "ευρωπαϊκή ένωση"]},
            {"id": "econ_policy", "keywords": ["τράπεζα της ελλάδος", "πρωτογενές πλεόνασμα", "πληθωρισμός", "επενδυτική βαθμίδα", "τουρισμός", "ναυτιλία"]},
            {"id": "security", "keywords": ["ένοπλες δυνάμεις", "belharra", "rafale", "αμυντική συμφωνία", "μεταναστευτικό", "λιμενικό"]},
        ]
    },
    "iraq": {
        "themes": [
            {"id": "elections", "keywords": ["انتخابات مجالس المحافظات", "مجلس النواب", "اقتراع", "مفوضية الانتخابات", "مرشح"]},
            {"id": "party_gov", "keywords": ["محمد شياع السوداني", "السوداني", "مجلس الوزراء", "البرلمان العراقي", "ائتلاف إدارة الدولة"]},
            {"id": "security", "keywords": ["الحشد الشعبي", "مكافحة الإرهاب", "داعش", "التحالف الدولي", "البيشمركة", "قوات حرس الحدود"]},
            {"id": "econ_policy", "keywords": ["نفط العراق", "شركة سومو", "سعر صرف الدولار", "البنك المركزي العراقي", "موازنة الدولة"]},
            {"id": "diplomacy", "keywords": ["العلاقات العراقية الأمريكية", "طريق التنمية", "الوساطة الإقليمية", "وزارة الخارجية"]},
        ]
    },
    "ireland": {
        "themes": [
            {"id": "elections", "keywords": ["general election", "dail eireann", "taoiseach", "polling", "constituency", "tanaiste"]},
            {"id": "party_gov", "keywords": ["simon harris", "fianna fail", "fine gael", "sinn fein", "oireachtas", "government buildings"]},
            {"id": "econ_policy", "keywords": ["corporate tax", "housing crisis", "budget surplus", "central bank of ireland", "cost of living"]},
            {"id": "diplomacy", "keywords": ["good friday agreement", "northern ireland", "brexit", "eu single market", "gaza recognition"]},
            {"id": "security", "keywords": ["defence forces", "neutrality debate", "triple lock", "cybersecurity", "garda"]},
        ]
    },
    "jordan": {
        "themes": [
            {"id": "elections", "keywords": ["parliamentary election", "independent election commission", "ballot", "مجلس النواب", "انتخابات برلمانية"]},
            {"id": "party_gov", "keywords": ["king abdullah", "crown prince hussein", "prime minister", "royal hashemite court", "ديوان ملكي", "حكومة"]},
            {"id": "diplomacy", "keywords": ["jerusalem holy sites", "hashemite custodianship", "unrwa", "palestinian cause", "state visit", "الوصاية الهاشمية"]},
            {"id": "security", "keywords": ["jordanian armed forces", "border security", "captagon smuggling", "syria border", "القوات المسلحة"]},
            {"id": "econ_policy", "keywords": ["water scarcity", "imf facility", "economic modernization", "inflation", "البنك المركزي"]},
        ]
    },
    "lebanon": {
        "themes": [
            {"id": "elections", "keywords": ["presidential election", "parliamentary quorum", "nabih berri", "انتخاب رئيس الجمهورية", "مجلس النواب"]},
            {"id": "security", "keywords": ["hezbollah", "unifil", "blue line", "ceasefire", "airstrike", "southern lebanon", "حزب الله", "اليونيفيل"]},
            {"id": "party_gov", "keywords": ["najib mikati", "caretaker government", "grand serail", "cabinet session", "مجلس الوزراء", "السراي الحكومي"]},
            {"id": "econ_policy", "keywords": ["banque du liban", "banking sector", "imf reform", "lira exchange rate", "مصرف لبنان", "إصلاح مصرفي"]},
            {"id": "diplomacy", "keywords": ["resolution 1701", "french initiative", "quintet committee", "diplomatic mediation", "قرار 1701"]},
        ]
    },
    "morocco": {
        "themes": [
            {"id": "diplomacy", "keywords": ["sahara marocain", "plan d'autonomie", "diplomatie marocaine", "bourita", "visite royale", "الصحراء المغربية", "مبادرة الحكم الذاتي"]},
            {"id": "party_gov", "keywords": ["mohammed vi", "akhannouch", "gouvernement", "parlement", "chambre des représentants", "مجلس النواب", "حكومة"]},
            {"id": "econ_policy", "keywords": ["ocp", "phosphate", "stress hydrique", "dessalement", "bank al-maghrib", "investissements", "المكتب الشريف للفوسفاط"]},
            {"id": "security", "keywords": ["forces armées royales", "sécurité frontalière", "coopération sécuritaire", "défense", "القوات المسلحة الملكية"]},
            {"id": "elections", "keywords": ["élections législatives", "scrutin", "partis politiques", "urne", "انتخابات"]},
        ]
    },
    "netherlands": {
        "themes": [
            {"id": "elections", "keywords": ["tweede kamerverkiezingen", "kiesraad", "stemming", "coalitievorming", "verkiezingen"]},
            {"id": "party_gov", "keywords": ["tweede kamer", "kabinet-schoof", "dick schoof", "minister-president", "geert wilders", "pvv", "vvd", "nsc", "bbb"]},
            {"id": "econ_policy", "keywords": ["asml", "haven van rotterdam", "stikstofcrisis", "dnb", "regeringsakkoord", "koopkracht", "begrotingsbeleid"]},
            {"id": "security", "keywords": ["defensie", "krijgsmacht", "f-35", "navo-norm", "cyberveiligheid", "aivd"]},
            {"id": "diplomacy", "keywords": ["eu-beleid", "asielcrisis", "internationaal gerechtshof", "ministerie van buitenlandse zaken"]},
        ]
    },
    "norway": {
        "themes": [
            {"id": "elections", "keywords": ["stortingsvalg", "stemmer", "valgkamp", "regjeringssonderinger"]},
            {"id": "party_gov", "keywords": ["stortinget", "jonas gahr støre", "statsminister", "regjeringen", "arbeiderpartiet", "senterpartiet"]},
            {"id": "econ_policy", "keywords": ["oljefondet", "norges bank", "rentebeslutning", "equinor", "strømpriser", "inflasjon", "handlingsregelen"]},
            {"id": "security", "keywords": ["forsvaret", "langtidsplan", "nato-nordflanke", "etterretningstjenesten", "grensevakt"]},
            {"id": "diplomacy", "keywords": ["utenriksdepartementet", "barentssamarbeidet", "nordisk råd", "ukrainahjelp"]},
        ]
    },
    "pacific_islands": {
        "themes": [
            {"id": "diplomacy", "keywords": ["pacific islands forum", "pif", "bilateral security pact", "geopolitical contest", "state visit", "suva declaration"]},
            {"id": "econ_policy", "keywords": ["climate adaptation", "loss and damage", "fisheries access", "seabed mining", "exclusive economic zone"]},
            {"id": "security", "keywords": ["maritime surveillance", "illegal fishing", "police cooperation", "regional security"]},
            {"id": "party_gov", "keywords": ["prime minister", "parliament", "no-confidence motion", "papua new guinea", "fiji", "solomon islands"]},
            {"id": "elections", "keywords": ["general election", "electoral commission", "ballot", "polling"]},
        ]
    },
    "peru": {
        "themes": [
            {"id": "elections", "keywords": ["elecciones generales", "onpe", "jne", "segunda vuelta", "votos", "adelanto de elecciones"]},
            {"id": "party_gov", "keywords": ["dina boluarte", "gustavo adrianzén", "congreso de la república", "moción de vacancia", "palacio de gobierno"]},
            {"id": "econ_policy", "keywords": ["minería de cobre", "tía maría", "las bambas", "puerto de chancay", "bcrp", "inflación"]},
            {"id": "security", "keywords": ["estado de emergencia", "seguridad ciudadana", "extorsión", "policía nacional", "fuerzas armadas"]},
            {"id": "diplomacy", "keywords": ["cumbre apec", "torre tagle", "cancillería", "alianza del pacífico"]},
        ]
    },
    "portugal": {
        "themes": [
            {"id": "elections", "keywords": ["eleições legislativas", "votação", "comícios", "cne", "maioria parlamentar"]},
            {"id": "party_gov", "keywords": ["luís montenegro", "aliança democrática", "assembleia da república", "são bento", "governo constitucional"]},
            {"id": "econ_policy", "keywords": ["orçamento do estado", "crise na habitação", "banco de portugal", "prr", "crescimento gdp"]},
            {"id": "security", "keywords": ["forças armadas", "polícia judiciária", "segurança interna", "vigilância marítima"]},
            {"id": "diplomacy", "keywords": ["cplp", "união europeia", "palop", "ministério dos negócios estrangeiros"]},
        ]
    },
    "romania": {
        "themes": [
            {"id": "elections", "keywords": ["alegeri prezidențiale", "alegeri parlamentare", "vot", "turul doi", "secții de votare", "biroul electoral central"]},
            {"id": "party_gov", "keywords": ["marcel ciolacu", "klaus iohannis", "guvernul româniei", "parlament", "coaliția psd-pnl"]},
            {"id": "security", "keywords": ["flancul estic", "marea neagră", "baza mihail kogălniceanu", "drone căzute", "armata română"]},
            {"id": "econ_policy", "keywords": ["deficit bugetar", "banca națională a româniei", "inflație", "fonduri europene", "pnrr"]},
            {"id": "diplomacy", "keywords": ["schengen", "moldova sprijin", "ministerul afacerilor externe", "parteneriat strategic"]},
        ]
    },
    "sri_lanka": {
        "themes": [
            {"id": "elections", "keywords": ["presidential election", "parliamentary poll", "election commission", "npp landslide", "මැතිවරණය", "தேர்தல்"]},
            {"id": "party_gov", "keywords": ["anura kumara dissanayake", "npp", "jvp", "prime minister harini amarasuriya", "parliament"]},
            {"id": "econ_policy", "keywords": ["imf bailout", "debt restructuring", "central bank of sri lanka", "forex reserves", "inflation"]},
            {"id": "diplomacy", "keywords": ["colombo port", "india-sri lanka cooperation", "chinese research vessel", "bilateral ties"]},
            {"id": "security", "keywords": ["maritime security", "drug trafficking", "sri lanka navy", "police reform"]},
        ]
    },
    "switzerland": {
        "themes": [
            {"id": "elections", "keywords": ["volksabstimmung", "ständerat", "nationalrat", "initiative", "referendum", "votations"]},
            {"id": "party_gov", "keywords": ["bundesrat", "bundespräsident", "departement", "berner bundeshaus", "conseil fédéral"]},
            {"id": "econ_policy", "keywords": ["snb", "schweizerische nationalbank", "leitzins", "franken", "ubs", "bankenregulierung", "finma"]},
            {"id": "diplomacy", "keywords": ["bilaterale iii", "abkommen mit eu", "neutralität", "gute dienste", "eda", "uno-sicherheitsrat"]},
            {"id": "security", "keywords": ["schweizer armee", "neutralitätsinitiative", "f-35 beschaffung", "rüstung"]},
        ]
    },
    "syria": {
        "themes": [
            {"id": "party_gov", "keywords": ["حكومة تسيير الأعمال", "الإدارة الانتقالية", "أحمد الشرع", "الجولاني", "المجلس العسكري", "دمشق"]},
            {"id": "security", "keywords": ["وقف إطلاق النار", "السيطرة الميدانية", "الفصائل المسلحة", "قوات سوريا الديمقراطية", "الضربات الإسرائيلية", "الأمن الداخلي"]},
            {"id": "diplomacy", "keywords": ["الاعتراف الدولي", "رفع العقوبات", "التطبيع العربي", "عودة اللاجئين", "المفاوضات الدولية"]},
            {"id": "econ_policy", "keywords": ["إعادة الإعمار", "الليرة السورية", "المساعدات الإنسانية", "استئناف التجارة", "الخدمات الأساسية"]},
            {"id": "unrest_conflict", "keywords": ["اشتباكات", "قصف", "انفجار", "خلايا نائمة", "استقرار أمني"]},
        ]
    },
    "west_africa": {
        "themes": [
            {"id": "diplomacy", "keywords": ["alliance des états du sahel", "aes", "cedeao", "ecowas", "sommet régional", "transition sahélo-saharienne"]},
            {"id": "party_gov", "keywords": ["bassirou diomaye faye", "ousmane sonko", "ibrahim traoré", "assimi goïta", "abdourahamane tchiani", "gouvernement"]},
            {"id": "security", "keywords": ["lutte antiterroriste", "jnim", "sécurité frontalière", "départ des forces occidentales", "bataillon"]},
            {"id": "econ_policy", "keywords": ["franc cfa", "souveraineté monétaire", "port de dakar", "gisements de pétrole", "uemoa"]},
            {"id": "elections", "keywords": ["élections législatives", "scrutin", "transition démocratique", "processus électoral"]},
        ]
    },
}

def main():
    created = []
    for desk, data in DESK_THEMES.items():
        pack_dir = COUNTRIES_DIR / desk
        if not pack_dir.exists():
            continue
        theme_path = pack_dir / "themes.yaml"
        content = yaml.dump(data, allow_unicode=True, sort_keys=False)
        theme_path.write_text(content, encoding="utf-8")
        created.append(desk)
    print(f"Created themes.yaml for {len(created)} desks: {created}")

if __name__ == "__main__":
    main()
