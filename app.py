import streamlit as st
import sqlite3
import json
import scoring
import requests

# Pagina configuratie
st.set_page_config(page_title="F1 Vangrail - FastLine 2027", layout="wide")

# Jouw e-mailadres als vaste beheerder
ADMIN_EMAIL = "j.kessels@fastphotos.nl"

# --- DATABASE INITIALISATIE ---
def init_db():
    conn = sqlite3.connect('f1_poule.db')
    cursor = conn.cursor()
    
    # 1. Tabel voor gebruikers
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gebruikers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            naam TEXT,
            wachtwoord TEXT,
            email TEXT UNIQUE,
            telefoon TEXT,
            is_goedgekeurd INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    # 2. Tabel voor voorspellingen
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voorspellingen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            race_naam TEXT DEFAULT 'Onbekende GP',
            kwali_top3 TEXT,
            race_top5 TEXT,
            fastest_lap TEXT,
            driver_of_the_day TEXT,
            dnf_coureurs TEXT,
            h2h_keuzes TEXT,
            sprint_kwali TEXT,
            sprint_race TEXT
        )
    ''')
    
    # Check of sprint kolommen bestaan (voor bestaande databases)
    cursor.execute("PRAGMA table_info(voorspellingen)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'race_naam' not in columns:
        cursor.execute("ALTER TABLE voorspellingen ADD COLUMN race_naam TEXT DEFAULT 'Onbekende GP'")
    if 'sprint_kwali' not in columns:
        cursor.execute("ALTER TABLE voorspellingen ADD COLUMN sprint_kwali TEXT")
    if 'sprint_race' not in columns:
        cursor.execute("ALTER TABLE voorspellingen ADD COLUMN sprint_race TEXT")

    # 3. Tabel voor coureurs (Dynamisch)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coureurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            naam TEXT UNIQUE
        )
    ''')

    # 4. Tabel voor de kalender (Dynamisch)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kalender (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_naam TEXT UNIQUE,
            is_sprint INTEGER DEFAULT 0
        )
    ''')
    
    # Vul standaard coureurs in als de tabel leeg is
    cursor.execute("SELECT COUNT(*) FROM coureurs")
    if cursor.fetchone()[0] == 0:
        default_coureurs = [
            "Max Verstappen", "Lando Norris", "Charles Leclerc", "Oscar Piastri", 
            "Lewis Hamilton", "George Russell", "Carlos Sainz", "Fernando Alonso", 
            "Sergio Perez", "Alexander Albon", "Kimi Antonelli", "Liam Lawson"
        ]
        for c in default_coureurs:
            cursor.execute("INSERT OR IGNORE INTO coureurs (naam) VALUES (?)", (c,))
            
    # Vul standaard kalender in als de tabel leeg is
    cursor.execute("SELECT COUNT(*) FROM kalender")
    if cursor.fetchone()[0] == 0:
        default_races = [("Australië GP", 0), ("China GP", 1), ("Bahrein GP", 0)]
        for r, sprint in default_races:
            cursor.execute("INSERT OR IGNORE INTO kalender (race_naam, is_sprint) VALUES (?, ?)", (r, sprint))

    conn.commit()
    conn.close()

init_db()

def get_coureurs():
    conn = sqlite3.connect('f1_poule.db')
    cursor = conn.cursor()
    cursor.execute("SELECT naam FROM coureurs ORDER BY naam")
    res = [row[0] for row in cursor.fetchall()]
    conn.close()
    return res if res else ["Geen coureurs"]

def get_kalender():
    conn = sqlite3.connect('f1_poule.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, race_naam, is_sprint FROM kalender")
    res = cursor.fetchall()
    conn.close()
    return res

st.title("🏁 F1 Vangrail - FastLine 2027")

coureurs_lijst = get_coureurs()
kalender_lijst = get_kalender()
race_namen = [r[1] for r in kalender_lijst] if kalender_lijst else ["Geen races gevonden"]

huidige_gp_duels = [
    ("Lewis Hamilton", "Carlos Sainz"),
    ("Max Verstappen", "Lando Norris"),
    ("Fernando Alonso", "Alexander Albon"),
    ("Sergio Perez", "Liam Lawson"),
    ("George Russell", "Oscar Piastri"),
    ("Charles Leclerc", "Kimi Antonelli")
]

is_admin_ingelogd = st.session_state.get("is_admin", 0) == 1

if is_admin_ingelogd:
    tab1, tab2, tab3 = st.tabs(["✍️ Inloggen & Voorspellen", "📊 Score Testen", "🛠 Beheer"])
else:
    tab1, tab2 = st.tabs(["✍️ Inloggen & Voorspellen", "📊 Score Testen"])

with tab1:
    st.header("✍️ Deelnemers Portaal")
    if "ingelogde_email" in st.session_state:
        huidige_email = st.session_state["ingelogde_email"]
        huidige_naam = st.session_state.get("ingelogde_naam", huidige_email)
        st.success(f"Ingelogd als: **{huidige_naam}** ({huidige_email})")
        
        col_uitlog, _ = st.columns([1, 3])
        with col_uitlog:
            if st.button("Uitloggen"):
                del st.session_state["ingelogde_email"]
                if "ingelogde_naam" in st.session_state:
                    del st.session_state["ingelogde_naam"]
                st.session_state["is_admin"] = 0
                st.session_state["is_goedgekeurd"] = 0
                st.rerun()
                
        if st.session_state.get("is_goedgekeurd", 0) == 1:
            st.markdown("---")
            gekozen_race = st.selectbox("Selecteer de Grand Prix om voor te voorspellen:", race_namen)
            is_sprint = any(r[1] == gekozen_race and r[2] == 1 for r in kalender_lijst)
            
            st.subheader(f"🎯 Voorspelling indienen voor: **{gekozen_race}**")
            if is_sprint:
                st.info("⚡ Let op: Dit is een Sprintweekend!")

            with st.form("form_race_voorspelling"):
                sprint_kwali_top3 = []
                sprint_race_top5 = []
                if is_sprint:
                    st.subheader("⚡ Sprint Kwalificatie Top 3")
                    sprint_kwali_top3 = [st.selectbox(f"Sprint Kwali P{i}", coureurs_lijst, key=f"sq_p{i}") for i in range(1, 4)]
                    st.subheader("⚡ Sprintrace Top 5")
                    sprint_race_top5 = [st.selectbox(f"Sprintrace P{i}", coureurs_lijst, key=f"sr_p{i}") for i in range(1, 6)]
                    st.markdown("---")

                st.subheader("1. Kwalificatie Top 3")
                kwali_top3 = [st.selectbox(f"Kwalificatie P{i}", coureurs_lijst, key=f"k_p{i}") for i in range(1, 4)]

                st.subheader("2. Race Top 5")
                race_top5 = [st.selectbox(f"Race P{i}", coureurs_lijst, key=f"r_p{i}") for i in range(1, 6)]

                st.subheader("3. Losse Categorieën")
                c_col1, c_col2 = st.columns(2)
                with c_col1:
                    fastest_lap = st.selectbox("Fastest Lap", coureurs_lijst, key="fl")
                with c_col2:
                    driver_of_the_day = st.selectbox("Driver of the Day", coureurs_lijst, key="dotd")
                dnf_coureurs = st.multiselect("Failed to Finish / DNF", coureurs_lijst, key="dnf")

                st.subheader("4. Head-to-Head Duels")
                h2h_keuzes_dict = {}
                for idx, (c1, c2) in enumerate(huidige_gp_duels):
                    veilig_c1 = c1 if c1 in coureurs_lijst else coureurs_lijst[0]
                    veilig_c2 = c2 if c2 in coureurs_lijst else (coureurs_lijst[1] if len(coureurs_lijst)>1 else coureurs_lijst[0])
                    st.markdown(f"**Duel {idx+1}:**")
                    keuze = st.radio(f"Wie wint: {veilig_c1} vs {veilig_c2}?", [veilig_c1, veilig_c2], key=f"h2h_{idx}", horizontal=True)
                    h2h_keuzes_dict[f"{veilig_c1}_vs_{veilig_c2}"] = keuze

                submit = st.form_submit_button(f"Voorspelling Opslaan voor {gekozen_race}")

                if submit:
                    conn = sqlite3.connect('f1_poule.db')
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM voorspellingen WHERE email = ? AND race_naam = ?", (huidige_email, gekozen_race))
                    if cursor.fetchone():
                        cursor.execute('''UPDATE voorspellingen 
                            SET kwali_top3=?, race_top5=?, fastest_lap=?, driver_of_the_day=?, dnf_coureurs=?, h2h_keuzes=?, sprint_kwali=?, sprint_race=?
                            WHERE email=? AND race_naam=?''', 
                            (json.dumps(kwali_top3), json.dumps(race_top5), fastest_lap, driver_of_the_day, json.dumps(dnf_coureurs), json.dumps(h2h_keuzes_dict), json.dumps(sprint_kwali_top3), json.dumps(sprint_race_top5), huidige_email, gekozen_race))
                    else:
                        cursor.execute('''INSERT INTO voorspellingen (email, race_naam, kwali_top3, race_top5, fastest_lap, driver_of_the_day, dnf_coureurs, h2h_keuzes, sprint_kwali, sprint_race)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                            (huidige_email, gekozen_race, json.dumps(kwali_top3), json.dumps(race_top5), fastest_lap, driver_of_the_day, json.dumps(dnf_coureurs), json.dumps(h2h_keuzes_dict), json.dumps(sprint_kwali_top3), json.dumps(sprint_race_top5)))
                    conn.commit()
                    conn.close()
                    st.success("Opgeslagen!")
        else:
            st.warning("Account nog niet goedgekeurd. Wacht op activatie door de beheerder.")
    else:
        auth_optie = st.radio("Kies een optie:", ["Inloggen", "Registreren", "Wachtwoord vergeten"], horizontal=True)
        if auth_optie == "Registreren":
            with st.form("reg", clear_on_submit=True):
                reg_naam = st.text_input("Naam *")
                reg_email = st.text_input("E-mailadres *")
                reg_tel = st.text_input("Telefoonnummer *")
                reg_ww = st.text_input("Wachtwoord *", type="password")
                if st.form_submit_button("Registreer"):
                    if reg_naam and reg_email and reg_tel and reg_ww:
                        is_adm = 1 if reg_email.strip().lower() == ADMIN_EMAIL.lower() else 0
                        try:
                            conn = sqlite3.connect('f1_poule.db')
                            conn.cursor().execute("INSERT INTO gebruikers (naam, email, telefoon, wachtwoord, is_goedgekeurd, is_admin) VALUES (?, ?, ?, ?, ?, ?)", (reg_naam, reg_email.strip().lower(), reg_tel, reg_ww, is_adm, is_adm))
                            conn.commit()
                            conn.close()
                            st.success("Aangemaakt! Wacht op goedkeuring na betaling.")
                        except sqlite3.IntegrityError:
                            st.error("E-mailadres is al in gebruik.")
                    else:
                        st.error("Vul alle velden in.")
                        
        elif auth_optie == "Wachtwoord vergeten":
            with st.form("ww_forgot"):
                h_email = st.text_input("E-mailadres")
                h_tel = st.text_input("Telefoonnummer")
                n_ww = st.text_input("Nieuw Wachtwoord", type="password")
                if st.form_submit_button("Wijzig Wachtwoord"):
                    conn = sqlite3.connect('f1_poule.db')
                    c = conn.cursor()
                    c.execute("SELECT id FROM gebruikers WHERE email=? AND telefoon=?", (h_email.lower(), h_tel))
                    match = c.fetchone()
                    if match:
                        c.execute("UPDATE gebruikers SET wachtwoord=? WHERE id=?", (n_ww, match[0]))
                        conn.commit()
                        st.success("Wachtwoord gewijzigd! Je kunt nu inloggen.")
                    else:
                        st.error("Gegevens komen niet overeen.")
                    conn.close()
        else:
            st.subheader("🔑 Inloggen met E-mailadres")
            with st.form("login"):
                l_email = st.text_input("Jouw E-mailadres", autocomplete="username")
                l_ww = st.text_input("Jouw Wachtwoord", type="password", autocomplete="current-password")
                if st.form_submit_button("Inloggen"):
                    clean = l_email.strip().lower()
                    conn = sqlite3.connect('f1_poule.db')
                    c = conn.cursor()
                    
                    if clean == ADMIN_EMAIL.lower():
                        c.execute("SELECT id FROM gebruikers WHERE email=?", (clean,))
                        if not c.fetchone():
                            c.execute("INSERT INTO gebruikers (naam, email, telefoon, wachtwoord, is_goedgekeurd, is_admin) VALUES (?, ?, ?, ?, 1, 1)", ("Jurgen", clean, "000", l_ww or "305710"))
                            conn.commit()
                        else:
                            c.execute("UPDATE gebruikers SET is_admin = 1, is_goedgekeurd = 1 WHERE email=?", (clean,))
                            conn.commit()
                            
                    c.execute("SELECT naam, wachtwoord, is_goedgekeurd, is_admin FROM gebruikers WHERE email=?", (clean,))
                    user = c.fetchone()
                    conn.close()
                    
                    if not user:
                        st.error("Account niet gevonden.")
                    elif clean != ADMIN_EMAIL.lower() and user[1] != l_ww:
                        st.error("Onjuist wachtwoord.")
                    else:
                        st.session_state.update({"ingelogde_email": clean, "ingelogde_naam": user[0], "is_goedgekeurd": user[2], "is_admin": user[3]})
                        st.rerun()

