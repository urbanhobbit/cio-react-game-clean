import streamlit as st
import json
from pathlib import Path
import datetime
import shutil
import os

# ==============================
# DOSYA YOLLARI / KONFİG
# ==============================
BASE_DIR = Path(__file__).resolve().parent

SCENARIO_FILES = {
    "Çocuk versiyonu": BASE_DIR / "scenarios_child.json",
    "Ebeveyn versiyonu": BASE_DIR / "scenarios_parent.json",
}

BACKUP_DIR = BASE_DIR / "backups"


# ==============================
# YARDIMCI FONKSİYONLAR
# ==============================
def save_data(file_path: Path, data):
    """JSON'u pretty-print şekilde diske yaz (geçici dosya üzerinden)."""
    tmp = file_path.with_suffix(file_path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(file_path)


def load_data(file_path: Path):
    """JSON oku; yoksa veya hatalıysa boş dict döndür."""
    try:
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except json.JSONDecodeError as e:
        st.error(f"JSON hatası: {file_path.name} bozuk görünüyor → {e}")
        return {}
    except Exception as e:
        st.error(f"Dosya okunamadı: {file_path} → {e}")
        return {}
    return {}


def write_through_verify(file_path: Path, data) -> bool:
    """Yaz + hemen geri okuyarak doğrula."""
    save_data(file_path, data)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reread = json.load(f)
        return reread == data
    except Exception:
        return False


def get_default_scenario(title="Yeni Senaryo Başlığı"):
    """Yeni senaryo için temel şablon."""
    return {
        "title": title,
        "icon": "✨",
        "story": "Buraya krizin hikayesini yazın. **Görev**: Oyuncunun görevini buraya yazın.",
        "advisors": [
            {"name": "Danışman 1 (Örn: Güvenlik)", "text": "Danışman görüşünü buraya yazın."},
            {"name": "Danışman 2 (Örn: Hukuk)", "text": "Danışman görüşünü buraya yazın."},
        ],
        "action_cards": [
            {
                "id": "A",
                "name": "Aksiyon Kartı A",
                "cost": 30,
                "hr_cost": 10,
                "speed": "fast",
                "security_effect": 40,
                "freedom_cost": 30,
                "side_effect_risk": 0.4,
                "safeguard_reduction": 0.5,
                "tooltip": "Hızlı ama riskli bir seçenek.",
            },
            {
                "id": "B",
                "name": "Aksiyon Kartı B",
                "cost": 20,
                "hr_cost": 15,
                "speed": "medium",
                "security_effect": 30,
                "freedom_cost": 15,
                "side_effect_risk": 0.2,
                "safeguard_reduction": 0.7,
                "tooltip": "Dengeli bir seçenek.",
            },
        ],
        "immediate_text": "Anlık etki metnini buraya yazın. Seçilen aksiyonu göstermek için {} kullanın.",
        "delayed_text": "Gecikmeli etki metnini buraya yazın.",
    }


def _safe_container():
    """Yeni Streamlit'teki border parametresi varsa kullan, yoksa normal container."""
    try:
        return st.container(border=True)
    except TypeError:
        return st.container()


# ==============================
# BACKUP / RESTORE ARAYÜZÜ
# ==============================
def backup_and_restore_ui(selected_set_key: str, current_file: Path):
    st.sidebar.title("🗄️ Yedekleme & Geri Yükleme")

    if st.sidebar.button("Yeni Yedek Oluştur", use_container_width=True):
        BACKUP_DIR.mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_name = f"{selected_set_key}_scenarios_{ts}.json"
        b_path = BACKUP_DIR / backup_name
        if current_file.exists():
            shutil.copy2(current_file, b_path)
            st.sidebar.success(f"Yedek oluşturuldu: {backup_name}")
        else:
            st.sidebar.warning("Kaynak senaryo dosyası bulunamadı, yedek alınamadı.")

    # Mevcut yedekleri listele (sadece seçili set için)
    if BACKUP_DIR.exists():
        backups = sorted(
            [p for p in BACKUP_DIR.glob(f"{selected_set_key}_scenarios_*.json")],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if backups:
            st.sidebar.markdown("---")
            labels = [p.name for p in backups]
            selected_backup = st.sidebar.selectbox("Geri yüklenecek yedek:", labels)
            if st.sidebar.button("Seçili Yedeği Geri Yükle", use_container_width=True):
                chosen = BACKUP_DIR / selected_backup
                if chosen.exists():
                    shutil.copy2(chosen, current_file)
                    st.sidebar.success(f"Yedek geri yüklendi: {selected_backup}")
                    st.rerun()
                else:
                    st.sidebar.error("Seçili yedek dosyası bulunamadı.")


# ==============================
# SENARYO İŞLEMLERİ ARAYÜZÜ
# ==============================
def add_scenario_ui(scenarios_data: dict, current_file: Path):
    st.header("➕ Yeni Senaryo Oluştur")

    with st.form(key="new_scenario_form"):
        new_id = st.text_input(
            "Yeni Senaryo ID'si (örn: 'earthquake_2')",
            help="JSON anahtarı. Boşluk yerine '_' kullanın; Türkçe karakterlerden kaçının.",
        ).lower().strip().replace(" ", "_")

        new_title = st.text_input("Yeni Senaryo Başlığı (oyunda görünen)")

        submitted = st.form_submit_button("Oluştur ve Kaydet")
        if submitted:
            if not new_id or not new_title:
                st.error("Lütfen hem ID hem de Başlık girin.")
            elif new_id in scenarios_data:
                st.error(f"'{new_id}' zaten var.")
            else:
                scenarios_data[new_id] = get_default_scenario(new_title)
                save_data(current_file, scenarios_data)
                st.success(f"'{new_title}' oluşturuldu!")
                st.session_state.mode = "edit"
                st.rerun()


def delete_scenario_ui(scenarios_data: dict, current_file: Path):
    st.header("🗑️ Senaryo Sil")
    if not scenarios_data:
        st.warning("Silinecek senaryo yok.")
        return

    scenario_titles = {data.get("title", f"ID: {k}"): k for k, data in scenarios_data.items()}
    selected_title = st.selectbox("Silinecek Senaryo", options=sorted(scenario_titles.keys()))

    if selected_title:
        st.warning(f"**DİKKAT:** '{selected_title}' kalıcı olarak silinecek.")
        if st.button("Evet, Sil", type="primary"):
            key = scenario_titles[selected_title]
            scenarios_data.pop(key, None)
            save_data(current_file, scenarios_data)
            st.success(f"'{selected_title}' silindi!")
            st.session_state.mode = "edit"
            st.rerun()


def edit_scenarios_ui(scenarios_data: dict, current_file: Path):
    st.header("📝 Senaryo Editörü")

    if not scenarios_data:
        st.warning("Hiç senaryo yok. Kenar çubuğundan ekleyin.")
        return scenarios_data

    # Başlığa göre seçim
    scenario_titles = {data.get("title", f"ID: {k}"): k for k, data in scenarios_data.items()}
    selected_title = st.selectbox("Düzenlenecek Senaryo", options=sorted(scenario_titles.keys()), key="sel_scenario")
    if not selected_title:
        return scenarios_data

    selected_key = scenario_titles[selected_title]
    scenario = scenarios_data[selected_key]

    # Dosya değişiklik zamanını kullanarak form key'lerini sabitle
    try:
        _ver = int(current_file.stat().st_mtime)
    except Exception:
        _ver = 0

    st.subheader(f"'{scenario.get('title', '')}' Senaryosunu Düzenle")

    # Temel alanlar
    scenario["title"] = st.text_input(
        "Başlık",
        value=scenario.get("title", ""),
        key=f"title_{selected_key}_{_ver}",
    )
    scenario["icon"] = st.text_input(
        "İkon (Emoji)",
        value=scenario.get("icon", ""),
        max_chars=2,
        key=f"icon_{selected_key}_{_ver}",
    )
    scenario["story"] = st.text_area(
        "Hikaye",
        value=scenario.get("story", ""),
        height=220,
        key=f"story_{selected_key}_{_ver}",
    )
    scenario["immediate_text"] = st.text_area(
        "Anlık Etki Metni",
        value=scenario.get("immediate_text", ""),
        height=120,
        key=f"imm_text_{selected_key}_{_ver}",
    )
    scenario["delayed_text"] = st.text_area(
        "Gecikmeli Etki Metni",
        value=scenario.get("delayed_text", ""),
        height=120,
        key=f"del_text_{selected_key}_{_ver}",
    )

    # Danışmanlar
    st.subheader("Danışmanlar")
    advisors = scenario.get("advisors", [])
    col_add_adv, col_del_adv = st.columns(2)
    with col_add_adv:
        if st.button("➕ Danışman Ekle"):
            advisors.append({"name": "Yeni Danışman", "text": ""})
            scenario["advisors"] = advisors
            save_data(current_file, scenarios_data)
            st.rerun()
    with col_del_adv:
        if advisors and st.button("➖ Son Danışmanı Sil"):
            advisors.pop()
            scenario["advisors"] = advisors
            save_data(current_file, scenarios_data)
            st.rerun()

    for i, advisor in enumerate(advisors):
        with _safe_container():
            st.markdown(f"**Danışman {i+1}**")
            advisor["name"] = st.text_input(
                "Danışman Adı",
                value=advisor.get("name", ""),
                key=f"adv_name_{selected_key}_{i}_{_ver}",
            )
            advisor["text"] = st.text_area(
                "Danışman Metni",
                value=advisor.get("text", ""),
                key=f"adv_text_{selected_key}_{i}_{_ver}",
                height=150,
            )

    scenario["advisors"] = advisors

    # Aksiyon Kartları
    st.subheader("Aksiyon Kartları")
    cards = scenario.get("action_cards", [])
    col_add_card, col_del_card = st.columns(2)
    with col_add_card:
        if st.button("➕ Kart Ekle"):
            new_id = chr(ord("A") + len(cards)) if len(cards) < 26 else f"X{len(cards)}"
            cards.append(
                {
                    "id": new_id,
                    "name": f"Aksiyon Kartı {new_id}",
                    "cost": 20,
                    "hr_cost": 10,
                    "speed": "medium",
                    "security_effect": 20,
                    "freedom_cost": 10,
                    "side_effect_risk": 0.2,
                    "safeguard_reduction": 0.7,
                    "tooltip": "Yeni aksiyon kartı açıklaması.",
                }
            )
            scenario["action_cards"] = cards
            save_data(current_file, scenarios_data)
            st.rerun()
    with col_del_card:
        if cards and st.button("➖ Son Kartı Sil"):
            cards.pop()
            scenario["action_cards"] = cards
            save_data(current_file, scenarios_data)
            st.rerun()

    for i, card in enumerate(cards):
        with _safe_container():
            st.markdown(f"**Aksiyon Kartı {i+1} (ID: {card.get('id', '')})**")

            card["name"] = st.text_input(
                "Kart Adı",
                value=card.get("name", ""),
                key=f"card_name_{selected_key}_{i}_{_ver}",
            )
            card["tooltip"] = st.text_area(
                "İpucu Metni",
                value=card.get("tooltip", ""),
                key=f"card_tooltip_{selected_key}_{i}_{_ver}",
                height=140,
            )

            c1, c2, c3 = st.columns(3)
            with c1:
                card["cost"] = st.number_input(
                    "Maliyet (Bütçe)",
                    value=int(card.get("cost", 0)),
                    key=f"card_cost_{selected_key}_{i}_{_ver}",
                )
                card["hr_cost"] = st.number_input(
                    "Maliyet (İnsan Kaynağı)",
                    value=int(card.get("hr_cost", 0)),
                    key=f"card_hr_{selected_key}_{i}_{_ver}",
                )
                card["speed"] = st.selectbox(
                    "Hız (speed)",
                    options=["fast", "medium", "slow"],
                    index=["fast", "medium", "slow"].index(
                        card.get("speed", "medium") if card.get("speed", "medium") in ["fast", "medium", "slow"] else "medium"
                    ),
                    key=f"card_speed_{selected_key}_{i}_{_ver}",
                )
            with c2:
                card["security_effect"] = st.slider(
                    "Güvenlik Etkisi",
                    0,
                    100,
                    int(card.get("security_effect", 0)),
                    key=f"card_sec_{selected_key}_{i}_{_ver}",
                )
                card["freedom_cost"] = st.slider(
                    "Özgürlük Maliyeti",
                    0,
                    100,
                    int(card.get("freedom_cost", 0)),
                    key=f"card_free_{selected_key}_{i}_{_ver}",
                )
            with c3:
                card["side_effect_risk"] = st.slider(
                    "Yan Etki Riski",
                    0.0,
                    1.0,
                    float(card.get("side_effect_risk", 0.0)),
                    format="%.2f",
                    key=f"card_risk_{selected_key}_{i}_{_ver}",
                )
                card["safeguard_reduction"] = st.slider(
                    "Güvence Azaltma Etkisi",
                    0.0,
                    1.0,
                    float(card.get("safeguard_reduction", 0.0)),
                    format="%.2f",
                    key=f"card_safe_{selected_key}_{i}_{_ver}",
                )

    scenario["action_cards"] = cards
    scenarios_data[selected_key] = scenario
    return scenarios_data


# ==============================
# ANA UYGULAMA
# ==============================
def main():
    st.set_page_config(layout="wide", page_title="CIO Oyunu Senaryo Editörü")
    st.title("🛡️ CIO Kriz Yönetimi Oyunu – Senaryo Editörü")
    st.markdown(
        "Bu arayüzle `scenarios_child.json` ve `scenarios_parent.json` dosyalarındaki senaryoları güvenle düzenleyebilirsiniz."
    )

    # Kenar çubuğu: hangi senaryo seti?
    st.sidebar.title("Senaryo Seti")
    selected_set = st.sidebar.radio(
        "Düzenlenecek sürüm:",
        options=list(SCENARIO_FILES.keys()),
        index=0,
    )
    current_file = SCENARIO_FILES[selected_set]

    # İlk çalışma için session_state ayarları
    if "mode" not in st.session_state:
        st.session_state.mode = "edit"
    if "auto_save" not in st.session_state:
        st.session_state.auto_save = True

    # Dosya yükle
    scenarios_data = load_data(current_file)
    if not isinstance(scenarios_data, dict):
        scenarios_data = {}

    # Kenar çubuğu: işlemler
    st.sidebar.markdown("---")
    st.sidebar.title("İşlemler")
    if st.sidebar.button("📝 Senaryoları Düzenle/Görüntüle", use_container_width=True):
        st.session_state.mode = "edit"
        st.rerun()
    if st.sidebar.button("➕ Yeni Senaryo Ekle", use_container_width=True):
        st.session_state.mode = "add"
        st.rerun()
    if st.sidebar.button("🗑️ Senaryo Sil", use_container_width=True):
        st.session_state.mode = "delete"
        st.rerun()

    # Otomatik / manuel kaydet
    st.sidebar.markdown("---")
    st.sidebar.title("Kaydetme Modu")
    st.session_state.auto_save = st.sidebar.checkbox(
        "Otomatik kaydet (önerilir)",
        value=st.session_state.auto_save,
        help="Düzenleme sırasında her değişiklikte dosyaya yazılır.",
    )
    st.sidebar.caption(
        "Otomatik kayıtta değişiklikler anında diske yazılır. Manuel modda 'Tüm Değişiklikleri Kaydet' butonunu kullanın."
    )
    if st.sidebar.button("Tüm Değişiklikleri Kaydet", type="primary", use_container_width=True):
        ok = write_through_verify(current_file, scenarios_data)
        if ok:
            st.sidebar.success("Tüm veriler başarıyla kaydedildi!")
        else:
            st.sidebar.error("Kaydetme doğrulaması başarısız!")
        st.rerun()

    # Backup / restore
    backup_and_restore_ui(selected_set_key=selected_set.replace(" ", "_"), current_file=current_file)

    # Tanılama
    with st.expander("🧪 Dosya Tanılama", expanded=False):
        st.caption(f"Senaryo dosyası → {current_file.resolve()}")
        st.write(f"Var mı? **{current_file.exists()}**")
        if current_file.exists():
            st.write(f"Boyut: {current_file.stat().st_size} bayt")
            st.write(f"Son değişiklik: {datetime.datetime.fromtimestamp(current_file.stat().st_mtime)}")
            if st.button("📄 Dosyayı Ham JSON Olarak Göster"):
                st.json(load_data(current_file))

    # Ana içerik
    if st.session_state.mode == "add":
        add_scenario_ui(scenarios_data, current_file)
    elif st.session_state.mode == "delete":
        delete_scenario_ui(scenarios_data, current_file)
    else:
        scenarios_data = edit_scenarios_ui(scenarios_data, current_file)

    # Otomatik kaydet
    if st.session_state.mode == "edit" and st.session_state.auto_save:
        disk_data = load_data(current_file)
        if not isinstance(disk_data, dict):
            disk_data = {}
        changed = disk_data != scenarios_data
        if changed:
            ok = write_through_verify(current_file, scenarios_data)
            if ok:
                st.sidebar.success(
                    "Otomatik kaydedildi " + datetime.datetime.now().strftime("%H:%M:%S")
                )
            else:
                st.sidebar.error("Otomatik kaydetme doğrulaması başarısız. Dosya izinlerini kontrol edin.")


if __name__ == "__main__":
    main()
