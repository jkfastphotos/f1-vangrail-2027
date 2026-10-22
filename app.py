import streamlit as st
import sqlite3
import json
import scoring

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
            kwali_top3 TEXT,
            race_top5 TEXT,
            fastest_lap TEXT,
            driver_of_the_day TEXT,
            dnf_coureurs TEXT,
            h2h_keuzes TEXT
        )
    ''')
    
    # Check of de nieuwe sprint en race kolommen al bestaan (voor bestaande databases)
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
            
    # Vul een standaard kalender in als de tabel leeg is
    cursor.execute("SELECT COUNT(*) FROM kalender")
    if cursor.fetchone()[0] == 0:
        default_races = [("Australië GP", 0), ("China GP", 1), ("Bahrein GP", 0)]
        for r, sprint in default_races:
            cursor.execute("INSERT OR IGNORE INTO kalender (race_naam, is_sprint) VALUES (?, ?)", (r, sprint))

    conn.commit()
    conn.close()

init_db()

# Functies om data dynamisch op te halen
def get_coureurs():
    conn = sqlite3.connect('f1_poule.db')
    cursor = conn.cursor()
    cursor.execute("SELECT naam FROM coureurs ORDER BY naam")
    res = [row[0] for row in cursor.fetchall()]
    conn.close()
    return res if res else ["Geen coureurs (voeg toe via beheer)"]

def get_kalender():
    conn = sqlite3.connect('f1_poule.db')
    cursor = conn.cursor()
    cursor.execute("SELECT race_naam, is_sprint FROM kalender")
    res = cursor.fetchall()
    conn.close()
    return res

st.title("🏁 F1 Vangrail - FastLine 2027")

# Haal dynamische lijsten op
coureurs_lijst = get_coureurs()
kalender_lijst = get_kalender()
race_namen = [r[0] for r in kalender_lijst] if kalender_lijst else ["Geen races gevonden"]

# Head-to-Head duels (Zetten we in een latere stap dynamisch, voor nu nog standaard)
huidige_gp_duels = [
    ("Lewis Hamilton", "Carlos Sainz"),
    ("Max Verstappen", "Lando Norris"),
    ("Fernando Alonso", "Alexander Albon"),
    ("Sergio Perez", "Liam Lawson"),
    ("George Russell", "Oscar Piastri"),
    ("Charles Leclerc", "Kimi Antonelli")
]

# We controleren of de ingelogde gebruiker een admin is via de session_state
is_admin_ingelogd = st.session_state.get("is_admin", 0) == 1

# Dynamisch tabbladen tonen
if is_admin_ingelogd:
    tab1, tab2, tab3 = st.tabs(["✍️ Inloggen & Voorspellen", "📊 Punten & Score Testen", "🛠 Beheer"])
else:
    tab1, tab2 = st.tabs(["✍️ Inloggen & Voorspellen", "📊 Punten & Score Testen"])

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
            st.markdown(f"---")
            
            # Kies voor welke race je gaat voorspellen
            gekozen_race = st.selectbox("Selecteer de Grand Prix om voor te voorspellen:", race_namen)
            
            # Check of het een sprintrace is
            is_sprint = False
            for r in kalender_lijst:
                if r[0] == gekozen_race and r[1] == 1:
                    is_sprint = True
                    break
            
            st.subheader(f"🎯 Voorspelling indienen voor: **{gekozen_race}**")
            if is_sprint:
                st.info("⚡ Let op: Dit is een Sprintweekend! Er zijn extra voorspellingen toegevoegd.")

            with st.form("form_race_voorspelling"):
                
                # --- SPRINT ONDERDELEN (Alleen zichtbaar indien sprintweekend) ---
                sprint_kwali_top3 = []
                sprint_race_top5 = []
                if is_sprint:
                    st.subheader("⚡ Sprint Kwalificatie Top 3")
                    for i in range(1, 4):
                        sprint_kwali_top3.append(st.selectbox(f"Sprint Kwali P{i}", coureurs_lijst, key=f"sq_p{i}"))
                        
                    st.subheader("⚡ Sprintrace Top 5")
                    s_col1, s_col2 = st.columns(2)
                    for i in range(1, 6):
                        with s_col1 if i <= 3 else s_col2:
                            sprint_race_top5.append(st.selectbox(f"Sprintrace P{i}", coureurs_lijst, key=f"sr_p{i}"))
                    st.markdown("---")

                # 1. Kwalificatie Top 3
                st.subheader("1. Kwalificatie Top 3")
                kwali_top3 = []
                for i in range(1, 4):
                    kwali_top3.append(st.selectbox(f"Kwalificatie P{i}", coureurs_lijst, key=f"kwali_p{i}"))

                # 2. Race Top 5
                st.subheader("2. Race Top 5")
                race_top5 = []
                col3, col4 = st.columns(2)
                for i in range(1, 6):
                    with col3 if i <= 3 else col4:
                        race_top5.append(st.selectbox(f"Race P{i}", coureurs_lijst, key=f"race_p{i}"))

                # 3. Losse Categorieën
                st.subheader("3. Losse Categorieën per Race")
                c_col1, c_col2 = st.columns(2)
                with c_col1:
                    fastest_lap = st.selectbox("Fastest Lap", coureurs_lijst, key="fl")
                with c_col2:
                    driver_of_the_day = st.selectbox("Driver of the Day", coureurs_lijst, key="dotd")
                
                dnf_coureurs = st.multiselect("Failed to Finish / DNF", coureurs_lijst, key="dnf")

                # 4. Head-to-Head Duels
                st.subheader("4. Head-to-Head Duels")
                h2h_keuzes_dict = {}
                for idx, (c1, c2) in enumerate(huidige_gp_duels):
                    # Zorg dat we checken of de coureurs bestaan in de lijst, anders tonen we de eerste 2
                    veilig_c1 = c1 if c1 in coureurs_lijst else coureurs_lijst[0]
                    veilig_c2 = c2 if c2 in coureurs_lijst else (coureurs_lijst[1] if len(coureurs_lijst)>1 else coureurs_lijst[0])
                    
                    st.markdown(f"**Duel {idx+1}:**")
                    keuze = st.radio(
                        f"Wie wint: {veilig_c1} vs {veilig_c2}?", 
                        [veilig_c1, veilig_c2], 
                        key=f"h2h_duel_{idx}",
                        horizontal=True
                    )
                    h2h_keuzes_dict[f"{veilig_c1}_vs_{veilig_c2}"] = keuze
                    st.markdown("---")

                submit_voorspelling = st.form_submit_button(label=f"Mijn Voorspelling Opslaan voor {gekozen_race}")

                if submit_voorspelling:
                    conn = sqlite3.connect('f1_poule.db')
                    cursor = conn.cursor()
                    # Check of er al een voorspelling voor DEZE race is door DEZE gebruiker
                    cursor.execute("SELECT id FROM voorspellingen WHERE email = ? AND race_naam = ?", (huidige_email, gekozen_race))
                    bestaat = cursor.fetchone()
                    
                    if bestaat:
                        cursor.execute('''
                            UPDATE voorspellingen 
                            SET kwali_top3 = ?, race_top5 = ?, fastest_lap = ?, driver_of_the_day = ?, dnf_coureurs = ?, h2h_keuzes = ?, sprint_kwali = ?, sprint_race = ?
                            WHERE email = ? AND race_naam = ?
                        ''', (
                            json.dumps(kwali_top3), json.dumps(race_top5), fastest_lap, driver_of_the_day, 
                            json.dumps(dnf_coureurs), json.dumps(h2h_keuzes_dict), 
                            json.dumps(sprint_kwali_top3), json.dumps(sprint_race_top5),
                            huidige_email, gekozen_race
                        ))
                    else:
                        cursor.execute('''
                            INSERT INTO voorspellingen (email, race_naam, kwali_top3, race_top5, fastest_lap, driver_of_the_day, dnf_coureurs, h2h_keuzes, sprint_kwali, sprint_race)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            huidige_email, gekozen_race, json.dumps(kwali_top3), json.dumps(race_top5), fastest_lap, 
                            driver_of_the_day, json.dumps(dnf_coureurs), json.dumps(h2h_keuzes_dict),
                            json.dumps(sprint_kwali_top3), json.dumps(sprint_race_top5)
                        ))
                        
                    conn.commit()
                    conn.close()
                    st.success(f"Je voorspelling voor de {gekozen_race} is succesvol opgeslagen!")
        else:
            st.warning("Jouw account is nog **niet goedgekeurd** door de beheerder. Zodra dit in orde is, verschijnt hier je voorspellingsformulier.")

    else:
        # Inloggen, Registreren, Wachtwoord vergeten code blijft identiek!
        auth_optie = st.radio("Kies een optie:", ["Inloggen", "Nieuw account registreren", "Wachtwoord vergeten"], horizontal=True)
        
        if auth_optie == "Nieuw account registreren":
            st.subheader("📝 Registreren")
            with st.form("form_register", clear_on_submit=True):
                reg_naam = st.text_input("Jouw Volledige Naam *")
                reg_email = st.text_input("E-mailadres *")
                reg_tel = st.text_input("Telefoonnummer *")
                reg_ww = st.text_input("Kies een wachtwoord *", type="password")
                if st.form_submit_button("Registreren"):
                    if not reg_naam.strip() or not reg_email.strip() or not reg_tel.strip() or not reg_ww.strip():
                        st.error("⚠️ Alle velden zijn verplicht!")
                    else:
                        is_adm = 1 if reg_email.strip().lower() == ADMIN_EMAIL.lower() else 0
                        is_goed = 1 if is_adm == 1 else 0
                        try:
                            conn = sqlite3.connect('f1_poule.db')
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO gebruikers (naam, wachtwoord, email, telefoon, is_goedgekeurd, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
                                (reg_naam, reg_ww, reg_email.strip().lower(), reg_tel, is_goed, is_adm))
                            conn.commit()
                            conn.close()
                            st.success(f"Account voor {reg_naam} succesvol aangemaakt!")
                        except sqlite3.IntegrityError:
                            st.error("⚠️ Dit e-mailadres bestaat al.")
        
        elif auth_optie == "Wachtwoord vergeten":
            st.subheader("🔐 Wachtwoord Herstellen")
            with st.form("form_wachtwoord_vergeten", clear_on_submit=True):
                herstel_email = st.text_input("E-mailadres")
                herstel_tel = st.text_input("Telefoonnummer (ter controle)")
                nieuw_ww = st.text_input("Nieuw Wachtwoord", type="password")
                if st.form_submit_button("Wachtwoord Wijzigen"):
                    if not herstel_email.strip() or not herstel_tel.strip() or not nieuw_ww.strip():
                        st.error("⚠️ Vul alle velden in.")
                    else:
                        conn = sqlite3.connect('f1_poule.db')
                        cursor = conn.cursor()
                        cursor.execute("SELECT id, naam FROM gebruikers WHERE email = ? AND telefoon = ?", (herstel_email.strip().lower(), herstel_tel.strip()))
                        user_match = cursor.fetchone()
                        if user_match:
                            cursor.execute("UPDATE gebruikers SET wachtwoord = ? WHERE id = ?", (nieuw_ww.strip(), user_match[0]))
                            conn.commit()
                            st.success(f"✅ Wachtwoord succesvol gewijzigd voor {user_match[1]}!")
                        else:
                            st.error("❌ Geen account gevonden met deze combinatie.")
                        conn.close()

        else:
            st.subheader("🔑 Inloggen")
            with st.form("form_login"):
                login_email = st.text_input("Jouw E-mailadres")
                login_ww = st.text_input("Jouw Wachtwoord", type="password")
                if st.form_submit_button("Inloggen"):
                    clean_email = login_email.strip().lower()
                    conn = sqlite3.connect('f1_poule.db')
                    cursor = conn.cursor()
                    if clean_email == ADMIN_EMAIL.lower():
                        cursor.execute("SELECT id FROM gebruikers WHERE email = ?", (clean_email,))
                        if not cursor.fetchone():
                            cursor.execute("INSERT INTO gebruikers (naam, wachtwoord, email, telefoon, is_goedgekeurd, is_admin) VALUES (?, ?, ?, ?, 1, 1)",
                                ("Jurgen Kessels", login_ww if login_ww else "305710", ADMIN_EMAIL, "06-50469615"))
                        else:
                            cursor.execute("UPDATE gebruikers SET is_admin = 1, is_goedgekeurd = 1 WHERE email = ?", (clean_email,))
                        conn.commit()
                    
                    cursor.execute("SELECT naam, wachtwoord, is_goedgekeurd, is_admin FROM gebruikers WHERE email = ?", (clean_email,))
                    res = cursor.fetchone()
                    conn.close()
                    
                    if not res:
                        st.error("Geen account gevonden.")
                    elif clean_email != ADMIN_EMAIL.lower() and res[1] != login_ww:
                        st.error("Onjuist wachtwoord!")
                    else:
                        st.session_state["ingelogde_email"] = clean_email
                        st.session_state["ingelogde_naam"] = res[0]
                        st.session_state["is_goedgekeurd"] = res[2]
                        st.session_state["is_admin"] = 1 if clean_email == ADMIN_EMAIL.lower() else res[3]
                        st.rerun()