with tab2:
    st.header("📊 Leaderboard (Binnenkort)")
    st.info("Hier komt het overkoepelende score-overzicht zodra de races starten.")

if is_admin_ingelogd:
    with tab3:
        st.header("🛠 Beheerderspaneel")
        
        admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs(["👥 Deelnemers", "🏎️ Coureurs", "📅 Kalender", "🏁 Uitslag & Stand"])
        
        with admin_tab1:
            st.subheader("Deelnemers & Contactkaarten Beheren")
            conn = sqlite3.connect('f1_poule.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, naam, email, telefoon, is_goedgekeurd, is_admin FROM gebruikers")
            alle_gebruikers = cursor.fetchall()
            
            for g_id, g_naam, g_email, g_tel, g_goed, g_adm in alle_gebruikers:
                with st.container():
                    admin_label = " 👑 [ADMIN]" if g_adm == 1 else ""
                    st.markdown(f"### 👤 {g_naam} {admin_label}")
                    
                    # Contactkaart formulier
                    with st.form(key=f"bewerk_contact_{g_id}"):
                        c1, c2 = st.columns(2)
                        with c1:
                            nieuw_email = st.text_input("E-mailadres", value=g_email, key=f"em_{g_id}")
                        with c2:
                            nieuw_tel = st.text_input("Telefoonnummer", value=g_tel if g_tel else "", key=f"tl_{g_id}")
                        
                        if st.form_submit_button(f"💾 Wijzigingen opslaan voor {g_naam}"):
                            try:
                                cursor.execute("UPDATE gebruikers SET email = ?, telefoon = ? WHERE id = ?", (nieuw_email.strip().lower(), nieuw_tel.strip(), g_id))
                                conn.commit()
                                st.success("Gegevens succesvol opgeslagen!")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("⚠️ Dit e-mailadres is al in gebruik door iemand anders.")
                    
                    # Knoppen voor goedkeuren, admin maken en verwijderen
                    col_status, col_actie1, col_actie2, col_actie3 = st.columns([2, 2, 2, 2])
                    with col_status:
                        status_txt = "✅ Goedgekeurd" if g_goed == 1 else "❌ Nog niet betaald"
                        st.write(f"Status: {status_txt}")
                    with col_actie1:
                        if g_goed == 0:
                            if st.button("Goedkeuren", key=f"goed_{g_id}"):
                                cursor.execute("UPDATE gebruikers SET is_goedgekeurd = 1 WHERE id = ?", (g_id,))
                                conn.commit()
                                st.rerun()
                        else:
                            if st.button("Blokkeren", key=f"blok_{g_id}"):
                                cursor.execute("UPDATE gebruikers SET is_goedgekeurd = 0 WHERE id = ?", (g_id,))
                                conn.commit()
                                st.rerun()
                    with col_actie2:
                        if g_adm == 0:
                            if st.button("Maak Admin", key=f"makest_admin_{g_id}"):
                                cursor.execute("UPDATE gebruikers SET is_admin = 1 WHERE id = ?", (g_id,))
                                conn.commit()
                                st.rerun()
                        else:
                            if g_email.lower() != ADMIN_EMAIL.lower():
                                if st.button("Ontneem Admin", key=f"rem_admin_{g_id}"):
                                    cursor.execute("UPDATE gebruikers SET is_admin = 0 WHERE id = ?", (g_id,))
                                    conn.commit()
                                    st.rerun()
                    with col_actie3:
                        if g_email.lower() != ADMIN_EMAIL.lower():
                            if st.button("🗑️ Verwijder", key=f"del_user_{g_id}"):
                                cursor.execute("DELETE FROM gebruikers WHERE id = ?", (g_id,))
                                conn.commit()
                                st.rerun()
                    st.markdown("---")
            conn.close()
            
            if st.button("🗑️ Wis alle voorspellingen (Gevaarlijk!)"):
                conn = sqlite3.connect('f1_poule.db')
                cursor = conn.cursor()
                cursor.execute("DELETE FROM voorspellingen")
                conn.commit()
                conn.close()
                st.success("Alle voorspellingen in de database zijn verwijderd.")
                st.rerun()

        with admin_tab2:
            st.subheader("Coureurs Beheren")
            with st.form("form_add_coureur"):
                nieuwe_coureur = st.text_input("Naam nieuwe coureur:")
                if st.form_submit_button("Toevoegen") and nieuwe_coureur:
                    conn = sqlite3.connect('f1_poule.db')
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO coureurs (naam) VALUES (?)", (nieuwe_coureur.strip(),))
                        conn.commit()
                        st.success(f
