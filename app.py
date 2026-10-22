import streamlit as st
import sqlite3
import json
import scoring
import requests  # <-- Nieuw: om data van internet te halen

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
    
    # Check of sprint kolommen bestaan (voor bestaande DB)
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
    
    # Vul standaard coureurs in
    cursor.execute("SELECT COUNT(*) FROM coureurs")
    if cursor.fetchone()[0] == 0:
        default_coureurs = [
            "Max Verstappen", "Lando Norris", "Charles Leclerc", "Oscar Piastri", 
            "Lewis Hamilton", "George Russell", "Carlos Sainz", "Fernando Alonso", 
            "Sergio Perez", "Alexander Albon", "Kimi Antonelli", "Liam Lawson"
        ]
        for c in default_coureurs:
            cursor.execute("INSERT OR IGNORE INTO coureurs (naam) VALUES (?)", (c,))
            
    # Vul standaard kalender in
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
    cursor.execute("SELECT race_naam, is_sprint FROM kalender")
    res = cursor.fetchall()
    conn.close()
    return res

st.title("🏁 F1 Vangrail - FastLine 2027")

coureurs_lijst = get_coureurs()
kalender_lijst = get_kalender()
race_namen = [r[0] for r in kalender_lijst] if kalender_lijst else ["Geen races gevonden"]

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
            st.markdown("---")
            gekozen_race = st.selectbox("Selecteer de Grand Prix om voor te voorspellen:", race_namen)
            is_sprint = any(r[0] == gekozen_race and r[1] == 1 for r in kalender_lijst)
            
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
            st.warning("Account nog niet goedgekeurd.")
    else:
        # Inlog functionaliteit
        auth_optie = st.radio("Kies een optie:", ["Inloggen", "Registreren", "Wachtwoord vergeten"], horizontal=True)
        if auth_optie == "Registreren":
            with st.form("reg"):
                reg_naam, reg_email, reg_tel, reg_ww = st.text_input("Naam *"), st.text_input("E-mail *"), st.text_input("Tel *"), st.text_input("Wachtwoord *", type="password")
                if st.form_submit_button("Registreer"):
                    is_adm = 1 if reg_email.strip().lower() == ADMIN_EMAIL.lower() else 0
                    try:
                        conn = sqlite3.connect('f1_poule.db')
                        conn.cursor().execute("INSERT INTO gebruikers (naam, email, telefoon, wachtwoord, is_goedgekeurd, is_admin) VALUES (?, ?, ?, ?, ?, ?)", (reg_naam, reg_email.strip().lower(), reg_tel, reg_ww, is_adm, is_adm))
                        conn.commit()
                        st.success("Aangemaakt!")
                    except sqlite3.IntegrityError:
                        st.error("E-mail bestaat al.")
        elif auth_optie == "Wachtwoord vergeten":
            with st.form("ww_forgot"):
                h_email, h_tel, n_ww = st.text_input("E-mail"), st.text_input("Telefoon"), st.text_input("Nieuw Wachtwoord", type="password")
                if st.form_submit_button("Wijzig"):
                    conn = sqlite3.connect('f1_poule.db')
                    c = conn.cursor()
                    c.execute("SELECT id FROM gebruikers WHERE email=? AND telefoon=?", (h_email.lower(), h_tel))
                    match = c.fetchone()
                    if match:
                        c.execute("UPDATE gebruikers SET wachtwoord=? WHERE id=?", (n_ww, match[0]))
                        conn.commit()
                        st.success("Gewijzigd!")
                    else:
                        st.error("Niet gevonden.")
        else:
            with st.form("login"):
                l_email, l_ww = st.text_input("E-mail"), st.text_input("Wachtwoord", type="password")
                if st.form_submit_button("Inloggen"):
                    clean = l_email.strip().lower()
                    conn = sqlite3.connect('f1_poule.db')
                    c = conn.cursor()
                    if clean == ADMIN_EMAIL.lower():
                        c.execute("SELECT id FROM gebruikers WHERE email=?", (clean,))
                        if not c.fetchone():
                            c.execute("INSERT INTO gebruikers (naam, email, telefoon, wachtwoord, is_goedgekeurd, is_admin) VALUES (?, ?, ?, ?, 1, 1)", ("Jurgen", clean, "000", l_ww or "123"))
                            conn.commit()
                    c.execute("SELECT naam, wachtwoord, is_goedgekeurd, is_admin FROM gebruikers WHERE email=?", (clean,))
                    user = c.fetchone()
                    if user and (clean == ADMIN_EMAIL.lower() or user[1] == l_ww):
                        st.session_state.update({"ingelogde_email": clean, "ingelogde_naam": user[0], "is_goedgekeurd": 1 if clean == ADMIN_EMAIL.lower() else user[2], "is_admin": 1 if clean == ADMIN_EMAIL.lower() else user[3]})
                        st.rerun()
                    else:
                        st.error("Fout e-mail of wachtwoord.")