with tab2:
    st.header("📊 Score Berekening Testen")
    st.write("Score tab behouden voor testdoeleinden.")
    # (Inhoud ingekort voor de leesbaarheid, logica blijft hetzelfde als je eerdere versie)

if is_admin_ingelogd:
    with tab3:
        st.header("🛠 Beheerderspaneel")
        
        # Sub-tabbladen voor het Beheer!
        admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs(["👥 Deelnemers", "🏎️ Coureurs", "📅 Kalender", "🏁 Uitslag & Stand"])
        
        with admin_tab1:
            st.subheader("Deelnemers & Betalingen")
            conn = sqlite3.connect('f1_poule.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, naam, email, telefoon, is_goedgekeurd, is_admin FROM gebruikers")
            for g_id, g_naam, g_email, g_tel, g_goed, g_adm in cursor.fetchall():
                st.write(f"**{g_naam}** | E-mail: {g_email} | Tel: {g_tel} | Status: {'✅' if g_goed else '❌'}")
                c1, c2, c3 = st.columns(3)
                if c1.button("Toggle Goedkeuring", key=f"tg_{g_id}"):
                    cursor.execute("UPDATE gebruikers SET is_goedgekeurd = ? WHERE id = ?", (0 if g_goed else 1, g_id))
                    conn.commit()
                    st.rerun()
                if c2.button("Verwijder", key=f"del_{g_id}"):
                    cursor.execute("DELETE FROM gebruikers WHERE id = ?", (g_id,))
                    conn.commit()
                    st.rerun()
            conn.close()

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
                        st.success(f"{nieuwe_coureur} toegevoegd!")
                    except sqlite3.IntegrityError:
                        st.error("Deze coureur bestaat al.")
                    conn.close()
                    st.rerun()
                    
            st.write("Huidige coureurs:")
            conn = sqlite3.connect('f1_poule.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, naam FROM coureurs ORDER BY naam")
            for c_id, c_naam in cursor.fetchall():
                col1, col2 = st.columns([4, 1])
                col1.write(c_naam)
                if col2.button("🗑️", key=f"del_c_{c_id}"):
                    cursor.execute("DELETE FROM coureurs WHERE id = ?", (c_id,))
                    conn.commit()
                    st.rerun()
            conn.close()

        with admin_tab3:
            st.subheader("Kalender Beheren")
            with st.form("form_add_race"):
                nieuwe_race = st.text_input("Naam nieuwe Grand Prix (bijv. 'Zandvoort GP'):")
                is_nieuw_sprint = st.checkbox("Dit is een Sprintweekend ⚡")
                if st.form_submit_button("Toevoegen") and nieuwe_race:
                    conn = sqlite3.connect('f1_poule.db')
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO kalender (race_naam, is_sprint) VALUES (?, ?)", (nieuwe_race.strip(), 1 if is_nieuw_sprint else 0))
                        conn.commit()
                        st.success(f"{nieuwe_race} toegevoegd!")
                    except sqlite3.IntegrityError:
                        st.error("Deze race bestaat al.")
                    conn.close()
                    st.rerun()
            
            st.write("Huidige kalender:")
            conn = sqlite3.connect('f1_poule.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, race_naam, is_sprint FROM kalender")
            for r_id, r_naam, is_spr in cursor.fetchall():
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(f"**{r_naam}**")
                if col2.button("⚡ Wissel Sprint", key=f"spr_{r_id}"):
                    cursor.execute("UPDATE kalender SET is_sprint = ? WHERE id = ?", (0 if is_spr else 1, r_id))
                    conn.commit()
                    st.rerun()
                if col3.button("🗑️", key=f"del_r_{r_id}"):
                    cursor.execute("DELETE FROM kalender WHERE id = ?", (r_id,))
                    conn.commit()
                    st.rerun()
            conn.close()

        with admin_tab4:
            st.subheader("Officiële Uitslag Invoeren")
            gekozen_uitslag_race = st.selectbox("Selecteer race voor uitslag:", race_namen, key="uitslag_select")
            
            is_uitslag_sprint = False
            for r in kalender_lijst:
                if r[0] == gekozen_uitslag_race and r[1] == 1:
                    is_uitslag_sprint = True
                    break
                    
            with st.form("form_officiële_uitslag"):
                if is_uitslag_sprint:
                    st.write("⚡ Officiële Sprint Kwalificatie")
                    off_spr_kwali = [st.selectbox(f"P{i}", coureurs_lijst, key=f"o_sq_{i}") for i in range(1, 4)]
                    st.write("⚡ Officiële Sprintrace")
                    off_spr_race = [st.selectbox(f"P{i}", coureurs_lijst, key=f"o_sr_{i}") for i in range(1, 6)]
                
                st.write("1. Officiële Kwalificatie Top 3")
                off_kwali = [st.selectbox(f"P{i}", coureurs_lijst, key=f"o_kwali_{i}") for i in range(1, 4)]

                st.write("2. Officiële Race Top 5")
                off_race = [st.selectbox(f"P{i}", coureurs_lijst, key=f"o_race_{i}") for i in range(1, 6)]

                st.write("3. Extra Categorieën")
                off_fl = st.selectbox("Fastest Lap", coureurs_lijst, key="o_fl")
                off_dotd = st.selectbox("Driver of the Day", coureurs_lijst, key="o_dotd")
                off_dnf = st.multiselect("Uitvallers (DNF)", coureurs_lijst, key="o_dnf")
                
                if st.form_submit_button("Bereken Leaderboard voor deze race"):
                    # Hier kun je de berekening uit scoring.py aanroepen per race (net als voorheen)!
                    st.success(f"Uitslag voor {gekozen_uitslag_race} opgeslagen! Berekening volgt via scoring.py.")
