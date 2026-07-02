import streamlit as st
import pandas as pd
from PIL import Image
import io
import base64
from datetime import datetime
import sqlite3
import json
from pathlib import Path

# =========================================================
# AURAATELIER v4.0
# Gardırop + Bütçe + Mini Chatbot + Tema Sistemi
# =========================================================

st.set_page_config(
    page_title="AuraAtelier // Budget Wardrobe AI",
    layout="wide",
    page_icon="🔮"
)
DB_PATH = Path(__file__).with_name("auraatelier.db")

DEFAULT_BUDGET_SETTINGS = {
    "monthly_income": 4000.0,
    "monthly_limit": 4000.0,
    "saving_goal": 0.0,
    "category_limits": {
        "Üst Giyim": 800.0,
        "Alt Giyim": 800.0,
        "Dış Giyim": 500.0,
        "Ayakkabı": 500.0,
        "Aksesuar": 300.0,
        "Kozmetik / Bakım": 600.0,
        "Diğer": 500.0,
    }
}


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wardrobe_items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                main_category TEXT,
                sub_category TEXT,
                price REAL,
                color TEXT,
                size TEXT,
                usage_count INTEGER,
                need_level TEXT,
                emotion TEXT,
                modest_level TEXT,
                theme TEXT,
                gender TEXT,
                style_identity TEXT,
                image BLOB,
                notes TEXT,
                created_at TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)


def load_wardrobe_items():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM wardrobe_items ORDER BY created_at DESC"
        ).fetchall()

    return [dict(row) for row in rows]


def save_wardrobe_item(item):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO wardrobe_items (
                id, name, main_category, sub_category, price, color, size,
                usage_count, need_level, emotion, modest_level, theme, gender,
                style_identity, image, notes, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["id"],
            item["name"],
            item["main_category"],
            item["sub_category"],
            item["price"],
            item["color"],
            item["size"],
            item["usage_count"],
            item["need_level"],
            item["emotion"],
            item["modest_level"],
            item["theme"],
            item["gender"],
            item["style_identity"],
            item["image"],
            item["notes"],
            item["created_at"],
        ))


def update_wardrobe_usage(item_id, usage_count):
    with get_conn() as conn:
        conn.execute(
            "UPDATE wardrobe_items SET usage_count = ? WHERE id = ?",
            (usage_count, item_id)
        )


def delete_wardrobe_item(item_id):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM wardrobe_items WHERE id = ?",
            (item_id,)
        )


def load_budget_settings():
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            ("budget_settings",)
        ).fetchone()

    if row is None:
        return json.loads(json.dumps(DEFAULT_BUDGET_SETTINGS))

    return json.loads(row["value"])