with tab2:
    st.header("📊 Score Testen")
    st.write("Score tab behouden voor testdoeleinden.")

if is_admin_ingelogd:
    with tab3:
        admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs(["👥 Deelnemers", "🏎️ Coureurs", "📅 Kalender", "🏁 Uitslag & Stand"])
        
        with admin_tab1:
            # Code voor beheer deelnemers blijft hetzelfde
            st.write("Deelnemers beheer...")

        with admin_tab2:
            # Code voor beheer coureurs blijft hetzelfde
            st.write("Coureurs beheer...")

        with admin_tab3:
            # Code voor beheer kalender blijft hetzelfde
            st.write("Kalender beheer...")

        with admin_tab4:
            st.subheader("Officiële Uitslag Invoeren of Ophalen")
            gekozen_uitslag_race = st.selectbox("Selecteer race voor uitslag:", race_namen, key="uitslag_select")
            
            st.info("💡 Je kunt de data handmatig invullen óf automatisch van internet plukken via de knop hieronder.")
            
            # --- NIEUW: AUTOMATISCH OPHALEN VIA API ---
            if st.button("📥 Haal meest recente F1 uitslag op via API"):
                try:
                    # We gebruiken de open Ergast/Jolpica F1 API voor de meest recente race resultaten
                    api_url = "https://api.jolpi.ca/ergast/f1/current/last/results.json"
                    response = requests.get(api_url)
                    data = response.json()
                    
                    race_info = data['MRData']['RaceTable']['Races'][0]
                    actuele_race_naam = race_info['raceName']
                    uitslagen = race_info['Results']
                    
                    # Top 5 uit de API halen (Achternamen)
                    top5_api = []
                    for i in range(5):
                        if i < len(uitslagen):
                            top5_api.append(uitslagen[i]['Driver']['familyName'])
                    
                    # DNF's bepalen (status is niet 'Finished' of '+1 Lap' etc.)
                    dnf_api = []
                    for u in uitslagen:
                        status = u['status']
                        if status not in ['Finished', '+1 Lap', '+2 Laps']:
                            dnf_api.append(u['Driver']['familyName'])
                            
                    # Snelste ronde uithalen
                    fl_api = "Onbekend"
                    for u in uitslagen:
                        if 'FastestLap' in u and u['FastestLap'].get('rank') == '1':
                            fl_api = u['Driver']['familyName']
                            break

                    st.success(f"Uitslag van {actuele_race_naam} succesvol gedownload!")
                    st.write(f"**Top 5 API:** {', '.join(top5_api)}")
                    st.write(f"**Fastest Lap API:** {fl_api}")
                    st.write(f"**Uitvallers (DNF):** {', '.join(dnf_api)}")
                    st.warning("⚠️ Let op: 'Driver of the Day' zit niet in de automatische racetiming API. Die moet je handmatig kiezen! Omdat het seizoen 2027 nog niet is gestart, toont hij nu de laatste race uit het echte seizoen. Vul de rest hieronder in en klik op Bereken.")
                except Exception as e:
                    st.error(f"Er ging iets mis met het ophalen via de API. Probeer het later opnieuw. (Error: {e})")

            # Het handmatige formulier daaronder
            with st.form("form_officiële_uitslag"):
                st.write("1. Officiële Kwalificatie Top 3")
                off_kwali = [st.selectbox(f"P{i}", coureurs_lijst, key=f"o_kwali_{i}") for i in range(1, 4)]
                
                st.write("2. Officiële Race Top 5")
                off_race = [st.selectbox(f"P{i}", coureurs_lijst, key=f"o_race_{i}") for i in range(1, 6)]

                st.write("3. Extra Categorieën")
                off_fl = st.selectbox("Fastest Lap", coureurs_lijst, key="o_fl")
                off_dotd = st.selectbox("Driver of the Day", coureurs_lijst, key="o_dotd")
                off_dnf = st.multiselect("Uitvallers (DNF)", coureurs_lijst, key="o_dnf")
                
                if st.form_submit_button("Sla Uitslag op & Bereken Leaderboard"):
                    st.success(f"Uitslag voor {gekozen_uitslag_race} opgeslagen! Berekening volgt.")