def save_budget_settings(settings):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO app_settings (key, value)
            VALUES (?, ?)
        """, (
            "budget_settings",
            json.dumps(settings, ensure_ascii=False)
        ))
# -----------------------------
# SESSION STATE
# -----------------------------

init_db()

if "db_loaded" not in st.session_state:
    st.session_state.wardrobe_items = load_wardrobe_items()
    st.session_state.budget_settings = load_budget_settings()
    st.session_state.db_loaded = True

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": "Selam, ben AuraMini. Bana bütçeni, almak istediğin ürünü veya kombin derdini yazabilirsin. Sepet yangını çıkmadan önce buradayım. 🦉"
        }
    ]


# -----------------------------
# HELPERS
# -----------------------------

def money(value):
    return f"{value:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


def get_total_spent():
    return sum(item["price"] for item in st.session_state.wardrobe_items)


def get_remaining_budget():
    return st.session_state.budget_settings["monthly_limit"] - get_total_spent()


def get_category_spent(category):
    return sum(
        item["price"]
        for item in st.session_state.wardrobe_items
        if item["main_category"] == category
    )


def get_cost_per_wear(price, usage_count):
    if usage_count <= 0:
        return price
    return price / usage_count


def image_to_base64(image_bytes):
    if image_bytes is None:
        return None
    return base64.b64encode(image_bytes).decode("utf-8")


def get_style_identity(gender, theme):
    if gender == "Erkek" and theme == "Gotik & Dark Academia":
        return "⛓️ Bad Boy / Vamp Essence Active"
    if gender == "Erkek" and theme == "Old Money / Quiet Luxury":
        return "👑 Classic Gentleman / Quiet Luxury Active"
    if gender == "Erkek" and theme == "Clean & Soft Girl":
        return "🧼 Clean Boy / Soft Minimal Active"
    if gender == "Erkek" and theme == "Vintage & Retro":
        return "📼 Retro Gentleman / Vintage Ease Active"
    if gender == "Kadın" and theme == "Clean & Soft Girl":
        return "🩰 Soft Muse / Clean Glow Active"
    if gender == "Kadın" and theme == "Gotik & Dark Academia":
        return "🕯️ Dark Muse / Gothic Academia Active"
    if gender == "Kadın" and theme == "Old Money / Quiet Luxury":
        return "🕊️ Quiet Muse / Capsule Elegance Active"
    if gender == "Kadın" and theme == "Vintage & Retro":
        return "📻 Retro Muse / Sepia Wardrobe Active"
    return f"✨ {theme} // {gender} Modu"


def get_budget_status_text():
    total = get_total_spent()
    remaining = get_remaining_budget()
    limit = st.session_state.budget_settings["monthly_limit"]

    if remaining < 0:
        return f"🚨 Bütçe {money(abs(remaining))} aşılmış. Sepet ejderhası büyümüş."
    if total > limit * 0.85:
        return f"⚠️ Bütçenin %85'inden fazlası kullanıldı. Bundan sonrası sarı bölge."
    if total > limit * 0.60:
        return f"🟡 Orta bölgedesin. Alışveriş öncesi chatbot'a danışmak iyi olur."
    return f"🟢 Bütçe dengede. Şimdilik cüzdanın nefes alıyor."


def analyze_purchase(name, price, category, emotion, need_level, expected_usage):
    remaining_after = get_remaining_budget() - price
    category_limit = st.session_state.budget_settings["category_limits"].get(category, None)
    category_after = get_category_spent(category) + price
    cpw = get_cost_per_wear(price, expected_usage)

    emotional_risk = emotion in [
        "Stres",
        "Final haftası",
        "Kıyas / moral bozukluğu",
        "Can sıkıntısı",
        "Oda / çevre gerginliği"
    ]

    if remaining_after < 0:
        return {
            "level": "red",
            "title": "Kırmızı Alarm",
            "message": f"Bu ürünü alırsan bütçe {money(abs(remaining_after))} eksiye düşüyor. Bu ay alma, sepette beklet veya iade/satış planı yap.",
            "cpw": cpw
        }

    if category_limit is not None and category_after > category_limit:
        return {
            "level": "yellow",
            "title": "Kategori Limiti Aşılıyor",
            "message": f"{category} kategorisinde limit aşılacak. Ürün kötü değil ama zamanlama sorunlu olabilir.",
            "cpw": cpw
        }

    if emotional_risk and need_level != "Zorunlu ihtiyaç":
        return {
            "level": "blue",
            "title": "Duygusal Alışveriş Sinyali",
            "message": "Bu alışveriş isteği gerçek olabilir ama altında stres, kıyas veya yorgunluk var gibi. 24 saat beklet, önce dolabından kombin üret.",
            "cpw": cpw
        }

    if expected_usage < 3 and need_level != "Zorunlu ihtiyaç":
        return {
            "level": "yellow",
            "title": "Kullanım Sayısı Düşük",
            "message": "Bu parça az kullanılacak gibi görünüyor. Kullanım başı maliyet yüksek kalabilir.",
            "cpw": cpw
        }

    return {
        "level": "green",
        "title": "Yeşil Bölge",
        "message": f"Bu ürün bütçeye sığıyor. Alırsan kalan bütçen {money(remaining_after)} olur.",
        "cpw": cpw
    }


def normalize_for_chat(text):
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return text.lower().translate(tr_map).strip()


def extract_price_from_text(text):
    cleaned = normalize_for_chat(text).replace(",", ".")
    tokens = cleaned.replace("₺", " tl ").replace("tl", " tl ").split()
    for token in tokens:
        token = token.replace("tl", "").strip()
        try:
            value = float(token)
            if value > 0:
                return value
        except ValueError:
            continue
    return None


def guess_category_from_text(text):
    t = normalize_for_chat(text)
    if any(w in t for w in ["pantolon", "etek", "sort", "jean", "tayt"]):
        return "Alt Giyim"
    if any(w in t for w in ["bluz", "gomlek", "tisort", "tshirt", "atlet", "crop", "kazak", "sweat", "ust"]):
        return "Üst Giyim"
    if any(w in t for w in ["ceket", "hirka", "mont", "trenkot", "kimono", "dis giyim"]):
        return "Dış Giyim"
    if any(w in t for w in ["bileklik", "kolye", "yuzuk", "kupe", "canta", "kemer", "zincir", "aksesuar"]):
        return "Aksesuar"
    if any(w in t for w in ["serum", "gunes kremi", "krem", "nemlendirici", "tonik", "c vitamini", "bakim", "far", "ruj", "maskara", "makyaj", "allik"]):
        return "Kozmetik / Bakım"
    if any(w in t for w in ["ayakkabi", "bot", "sandalet", "babet", "sneaker"]):
        return "Ayakkabı"
    return "Diğer"


def detect_mood_from_text(text):
    t = normalize_for_chat(text)
    if any(w in t for w in ["uzgun", "uzgunum", "moralim bozuk", "kotuyum", "canim sikkin", "aglayasim", "yalniz", "degmez", "hic iyi degil"]):
        return "sad"
    if any(w in t for w in ["stres", "final", "sinav", "yetismiyor", "bunaldim", "gerildim", "yorgunum", "biktim"]):
        return "stress"
    if any(w in t for w in ["kiyas", "baskalari", "guzel degilim", "cirkin", "yakismiyor", "acik giyinen", "kisa giyinen"]):
        return "comparison"
    if any(w in t for w in ["mutluyum", "iyi hissediyorum", "sevindim", "basardim"]):
        return "happy"
    return "neutral"


def looks_like_purchase_intent(text):
    t = normalize_for_chat(text)
    has_purchase_word = any(w in t for w in [
        "alayim mi", "almali miyim", "satin alayim", "alsam mi", "almak istiyorum",
        "almak istiyom", "sepette", "sepet", "alacam", "alicam", "alabilir miyim", "almak"
    ])
    has_product_hint = any(w in t for w in ["bluz", "pantolon", "bileklik", "kolye", "far", "krem", "gomlek", "ayakkabi", "serum", "aksesuar"])
    return has_purchase_word or (extract_price_from_text(t) is not None and has_product_hint)


def get_category_summary_text():
    lines = []
    for category in st.session_state.budget_settings["category_limits"]:
        spent = get_category_spent(category)
        limit = st.session_state.budget_settings["category_limits"][category]
        remaining = limit - spent
        status = f"{money(abs(remaining))} aşılmış" if remaining < 0 else f"{money(remaining)} kaldı"
        lines.append(f"- **{category}:** {money(spent)} / {money(limit)} | {status}")
    return "\n".join(lines)


def get_wardrobe_short_summary():
    items = st.session_state.wardrobe_items
    if not items:
        return "Gardırobunda henüz kayıtlı ürün yok. Önce Ürün Ekle sekmesinden birkaç parça girelim."
    lines = []
    for item in items[:8]:
        lines.append(f"- **{item['name']}** ({item['main_category']}) | {money(item['price'])} | kullanım: {item['usage_count']}")
    return "\n".join(lines)


def smart_purchase_advice(user_text):
    price = extract_price_from_text(user_text)
    category = guess_category_from_text(user_text)
    mood = detect_mood_from_text(user_text)
    if price is None:
        return "Fiyatı yakalayamadım dostum. Şöyle yazarsan net karar veririm:\n\n**700 TL bluz almak istiyorum, moralim biraz bozuk.**"
    remaining_after = get_remaining_budget() - price
    category_limit = st.session_state.budget_settings["category_limits"].get(category, 0)
    category_after = get_category_spent(category) + price
    cpw_hint = "Bunu en az 5 kez kullanacak mısın?" if category not in ["Kozmetik / Bakım"] else "Bu bakım/makyaj ürünü gerçekten rutinde yer bulacak mı?"
    if remaining_after < 0:
        return f"🚨 **Kırmızı bölge.** Bunu alırsan bütçen **{money(abs(remaining_after))}** eksiye düşüyor.\n\nTahmini kategori: **{category}**\nBenim kararım: **Bu ay alma.** Sepette beklet. Önce iade/satış/alternatif kombin planı yapalım."
    if category_limit > 0 and category_after > category_limit:
        return f"🟡 **Sarı bölge.** Genel bütçen tamamen yanmıyor ama **{category}** limitini aşıyor.\n\nAlırsan kalan genel bütçe: **{money(remaining_after)}**\nBenim kararım: **24 saat bekle.** Dolabında benzeri var mı, önce onu kontrol edelim."
    if mood in ["sad", "stress", "comparison"]:
        return f"🔵 Para açısından mümkün: alırsan kalan bütçen **{money(remaining_after)}** olur.\n\nAma cümlende duygu sinyali var. Bu ürün gerçekten ihtiyaç mı, yoksa moral toparlama isteği mi?\nBenim kararım: **Şimdi alma, önce 1 kombin deneyelim.** Dolabından 1 üst + 1 alt + 1 aksesuar yaz."
    return f"🟢 **Bütçe açısından alınabilir görünüyor.**\n\nTahmini kategori: **{category}**\nAlırsan kalan bütçen: **{money(remaining_after)}**\n\nSon kontrol: {cpw_hint} Cevap evetse daha mantıklı."


def smart_outfit_reply():
    items = st.session_state.wardrobe_items
    if len(items) < 2:
        return "Kombin çıkarabilmem için gardıropta en az 2 ürün olmalı. Önce birkaç parça ekleyelim."
    tops = [i for i in items if i["main_category"] == "Üst Giyim"]
    bottoms = [i for i in items if i["main_category"] == "Alt Giyim"]
    accessories = [i for i in items if i["main_category"] == "Aksesuar"]
    outerwear = [i for i in items if i["main_category"] == "Dış Giyim"]
    if not tops or not bottoms:
        return "Gardıropta kombin için en az bir üst ve bir alt parça lazım. Şu an üst-alt dengesi eksik görünüyor."
    top = tops[0]
    bottom = bottoms[0]
    acc = accessories[0] if accessories else None
    outer = outerwear[0] if outerwear else None
    outfit = f"Bugün şunu deneyebilirsin:\n\n- **{top['name']}**\n- **{bottom['name']}**"
    if outer:
        outfit += f"\n- **{outer['name']}**"
    if acc:
        outfit += f"\n- **{acc['name']}**"
    outfit += "\n\nBu kombin yeni alışveriş yapmadan dolabı çalıştırır. Kullanım başı maliyet de düşer. Cüzdan içeride sessizce alkışlıyor."
    return outfit


def mini_chatbot_reply(user_text):
    text = user_text.strip()
    t = normalize_for_chat(text)
    mood = detect_mood_from_text(text)
    if not text:
        return "Buradayım dostum. Bir şey yaz, beraber çözelim."
    if any(w in t for w in ["selam", "merhaba", "slm", "hey", "naber"]):
        return "Selam dostum 🌷 Bugün ne yapıyoruz? Bütçe mi, kombin mi, sepet krizi mi?"
    if any(w in t for w in ["nasilsin", "iyi misin", "ne yapiyorsun"]):
        return "Ben küçük gardırop baykuşu gibi nöbetteyim. Sen nasılsın? Bugün moral mi düşük, bütçe mi karışık?"
    if any(w in t for w in ["tesekkur", "sag ol", "eyvallah", "harikasin"]):
        return "Her zaman dostum 💛 Beraber hem bütçeyi hem dolabı hem ruh halini toparlarız."
    if mood == "sad":
        return "Kıyamam dostum. Üzgünken alışveriş isteği çok normal; insan bazen ürün değil, kendini iyi hissetme ihtimali almak istiyor.\n\nİki yol var: Bana ne olduğunu anlatabilirsin ya da dolabından 3 parça yaz, bütçeyi yakmadan moral yükselten kombin çıkarayım."
    if mood == "stress":
        return "Bu biraz stres alışverişi kokusu veriyor. Almak istediğin şeyi fiyatıyla yaz, sana al/bekle/alma diye bütçeye göre yorumlayayım."
    if mood == "comparison":
        return "Kıyas modu açılmış gibi. Açık/kısa giyinmeden de güçlü ve yazlık kombin kurulur. Bana 1 üst + 1 alt + 1 aksesuar yaz."
    if any(w in t for w in ["butce", "kalan", "param", "durum", "ne kadar kaldi"]):
        return f"Bu ay toplam harcaman: **{money(get_total_spent())}**\n\nKalan bütçen: **{money(get_remaining_budget())}**\n\n{get_budget_status_text()}"
    if any(w in t for w in ["kategori", "ozet", "dokum", "kiyafete", "aksesuara", "bakima"]):
        return "Kategori dökümün şöyle:\n\n" + get_category_summary_text()
    if looks_like_purchase_intent(text):
        return smart_purchase_advice(text)
    if any(w in t for w in ["kombin", "ne giyeyim", "giysem", "outfit"]):
        return smart_outfit_reply()
    if any(w in t for w in ["gardirob", "dolap", "urunlerim", "neler var"]):
        return "Gardırobunda kısa özet şöyle:\n\n" + get_wardrobe_short_summary()
    if any(w in t for w in ["tasarruf", "eksi", "acik", "para biriktir", "altin"]):
        return "Toparlanma planı:\n\n1. Bu ay keyfi harcamaya mini kilit koy.\n2. Kullanmadığın 2-3 parçayı satışa çıkar.\n3. Alışveriş isteği gelince önce fiyatıyla bana yaz.\n4. Birikim hedefini ay başında ayır.\n\nCüzdanı battaniyeye sarıyoruz, panik yok."
    return "Anladım dostum. Bunu bütçe, stil ya da moral tarafından ele alabiliriz.\n\nŞöyle yazarsan daha iyi yardımcı olurum:\n- **Bütçem ne durumda?**\n- **700 TL bluz almak istiyorum.**\n- **Moralim bozuk, alışveriş yapmak istiyorum.**\n- **Kombin öner.**\n- **Dolabımda neler var?**"


def generate_simple_outfit_advice(occasion=None):
    items = st.session_state.wardrobe_items

    tops = [i for i in items if i["main_category"] == "Üst Giyim"]
    bottoms = [i for i in items if i["main_category"] == "Alt Giyim"]
    accessories = [i for i in items if i["main_category"] == "Aksesuar"]
    outerwear = [i for i in items if i["main_category"] == "Dış Giyim"]

    if not tops or not bottoms:
        return "Kombin için en az bir üst ve bir alt giyim parçası eklemelisin."

    # Aynı kombini tekrar tekrar vermemek için session state sayaçları
    if "combo_rotation_index" not in st.session_state:
        st.session_state.combo_rotation_index = 0

    if "last_combo_signature" not in st.session_state:
        st.session_state.last_combo_signature = None

    # Daha az kullanılan parçaları öne almak için sırala
    tops = sorted(tops, key=lambda x: x.get("usage_count", 0))
    bottoms = sorted(bottoms, key=lambda x: x.get("usage_count", 0))
    accessories = sorted(accessories, key=lambda x: x.get("usage_count", 0))
    outerwear = sorted(outerwear, key=lambda x: x.get("usage_count", 0))

    # Tüm üst-alt kombinlerini oluştur
    all_combos = []
    for top in tops:
        for bottom in bottoms:
            combo_score = top.get("usage_count", 0) + bottom.get("usage_count", 0)
            all_combos.append({
                "top": top,
                "bottom": bottom,
                "score": combo_score
            })

    # Az kullanılan kombinleri öne koy
    all_combos = sorted(all_combos, key=lambda x: x["score"])

    # Eğer son kombinle aynıysa bir sonrakine geç
    start_idx = st.session_state.combo_rotation_index % len(all_combos)

    selected_combo = None
    for offset in range(len(all_combos)):
        idx = (start_idx + offset) % len(all_combos)
        candidate = all_combos[idx]
        signature = f"{candidate['top']['id']}-{candidate['bottom']['id']}"

        if signature != st.session_state.last_combo_signature:
            selected_combo = candidate
            st.session_state.combo_rotation_index = idx + 1
            st.session_state.last_combo_signature = signature
            break

    if selected_combo is None:
        selected_combo = all_combos[0]
        st.session_state.combo_rotation_index += 1
        st.session_state.last_combo_signature = (
            f"{selected_combo['top']['id']}-{selected_combo['bottom']['id']}"
        )

    top = selected_combo["top"]
    bottom = selected_combo["bottom"]

    # Aksesuar ve dış giyimde de dönüşümlü seçim
    acc = None
    outer = None

    if accessories:
        acc_index = st.session_state.combo_rotation_index % len(accessories)
        acc = accessories[acc_index]

    # Kombin amacına göre outer seç
    if outerwear:
        if occasion and ("Kapalı" in occasion or "Yazlık" in occasion or "Final" in occasion):
            outer = outerwear[0]
        else:
            outer_index = st.session_state.combo_rotation_index % len(outerwear)
            outer = outerwear[outer_index]

    outfit_lines = [
        f"Bugün için önerim:",
        f"- **{top['name']}**",
        f"- **{bottom['name']}**"
    ]

    if outer:
        outfit_lines.append(f"- **{outer['name']}**")
    if acc:
        outfit_lines.append(f"- **{acc['name']}**")

    outfit_text = "\n".join(outfit_lines)

    extra_note = ""

    if occasion:
        if "Kapalı" in occasion or "Yazlık" in occasion:
            extra_note = (
                "\n\nBu kombin kapalı ama ferah görünüm için uygun. "
                "İnce kumaş, açık ton ve rahat kesim işini kolaylaştırır."
            )
        elif "Old money" in occasion or "Old Money" in occasion:
            extra_note = (
                "\n\nBu kombin old money hissi için sade ve temiz tutulmalı. "
                "Az aksesuar, düzgün duruş, temiz siluet."
            )
        elif "Gotik" in occasion:
            extra_note = (
                "\n\nBu kombin gotik etki için koyu bir aksesuar veya keskin bir detayla güçlenebilir."
            )
        elif "Soft" in occasion:
            extra_note = (
                "\n\nBu kombin soft görünüm için daha yumuşak renk ve sade aksesuarla tamamlanabilir."
            )

    outfit_text += (
        "\n\nBu kombin yeni alışveriş yapmadan dolaptaki parçaları çalıştırır. "
        "Ayrıca kullanım başı maliyeti de düşürmeye yardım eder."
        + extra_note
    )

    return outfit_text



# -----------------------------
# ADVANCED THEME SYSTEM v5
# -----------------------------

THEME_KITS = {
    "Vintage & Retro": {
        "emoji": "📻",
        "title": "Vintage Archive",
        "kicker": "sepia / retro / yazlık defter",
        "subtitle": "Eski defter dokusu, ekose, çizgi, bordo, krem ve dolaptan yeniden doğan parçalar.",
        "quote": "Bugünün kombini biraz plak cızırtısı, biraz eski yazlık fotoğrafı.",
        "font_title": "'Playfair Display', serif",
        "font_body": "'Courier Prime', monospace",
        "day": {
            "bg1": "#FFF8EE", "bg2": "#E9D2B8", "bg3": "#B77C58",
            "text": "#46342D", "muted": "#876D5F", "accent": "#9A6B4F", "accent2": "#D89A54",
            "card": "rgba(255,246,235,0.78)", "panel": "rgba(255,250,244,0.74)", "border": "rgba(154,107,79,0.30)",
            "shadow": "rgba(118,78,52,0.18)", "grain": "0.17"
        },
        "night": {
            "bg1": "#241813", "bg2": "#4C3025", "bg3": "#A36B3F",
            "text": "#FFEBD8", "muted": "#D7BBA5", "accent": "#D59458", "accent2": "#F0C078",
            "card": "rgba(55,36,29,0.82)", "panel": "rgba(37,24,19,0.82)", "border": "rgba(240,192,120,0.24)",
            "shadow": "rgba(0,0,0,0.38)", "grain": "0.24"
        },
        "chips": ["Sepia", "Çizgili", "Ekose", "Bordo", "Pazar avı"],
        "ritual_title": "📜 Vintage Stil Defteri",
        "ritual_lines": [
            "Bir ana parça seç: çizgili pantolon, etnik bluz veya gömlek.",
            "Yanına nostaljik bir renk ekle: bordo, kahve, krem veya soluk yeşil.",
            "Yeni alışverişten önce dolaptaki eski parçaya ikinci hayat ver."
        ],
        "special": {
            "title": "📻 Vintage Özel Bileşenler",
            "fields": [
                ("Dönem hissi", ["70s", "80s", "90s", "Y2K", "Anadolu retro"]),
                ("Desen odağı", ["Çizgili", "Ekose", "Etnik", "Çiçekli", "Düz"]),
                ("Nostalji dozu", ["Hafif", "Belirgin", "Tam retro"]),
            ],
            "note": "Vintage modda kombin motoru yeni alışveriş yerine eski parçayı yeniden çalıştırmayı önceler."
        }
    },
    "Gotik & Dark Academia": {
        "emoji": "🕯️",
        "title": "Nocturne Wardrobe",
        "kicker": "dark academia / bordo / metal",
        "subtitle": "Koyu palet, bordo parıltı, akademik gölge ve dramatik bir gardırop sahnesi.",
        "quote": "Dolap kapağı açıldı, küçük bir şato koridoru nefes aldı.",
        "font_title": "'Cinzel', serif",
        "font_body": "'EB Garamond', serif",
        "day": {
            "bg1": "#15151C", "bg2": "#2B101F", "bg3": "#5C0022",
            "text": "#F4EAE5", "muted": "#BAACAF", "accent": "#B3002D", "accent2": "#7D4CDB",
            "card": "rgba(21,21,30,0.86)", "panel": "rgba(14,14,20,0.84)", "border": "rgba(179,0,45,0.42)",
            "shadow": "rgba(0,0,0,0.62)", "grain": "0.12"
        },
        "night": {
            "bg1": "#050507", "bg2": "#160008", "bg3": "#3A0016",
            "text": "#FFF0EA", "muted": "#B9A5AA", "accent": "#E0003F", "accent2": "#8C5CFF",
            "card": "rgba(10,10,16,0.92)", "panel": "rgba(5,5,8,0.90)", "border": "rgba(224,0,63,0.52)",
            "shadow": "rgba(0,0,0,0.78)", "grain": "0.10"
        },
        "chips": ["Bordo", "Siyah", "Metal", "Vamp aura", "Kütüphane gölgesi"],
        "ritual_title": "🩸 Gotik Kombin Ritüeli",
        "ritual_lines": [
            "Bir koyu temel seç: siyah pantolon, bordo parça veya koyu gömlek.",
            "Tek vurucu detay ekle: kolye, bel zinciri, koyu far veya keskin yaka.",
            "Her şeyi siyah yapma. Bordo ve gri, gotik etkiyi daha pahalı gösterir."
        ],
        "special": {
            "title": "🕯️ Gotik Özel Bileşenler",
            "fields": [
                ("Ana koyu ton", ["Siyah", "Bordo", "Koyu gri", "Mor", "Kahve"]),
                ("Vurucu detay", ["Metal kolye", "Bel zinciri", "Koyu far", "Keskin yaka", "Bot"]),
                ("Aura seviyesi", ["Soft Gothic", "Dark Academia", "Vamp", "Full Dramatic"]),
            ],
            "note": "Gotik modda öneri motoru tek güçlü detayı merkeze alır. Her şeyi siyah yapmak yerine kontrast arar."
        }
    },
    "Old Money / Quiet Luxury": {
        "emoji": "🕊️",
        "title": "Quiet Ledger",
        "kicker": "capsule / fabric / minimal",
        "subtitle": "Sade kumaşlar, temiz çizgiler, az ama güçlü parçalar ve pahalı görünen sessizlik.",
        "quote": "Logo konuşmaz. Kumaş, kesim ve duruş usulca imza atar.",
        "font_title": "'Cormorant Garamond', serif",
        "font_body": "'Inter', sans-serif",
        "day": {
            "bg1": "#F8F4EA", "bg2": "#DDD4C1", "bg3": "#8E7A55",
            "text": "#1F2A24", "muted": "#6A665A", "accent": "#25372D", "accent2": "#B79B6C",
            "card": "rgba(255,255,255,0.76)", "panel": "rgba(247,244,234,0.78)", "border": "rgba(37,55,45,0.18)",
            "shadow": "rgba(31,42,36,0.13)", "grain": "0.10"
        },
        "night": {
            "bg1": "#111711", "bg2": "#2C3328", "bg3": "#76633D",
            "text": "#EFE9DC", "muted": "#BEB4A3", "accent": "#C5A66F", "accent2": "#61725E",
            "card": "rgba(28,38,30,0.84)", "panel": "rgba(17,23,17,0.86)", "border": "rgba(197,166,111,0.25)",
            "shadow": "rgba(0,0,0,0.44)", "grain": "0.12"
        },
        "chips": ["Kapsül gardırop", "Keten", "Krem", "İyi kesim", "Az aksesuar"],
        "ritual_title": "🥂 Quiet Luxury Kontrolü",
        "ritual_lines": [
            "Bugünün formülü: temiz pantolon + sade üst + tek aksesuar.",
            "Ürün alırken logo değil kumaş, kesim ve kullanım sayısı sor.",
            "Bir parça 10 kombin kurmuyorsa old money değil, sepet sisidir."
        ],
        "special": {
            "title": "🕊️ Old Money Özel Bileşenler",
            "fields": [
                ("Kumaş hissi", ["Pamuk", "Keten", "Viskon", "Yün", "Saten"]),
                ("Siluet", ["Bol ama derli", "Düz kesim", "Yüksek bel", "Gömlekli", "Minimal"]),
                ("Aksesuar seviyesi", ["Yok", "Tek parça", "Saat/çanta", "İnci/altın ton"]),
            ],
            "note": "Old Money modda ürünün pahalı görünmesi için logo değil kesim, kumaş ve sade renk kontrol edilir."
        }
    },
    "Clean & Soft Girl": {
        "emoji": "🫧",
        "title": "Soft Glow Studio",
        "kicker": "pastel / clean / glow",
        "subtitle": "Pastel, ferah, temiz, hafif parıltılı ve moral toparlayan bir stil odası.",
        "quote": "Dolapta küçük bir sabah ışığı geziniyor.",
        "font_title": "'Poppins', sans-serif",
        "font_body": "'Poppins', sans-serif",
        "day": {
            "bg1": "#FFF7FB", "bg2": "#EAF6FF", "bg3": "#FFC6D7",
            "text": "#5A4650", "muted": "#9B7C8A", "accent": "#FF8FAB", "accent2": "#8BC8FF",
            "card": "rgba(255,255,255,0.72)", "panel": "rgba(255,247,251,0.76)", "border": "rgba(255,143,171,0.32)",
            "shadow": "rgba(255,143,171,0.20)", "grain": "0.08"
        },
        "night": {
            "bg1": "#211824", "bg2": "#34253F", "bg3": "#624C7C",
            "text": "#FFEAF2", "muted": "#D9B6C7", "accent": "#FF9BBB", "accent2": "#9BCBFF",
            "card": "rgba(50,38,56,0.82)", "panel": "rgba(33,24,36,0.84)", "border": "rgba(255,155,187,0.34)",
            "shadow": "rgba(0,0,0,0.36)", "grain": "0.08"
        },
        "chips": ["Pastel", "Clean girl", "Glow", "Rahat", "Ferah"],
        "ritual_title": "🧴 Soft Reset Paneli",
        "ritual_lines": [
            "Bugün temiz bir baz seç: sade üst, ferah pantolon, yumuşak renk.",
            "Moral bozuksa önce bakım + kombin dene, sonra alışveriş kararına dön.",
            "Parça seni sıkmamalı. Rahatlık bu temanın ana aksesuarı."
        ],
        "special": {
            "title": "🫧 Clean / Soft Girl Özel Bileşenler",
            "fields": [
                ("Renk enerjisi", ["Beyaz", "Pembe", "Bebe mavisi", "Krem", "Lila"]),
                ("Görünüm hedefi", ["Temiz", "Ferah", "Tatlı", "Bakımlı", "Rahat"]),
                ("Glow detayı", ["Güneş kremi", "Serum", "Hafif far", "Parlak dudak", "Sade aksesuar"]),
            ],
            "note": "Soft modda moral düşükse önce bakım + dolaptan kombin önerilir, direkt alışverişe atlamaz."
        }
    }
}


def build_advanced_css(theme, day_mode):
    kit = THEME_KITS[theme]
    mode_key = "night" if day_mode == "Gece" else "day"
    p = kit[mode_key]
    return f"""
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Courier+Prime&family=Cinzel:wght@600;700&family=EB+Garamond:wght@500;700&family=Cormorant+Garamond:wght@700&family=Poppins:wght@400;600;700;800&family=Inter:wght@400;600;800&display=swap');

    :root {{
        --bg1: {p["bg1"]};
        --bg2: {p["bg2"]};
        --bg3: {p["bg3"]};
        --text: {p["text"]};
        --muted: {p["muted"]};
        --accent: {p["accent"]};
        --accent2: {p["accent2"]};
        --card: {p["card"]};
        --panel: {p["panel"]};
        --border: {p["border"]};
        --shadow: {p["shadow"]};
        --grain-opacity: {p["grain"]};
        --title-font: {kit["font_title"]};
        --body-font: {kit["font_body"]};
    }}

    .stApp {{
        color: var(--text);
        font-family: var(--body-font);
        background:
            radial-gradient(circle at 8% 8%, color-mix(in srgb, var(--accent) 34%, transparent), transparent 27%),
            radial-gradient(circle at 92% 10%, color-mix(in srgb, var(--accent2) 30%, transparent), transparent 28%),
            radial-gradient(circle at 50% 100%, color-mix(in srgb, var(--bg3) 32%, transparent), transparent 34%),
            linear-gradient(135deg, var(--bg1), var(--bg2));
        background-attachment: fixed;
    }}

    .stApp::before {{
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        opacity: var(--grain-opacity);
        background-image:
            linear-gradient(115deg, transparent 0%, rgba(255,255,255,0.06) 40%, transparent 42%),
            radial-gradient(circle at 25% 20%, rgba(255,255,255,0.18) 0 1px, transparent 1px),
            radial-gradient(circle at 75% 65%, rgba(255,255,255,0.14) 0 1px, transparent 1px);
        background-size: 180px 180px, 38px 38px, 54px 54px;
        animation: auraDrift 18s ease-in-out infinite alternate;
    }}

    @keyframes auraDrift {{
        from {{ transform: translate3d(0,0,0) scale(1); filter: blur(0px); }}
        to {{ transform: translate3d(16px,-10px,0) scale(1.02); filter: blur(0.4px); }}
    }}

    header[data-testid="stHeader"] {{ background: transparent; backdrop-filter: blur(14px); }}
    .block-container {{ padding-top: 1.2rem; max-width: 1180px; position: relative; z-index: 1; }}

    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, color-mix(in srgb, var(--panel) 88%, transparent), color-mix(in srgb, var(--bg1) 92%, black 4%));
        border-right: 1px solid var(--border);
        box-shadow: 18px 0 60px var(--shadow);
    }}
    section[data-testid="stSidebar"] * {{ color: var(--text) !important; }}

    h1, h2, h3 {{ color: var(--text) !important; font-family: var(--title-font); letter-spacing: -0.02em; }}
    p, span, label, .stMarkdown, div {{ color: var(--text); }}

    .aura-hero {{
        position: relative; overflow: hidden; padding: 34px 36px; border-radius: 34px;
        background: linear-gradient(135deg, color-mix(in srgb, var(--card) 92%, transparent), color-mix(in srgb, var(--panel) 92%, transparent));
        border: 1px solid var(--border);
        box-shadow: 0 26px 80px var(--shadow), inset 0 1px 0 rgba(255,255,255,0.18);
        margin-bottom: 26px; isolation: isolate;
    }}
    .aura-hero::before {{
        content: ""; position: absolute; width: 310px; height: 310px; right: -90px; top: -120px;
        background: radial-gradient(circle, color-mix(in srgb, var(--accent) 42%, transparent), transparent 68%);
        filter: blur(3px); z-index: -1; animation: orbFloat 9s ease-in-out infinite alternate;
    }}
    .aura-hero::after {{
        content: ""; position: absolute; inset: 0;
        background: linear-gradient(105deg, transparent 0 25%, rgba(255,255,255,0.12) 43%, transparent 58% 100%);
        transform: translateX(-72%); animation: shimmer 6.5s ease-in-out infinite; z-index: -1;
    }}
    @keyframes orbFloat {{ from {{ transform: translateY(0) scale(1); }} to {{ transform: translateY(28px) scale(1.08); }} }}
    @keyframes shimmer {{ 0%, 55% {{ transform: translateX(-78%); opacity: 0; }} 70% {{ opacity: 1; }} 100% {{ transform: translateX(78%); opacity: 0; }} }}

    .aura-kicker {{ font-size: 0.82rem; color: var(--muted); font-weight: 800; text-transform: uppercase; letter-spacing: 0.20em; margin-bottom: 10px; }}
    .aura-title {{ font-family: var(--title-font); font-size: clamp(2.4rem, 6vw, 5.4rem); line-height: 0.88; font-weight: 800; margin: 0 0 16px 0; color: var(--text); text-shadow: 0 18px 46px var(--shadow); }}
    .aura-subtitle {{ max-width: 780px; color: var(--muted); font-size: 1.05rem; line-height: 1.72; }}
    .aura-chip-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }}
    .aura-chip {{ display: inline-flex; align-items: center; padding: 9px 13px; border-radius: 999px; background: color-mix(in srgb, var(--accent) 16%, var(--card)); border: 1px solid var(--border); color: var(--text); font-size: 0.88rem; font-weight: 800; box-shadow: 0 12px 24px color-mix(in srgb, var(--shadow) 60%, transparent); }}

    .aura-card, .ritual-card, div[data-testid="stMetric"], .stDataFrame, .stAlert {{
        background: var(--card) !important; border: 1px solid var(--border) !important; border-radius: 24px !important;
        box-shadow: 0 18px 48px var(--shadow) !important; backdrop-filter: blur(14px);
    }}
    .aura-card {{ padding: 22px; transition: transform 0.24s ease, box-shadow 0.24s ease, border-color 0.24s ease; }}
    .aura-card:hover {{ transform: translateY(-5px); border-color: color-mix(in srgb, var(--accent) 64%, var(--border)) !important; box-shadow: 0 28px 70px var(--shadow) !important; }}

    .ritual-card {{ position: relative; overflow: hidden; padding: 24px; margin: 12px 0 22px 0; }}
    .ritual-card::after {{ content: ""; position: absolute; width: 170px; height: 170px; right: -48px; bottom: -55px; border-radius: 999px; background: color-mix(in srgb, var(--accent2) 28%, transparent); filter: blur(5px); }}
    .ritual-title {{ font-family: var(--title-font); font-size: 1.45rem; font-weight: 800; margin-bottom: 12px; color: var(--text); }}
    .ritual-line {{ padding: 10px 0; border-bottom: 1px solid color-mix(in srgb, var(--border) 60%, transparent); color: var(--text); position: relative; z-index: 1; }}
    .theme-meter {{ height: 12px; border-radius: 999px; background: color-mix(in srgb, var(--muted) 18%, transparent); overflow: hidden; border: 1px solid var(--border); position: relative; z-index: 1; }}
    .theme-meter-fill {{ height: 100%; width: 72%; background: linear-gradient(90deg, var(--accent), var(--accent2)); border-radius: 999px; box-shadow: 0 0 24px color-mix(in srgb, var(--accent) 48%, transparent); }}

    .stTabs [data-baseweb="tab-list"] {{ gap: 8px; border-bottom: 1px solid var(--border); }}
    .stTabs [data-baseweb="tab"] {{ border-radius: 999px 999px 0 0; padding: 12px 16px; color: var(--muted) !important; background: color-mix(in srgb, var(--card) 42%, transparent); border: 1px solid transparent; }}
    .stTabs [aria-selected="true"] {{ background: color-mix(in srgb, var(--accent) 20%, var(--card)); color: var(--text) !important; border: 1px solid var(--border); border-bottom: 3px solid var(--accent); box-shadow: 0 12px 28px var(--shadow); }}

    div[data-testid="stMetric"] {{ padding: 18px; }}
    div[data-testid="stMetricValue"] {{ color: var(--text) !important; font-size: 1.85rem; font-family: var(--title-font); }}
    .stButton > button {{ border-radius: 16px; border: 1px solid var(--border); background: linear-gradient(135deg, var(--accent), var(--accent2)); color: white !important; font-weight: 900; box-shadow: 0 14px 36px color-mix(in srgb, var(--accent) 28%, transparent); transition: all 0.22s ease; }}
    .stButton > button:hover {{ transform: translateY(-2px) scale(1.01); filter: brightness(1.08); border: 1px solid var(--accent2); }}
    .stChatMessage {{ background: color-mix(in srgb, var(--card) 86%, transparent) !important; border: 1px solid var(--border); border-radius: 22px; padding: 10px; box-shadow: 0 14px 34px var(--shadow); }}
    input, textarea, div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {{ border-radius: 16px !important; background: color-mix(in srgb, var(--card) 82%, black 3%) !important; color: var(--text) !important; border-color: var(--border) !important; }}
    input::placeholder, textarea::placeholder {{ color: color-mix(in srgb, var(--muted) 86%, transparent) !important; opacity: 1 !important; }}

    /* BaseWeb dropdown fix: dark/gothic mode white menu bug */
    div[data-baseweb="popover"] {{ background: transparent !important; z-index: 999999 !important; }}
    div[data-baseweb="popover"] > div {{ background: var(--card) !important; border: 1px solid var(--border) !important; border-radius: 18px !important; box-shadow: 0 24px 70px var(--shadow) !important; overflow: hidden !important; backdrop-filter: blur(16px); }}
    ul[role="listbox"] {{ background: var(--card) !important; color: var(--text) !important; border: 1px solid var(--border) !important; }}
    li[role="option"], div[role="option"] {{ background: var(--card) !important; color: var(--text) !important; font-weight: 700 !important; }}
    li[role="option"]:hover, div[role="option"]:hover, li[aria-selected="true"], div[aria-selected="true"] {{ background: color-mix(in srgb, var(--accent) 26%, var(--card)) !important; color: var(--text) !important; }}
    div[data-baseweb="select"] svg {{ fill: var(--text) !important; }}

    .stDownloadButton > button {{ border-radius: 16px; border: 1px solid var(--border); }}
    """



def build_theme_fx_css():
    return """
    .fx-layer { position: fixed; inset: 0; pointer-events: none; z-index: 0; overflow: hidden; }
    .fx-layer * { pointer-events: none; }
    .gothic-web { position: fixed; top: 0; left: 0; width: 230px; height: 230px; opacity: 0.28; background: radial-gradient(circle at 0 0, transparent 0 24px, rgba(255,255,255,0.17) 25px 26px, transparent 27px 52px, rgba(255,255,255,0.13) 53px 54px, transparent 55px 82px), repeating-conic-gradient(from 0deg at 0 0, rgba(255,255,255,0.18) 0deg 2deg, transparent 2deg 18deg); filter: blur(0.2px); }
    .spider-thread { position: fixed; top: 0; right: 150px; width: 2px; height: 170px; background: rgba(255,255,255,0.26); }
    .spider-body { position: fixed; top: 150px; right: 136px; font-size: 32px; animation: spiderSwing 4s ease-in-out infinite alternate; filter: drop-shadow(0 8px 12px rgba(0,0,0,0.40)); }
    @keyframes spiderSwing { from { transform: rotate(-8deg) translateY(0px); } to { transform: rotate(8deg) translateY(12px); } }
    .chain { position: fixed; top: -8px; font-size: 40px; opacity: 0.48; animation: chainSway 5s ease-in-out infinite alternate; filter: drop-shadow(0 8px 12px rgba(0,0,0,0.35)); }
    .chain.c1 { left: 8%; animation-delay: 0s; } .chain.c2 { left: 18%; animation-delay: 1s; } .chain.c3 { left: 82%; animation-delay: 0.5s; } .chain.c4 { left: 91%; animation-delay: 1.5s; }
    @keyframes chainSway { from { transform: translateY(0px) rotate(-4deg); } to { transform: translateY(14px) rotate(4deg); } }
    .ribbon { position: fixed; top: -50px; font-size: 28px; opacity: 0.62; animation: ribbonFall linear infinite; filter: drop-shadow(0 6px 10px rgba(255,143,171,0.22)); }
    .r1 { left: 8%; animation-duration: 11s; animation-delay: 0s; } .r2 { left: 22%; animation-duration: 13s; animation-delay: 1s; } .r3 { left: 36%; animation-duration: 10s; animation-delay: 2s; } .r4 { left: 52%; animation-duration: 14s; animation-delay: 0.5s; } .r5 { left: 68%; animation-duration: 12s; animation-delay: 1.7s; } .r6 { left: 84%; animation-duration: 15s; animation-delay: 0.2s; }
    @keyframes ribbonFall { 0% { transform: translateY(-40px) rotate(0deg); opacity: 0; } 10% { opacity: 0.62; } 100% { transform: translateY(110vh) rotate(220deg); opacity: 0; } }
    .cleanboy-token { position: fixed; top: -50px; font-size: 26px; opacity: 0.50; animation: tokenFall linear infinite; filter: drop-shadow(0 6px 10px rgba(139,200,255,0.20)); }
    .cb1 { left: 12%; animation-duration: 12s; animation-delay: 0s; } .cb2 { left: 30%; animation-duration: 15s; animation-delay: 1s; } .cb3 { left: 48%; animation-duration: 11s; animation-delay: 2s; } .cb4 { left: 66%; animation-duration: 14s; animation-delay: 0.5s; } .cb5 { left: 84%; animation-duration: 13s; animation-delay: 1.4s; }
    @keyframes tokenFall { 0% { transform: translateY(-40px) rotate(0deg); opacity: 0; } 10% { opacity: 0.48; } 100% { transform: translateY(110vh) rotate(90deg); opacity: 0; } }
    .vintage-scratch { position: fixed; top: 0; bottom: 0; width: 1px; background: rgba(255,255,255,0.18); opacity: .35; animation: scratchFlicker 2.8s infinite; }
    .vintage-scratch.s1 { left: 18%; } .vintage-scratch.s2 { left: 76%; animation-delay: .8s; }
    @keyframes scratchFlicker { 0%,100% { opacity: .06; } 45% { opacity: .36; } 47% { opacity: .02; } }
    .gold-dust { position: fixed; top: -30px; font-size: 18px; opacity: .46; animation: goldFloat linear infinite; }
    .g1 { left: 14%; animation-duration: 13s; } .g2 { left: 42%; animation-duration: 16s; animation-delay: 1s; } .g3 { left: 70%; animation-duration: 14s; animation-delay: .4s; } .g4 { left: 88%; animation-duration: 17s; animation-delay: 1.8s; }
    @keyframes goldFloat { 0% { transform: translateY(-30px) scale(.9); opacity: 0; } 12% { opacity: .42; } 100% { transform: translateY(105vh) scale(1.25); opacity: 0; } }
    """


def render_theme_fx(theme, gender):
    html = ""
    if theme == "Gotik & Dark Academia" and gender == "Erkek":
        html = """<div class="fx-layer"><div class="chain c1">⛓️</div><div class="chain c2">⛓️</div><div class="chain c3">⛓️</div><div class="chain c4">⛓️</div></div>"""
    elif theme == "Gotik & Dark Academia":
        html = """<div class="fx-layer"><div class="gothic-web"></div><div class="spider-thread"></div><div class="spider-body">🕷️</div></div>"""
    elif theme == "Clean & Soft Girl" and gender == "Erkek":
        html = """<div class="fx-layer"><div class="cleanboy-token cb1">🫧</div><div class="cleanboy-token cb2">⌚</div><div class="cleanboy-token cb3">🧼</div><div class="cleanboy-token cb4">✦</div><div class="cleanboy-token cb5">🫧</div></div>"""
    elif theme == "Clean & Soft Girl":
        html = """<div class="fx-layer"><div class="ribbon r1">🎀</div><div class="ribbon r2">🎀</div><div class="ribbon r3">🎀</div><div class="ribbon r4">🎀</div><div class="ribbon r5">🎀</div><div class="ribbon r6">🎀</div></div>"""
    elif theme == "Vintage & Retro":
        html = """<div class="fx-layer"><div class="vintage-scratch s1"></div><div class="vintage-scratch s2"></div></div>"""
    elif theme == "Old Money / Quiet Luxury":
        html = """<div class="fx-layer"><div class="gold-dust g1">✦</div><div class="gold-dust g2">✧</div><div class="gold-dust g3">✦</div><div class="gold-dust g4">✧</div></div>"""
    st.markdown(html, unsafe_allow_html=True)


def render_theme_header(theme, gender, day_mode, style_identity):
    kit = THEME_KITS[theme]
    display_title = kit["title"]
    if theme == "Clean & Soft Girl" and gender == "Erkek":
        display_title = "Clean Glow Gentleman"
    elif theme == "Gotik & Dark Academia" and gender == "Erkek":
        display_title = "Bad Boy Nocturne"
    elif theme == "Vintage & Retro" and gender == "Erkek":
        display_title = "Retro Gentleman Archive"
    mode_icon = "🌙" if day_mode == "Gece" else "☀️"
    mode_text = "Gece Modu" if day_mode == "Gece" else "Gündüz Modu"
    chips_html = "".join([f'<span class="aura-chip">✦ {chip}</span>' for chip in kit["chips"]])

    st.markdown(
        f"""
        <div class="aura-hero">
            <div class="aura-kicker">{kit["emoji"]} {mode_icon} {mode_text} / {gender} / {kit["kicker"]}</div>
            <div class="aura-title">{display_title}</div>
            <div class="aura-subtitle">
                <b>{style_identity}</b><br>
                {kit["subtitle"]}<br>
                <i>{kit["quote"]}</i>
            </div>
            <div class="aura-chip-row">{chips_html}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_theme_ritual(theme):
    kit = THEME_KITS[theme]
    lines_html = "".join([f'<div class="ritual-line">✧ {line}</div>' for line in kit["ritual_lines"]])
    st.markdown(
        f"""
        <div class="ritual-card">
            <div class="ritual-title">{kit["ritual_title"]}</div>
            {lines_html}
            <br>
            <div class="theme-meter"><div class="theme-meter-fill"></div></div>
            <p style="margin-top:10px; opacity:0.72; position:relative; z-index:1;">
                Tema uyumu: dolabındaki parçalar arttıkça bu alan daha akıllı yorum verecek.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_theme_specific_tools(theme):
    special = THEME_KITS[theme]["special"]
    st.markdown(f"### {special['title']}")
    cols = st.columns(3)
    answers = {}
    for idx, (label, options) in enumerate(special["fields"]):
        with cols[idx % 3]:
            answers[label] = st.selectbox(label, options, key=f"theme_tool_{theme}_{idx}")
    st.info(special["note"])
    return answers

# -----------------------------
# SIDEBAR CONFIG
# -----------------------------

st.sidebar.markdown("## 🎭 Style & Identity Config")

gender = st.sidebar.selectbox(
    "Cinsiyet / Stil Kimliği",
    ["Kadın", "Erkek", "Unisex / Belirtmek istemiyorum"]
)

theme = st.sidebar.selectbox(
    "Aura / Theme",
    [
        "Vintage & Retro",
        "Gotik & Dark Academia",
        "Old Money / Quiet Luxury",
        "Clean & Soft Girl"
    ]
)

day_mode = st.sidebar.radio(
    "Görünüm Modu",
    ["Gündüz", "Gece"],
    horizontal=True
)

style_identity = get_style_identity(gender, theme)

st.markdown(
    f"<style>{build_advanced_css(theme, day_mode)} {build_theme_fx_css()}</style>",
    unsafe_allow_html=True
)

render_theme_fx(theme, gender)


# -----------------------------
# HEADER
# -----------------------------

render_theme_header(theme, gender, day_mode, style_identity)


# -----------------------------
# TABS
# -----------------------------

tab_dashboard, tab_budget, tab_add, tab_wardrobe, tab_ai, tab_chat = st.tabs(
    [
        "📊 Dashboard",
        "💰 Bütçe",
        "📥 Ürün Ekle",
        "👗 Gardırop",
        "🧠 Kombin Motoru",
        "💬 AuraMini Chatbot"
    ]
)


# -----------------------------
# DASHBOARD
# -----------------------------

with tab_dashboard:
    st.markdown("## 📊 Aylık Finans & Stil Panosu")

    total_spent = get_total_spent()
    remaining = get_remaining_budget()
    monthly_limit = st.session_state.budget_settings["monthly_limit"]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Aylık Limit", money(monthly_limit))
    col2.metric("Toplam Harcama", money(total_spent))
    col3.metric("Kalan Bütçe", money(remaining))
    col4.metric("Kayıtlı Ürün", len(st.session_state.wardrobe_items))

    st.info(get_budget_status_text())

    st.markdown("## 🎭 Tema Paneli")
    render_theme_ritual(theme)
    render_theme_specific_tools(theme)

    if st.session_state.wardrobe_items:
        df = pd.DataFrame([
            {
                "Ad": item["name"],
                "Kategori": item["main_category"],
                "Alt Kategori": item["sub_category"],
                "Fiyat": item["price"],
                "Kullanım": item["usage_count"],
                "Kullanım Başı Maliyet": get_cost_per_wear(item["price"], item["usage_count"]),
                "Duygu": item["emotion"],
                "İhtiyaç Durumu": item["need_level"],
                "Tema": item["theme"]
            }
            for item in st.session_state.wardrobe_items
        ])

        st.markdown("### Kategori Harcama Dağılımı")
        category_df = df.groupby("Kategori", as_index=False)["Fiyat"].sum()
        st.bar_chart(category_df, x="Kategori", y="Fiyat")

        st.markdown("### Ürün Listesi")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 CSV Olarak İndir",
            data=csv,
            file_name="auraatelier_gardrop_butce.csv",
            mime="text/csv"
        )
    else:
        st.warning("Henüz ürün eklenmedi. İlk parçayı ekleyince dashboard canlanacak.")


# -----------------------------
# BUDGET SETTINGS
# -----------------------------

with tab_budget:
    st.markdown("## 💰 Bütçe Ayarları")

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        monthly_income = st.number_input(
            "Aylık gelir / burs",
            min_value=0.0,
            step=100.0,
            value=float(st.session_state.budget_settings["monthly_income"])
        )

    with col_b:
        monthly_limit = st.number_input(
            "Bu ay harcama limiti",
            min_value=0.0,
            step=100.0,
            value=float(st.session_state.budget_settings["monthly_limit"])
        )

    with col_c:
        saving_goal = st.number_input(
            "Birikim / altın hedefi",
            min_value=0.0,
            step=100.0,
            value=float(st.session_state.budget_settings["saving_goal"])
        )

    st.markdown("### Kategori Limitleri")

    new_limits = {}
    limit_cols = st.columns(2)

    categories_for_limits = [
        "Üst Giyim",
        "Alt Giyim",
        "Dış Giyim",
        "Ayakkabı",
        "Aksesuar",
        "Kozmetik / Bakım",
        "Diğer"
    ]

    for idx, category in enumerate(categories_for_limits):
        with limit_cols[idx % 2]:
            current_value = st.session_state.budget_settings["category_limits"].get(category, 0.0)
            new_limits[category] = st.number_input(
                f"{category} limiti",
                min_value=0.0,
                step=50.0,
                value=float(current_value),
                key=f"limit_{category}"
            )

    if st.button("💾 Bütçeyi Kaydet"):
        new_budget_settings = {
    "monthly_income": monthly_income,
    "monthly_limit": monthly_limit,
    "saving_goal": saving_goal,
    "category_limits": new_limits
}

        st.session_state.budget_settings = new_budget_settings
        save_budget_settings(new_budget_settings)
        st.success("Bütçe ayarları kaydedildi. Finans kristali güncellendi. 🔮")
        st.rerun()

    st.markdown("---")
    st.markdown("### Anlık Bütçe Yorumu")
    st.write(get_budget_status_text())


# -----------------------------
# ADD ITEM
# -----------------------------

with tab_add:
    st.markdown("## 📥 Parça Ekleme Konsolu")

    col_input, col_check = st.columns([1.2, 1])

    with col_input:
        main_category = st.selectbox(
            "Ana Kategori",
            [
                "Üst Giyim",
                "Alt Giyim",
                "Dış Giyim",
                "Ayakkabı",
                "Aksesuar",
                "Kozmetik / Bakım",
                "Diğer"
            ]
        )

        sub_options = {
            "Üst Giyim": ["Bluz", "Tişört", "Gömlek", "Atlet", "Crop", "Kazak", "Sweatshirt", "Diğer"],
            "Alt Giyim": ["Pantolon", "Jean", "Etek", "Şort", "Tayt", "Diğer"],
            "Dış Giyim": ["Ceket", "Trençkot", "Mont", "Hırka", "Kimono", "Gömlek Ceket", "Diğer"],
            "Ayakkabı": ["Sneaker", "Babet", "Bot", "Sandalet", "Topuklu", "Diğer"],
            "Aksesuar": ["Kolye", "Bileklik", "Yüzük", "Kemer", "Bel Zinciri", "Çanta", "Diğer"],
            "Kozmetik / Bakım": ["Güneş Kremi", "Serum", "Nemlendirici", "Far Paleti", "Ruj", "Parfüm", "Diğer"],
            "Diğer": ["Diğer"]
        }

        sub_category = st.selectbox(
            "Alt Kategori",
            sub_options[main_category]
        )

        name = st.text_input("Parça Tanımı / Marka", placeholder="Örn: LCW Etnik Desen Bluz")

        price = st.number_input(
            "Satın Alım Bedeli",
            min_value=0.0,
            step=10.0
        )

        color = st.text_input("Renk / Desen", placeholder="Örn: bordo, gri çizgili, etnik desen")

        size = st.text_input("Beden", placeholder="Örn: 2XL, 46, M")

        usage_count = st.number_input(
            "Tahmini / mevcut kullanım sayısı",
            min_value=1,
            step=1,
            value=1
        )

        need_level = st.selectbox(
            "Bu ürün ne kadar gerekli?",
            [
                "Zorunlu ihtiyaç",
                "Eksik tamamlıyor",
                "Kombin güçlendiriyor",
                "Keyfi ama kullanırım",
                "Tamamen moral alışverişi"
            ]
        )

        emotion = st.selectbox(
            "Alışveriş motivasyonu",
            [
                "Sakin / planlı",
                "Stres",
                "Final haftası",
                "Kıyas / moral bozukluğu",
                "Can sıkıntısı",
                "Oda / çevre gerginliği",
                "Ödül",
                "Gerçek ihtiyaç"
            ]
        )

        modest_level = st.selectbox(
            "Kapalı / rahatlık tercihi",
            [
                "Fark etmez",
                "Çok açık olmasın",
                "Kapalı ve ferah olsun",
                "Oversize / bol dursun",
                "Katmanlı kombin gerekir"
            ]
        )

        uploaded_file = st.file_uploader(
            "Ürünün fotoğrafını yükle",
            type=["png", "jpg", "jpeg"]
        )

        notes = st.text_area(
            "Not",
            placeholder="Örn: Yazlıkta giyilecek, crop olduğu için üstüne gömlek gerekir."
        )

    with col_check:
        st.markdown("### 🧪 Satın Alma Analizi")

        if name and price > 0:
            analysis = analyze_purchase(
                name=name,
                price=price,
                category=main_category,
                emotion=emotion,
                need_level=need_level,
                expected_usage=usage_count
            )

            if analysis["level"] == "red":
                st.error(f"🚨 {analysis['title']}")
            elif analysis["level"] == "yellow":
                st.warning(f"🟡 {analysis['title']}")
            elif analysis["level"] == "blue":
                st.info(f"🔵 {analysis['title']}")
            else:
                st.success(f"🟢 {analysis['title']}")

            st.write(analysis["message"])
            st.metric("Kullanım Başı Maliyet", money(analysis["cpw"]))

            st.markdown("### Bütçeye Etki")
            st.write(f"Şu an kalan bütçe: **{money(get_remaining_budget())}**")
            st.write(f"Bu ürün sonrası kalan: **{money(get_remaining_budget() - price)}**")
        else:
            st.info("Ürün adı ve fiyat girince analiz burada belirecek.")

    if st.button("🚀 Parçayı Gardıroba Mühürle"):
        if not name:
            st.error("Parça adı boş olamaz.")
        elif price <= 0:
            st.error("Fiyat 0'dan büyük olmalı.")
        else:
            img_bytes = uploaded_file.getvalue() if uploaded_file is not None else None

            new_item = {
                "id": f"item_{datetime.now().timestamp()}",
                "name": name,
                "main_category": main_category,
                "sub_category": sub_category,
                "price": price,
                "color": color,
                "size": size,
                "usage_count": usage_count,
                "need_level": need_level,
                "emotion": emotion,
                "modest_level": modest_level,
                "theme": theme,
                "gender": gender,
                "style_identity": style_identity,
                "image": img_bytes,
                "notes": notes,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }

            st.session_state.wardrobe_items.append(new_item)
            save_wardrobe_item(new_item)
            st.success(f"'{name}' gardıroba kaydedildi.")
            st.rerun()


# -----------------------------
# WARDROBE
# -----------------------------

with tab_wardrobe:
    st.markdown("## 👗 Canlı Gardırop & Görsel Matris")

    if not st.session_state.wardrobe_items:
        st.info("Henüz ürün eklenmedi. Soluk bir askı bekliyor, ilk parçanı ekle.")
    else:
        for idx, item in enumerate(st.session_state.wardrobe_items):
            col_card, col_image, col_actions = st.columns([2, 1, 0.7])

            with col_card:
                st.markdown(
                    f"""
                    <div class="aura-card">
                        <h3>{item["name"]}</h3>
                        <p><b>Kategori:</b> {item["main_category"]} / {item["sub_category"]}</p>
                        <p><b>Fiyat:</b> {money(item["price"])} | <b>Kullanım:</b> {item["usage_count"]}</p>
                        <p><b>Kullanım Başı Maliyet:</b> {money(get_cost_per_wear(item["price"], item["usage_count"]))}</p>
                        <p><b>Renk:</b> {item["color"] or "Belirtilmedi"} | <b>Beden:</b> {item["size"] or "Belirtilmedi"}</p>
                        <p><b>Duygu:</b> {item["emotion"]} | <b>İhtiyaç:</b> {item["need_level"]}</p>
                        <p><b>Stil:</b> {item["style_identity"]}</p>
                        <p class="small-muted">{item["notes"]}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with col_image:
                if item["image"] is not None:
                    image = Image.open(io.BytesIO(item["image"]))
                    st.image(image, caption=item["name"], use_container_width=True)
                else:
                    st.caption("Görsel yok")

            with col_actions:
                if st.button("➕ Kullanım", key=f"use_{idx}"):
                    st.session_state.wardrobe_items[idx]["usage_count"] += 1
                    st.rerun()

                if st.button("🗑️ Sil", key=f"delete_{idx}"):
                    st.session_state.wardrobe_items.pop(idx)
                    st.rerun()

            st.markdown("---")


# -----------------------------
# AI / OUTFIT ENGINE
# -----------------------------

with tab_ai:
    st.markdown("## 🧠 AI Intellect Matrix")

    st.write(
        "Bu sekme şimdilik yerel kombin motoru gibi çalışıyor. "
        "İleride gerçek yapay zekâ API'si bağlanınca ürün görselleri, renkler, bedenler, stil aurası ve bütçe birlikte analiz edilebilir."
    )

    occasion = st.selectbox(
        "Kombin amacı",
        [
            "Günlük rahat",
            "Yazlık / sıcak hava",
            "Final haftası rahatlığı",
            "Arkadaş buluşması",
            "Kapalı ama ferah",
            "Old money şık",
            "Gotik / dark academia",
            "Soft girl temiz görünüm"
        ]
    )

    if st.button("🔮 Kombin Simülasyonu Yaptır"):
        if len(st.session_state.wardrobe_items) < 2:
            st.warning("Kombin için en az 2 ürün eklemelisin.")
        else:
            st.success("Analiz tamamlandı.")
            st.markdown("### AuraMini Kombin Önerisi")
            st.write(generate_simple_outfit_advice(occasion))

            st.markdown("### Stil Yorumu")
            if "Kapalı" in occasion or "Yazlık" in occasion:
                st.info(
                    "Kapalı ama ferah görünüm için ince kumaş, açık ton, bol kesim ve katmanlı kullanım daha iyi çalışır. "
                    "Yeni ürün almadan önce gömlek + pantolon + sade aksesuar üçlüsünü dene."
                )
            elif "Gotik" in occasion:
                st.info(
                    "Gotik etki için koyu ton, metal aksesuar, keskin siluet ve tek vurucu detay yeterli. "
                    "Her parçayı siyah yapmak zorunda değilsin; bordo ve gri de çok iyi çalışır."
                )
            elif "Old money" in occasion:
                st.info(
                    "Old money etkisi için sade renk, iyi oturan pantolon, temiz yaka ve az aksesuar yeterli. "
                    "Logodan çok kumaş ve duruş konuşsun."
                )
            else:
                st.info(
                    "Bu kombin dolabındaki parçaları çalıştırır ve kullanım başı maliyeti düşürür. "
                    "Yeni alışverişten önce bu kombini bir kez dene."
                )


# -----------------------------
# CHATBOT
# -----------------------------

with tab_chat:
    st.markdown("## 💬 AuraMini Chatbot")
    st.caption("Bütçe, kombin ve alışveriş dürtüsü için mini danışman.")

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_prompt = st.chat_input("Örn: 350 TL bileklik alayım mı? / Bütçem ne durumda?")

    if user_prompt:
        st.session_state.chat_messages.append(
            {"role": "user", "content": user_prompt}
        )

        reply = mini_chatbot_reply(user_prompt)

        st.session_state.chat_messages.append(
            {"role": "assistant", "content": reply}
        )

        st.rerun()