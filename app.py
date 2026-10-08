import streamlit as st
import sqlite3
import json
import scoring

# Pagina configuratie
st.set_page_config(page_title="F1 Vangrail - FastLine 2027", page_icon="🏎️", layout="wide")

# Jouw naam als vaste beheerder
ADMIN_NAAM = "Jurgen Kessels" 

# --- DATABASE INITIALISATIE ---
def init_db():
    conn = sqlite3.connect('f1_poule.db', check_same_thread=False)
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
    
    # 2. Tabel voor coureurs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coureurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            naam TEXT UNIQUE,
            team TEXT
        )
    ''')
    
    # 3. Tabel voor races / kalender (met is_sprint vlag)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS races (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            naam TEXT UNIQUE,
            datum TEXT,
            is_sprint INTEGER DEFAULT 0
        )
    ''')
    
    # 4. Tabel voor voorspellingen (per race gekoppeld aan e-mail/gebruiker)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voorspellingen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            race_id INTEGER,
            kwali_top3 TEXT,
            race_top5 TEXT,
            fastest_lap TEXT,
            driver_of_the_day TEXT,
            dnf_coureurs TEXT,
            h2h_keuzes TEXT,
            sprint_kwali TEXT,
            sprint_race TEXT,
            FOREIGN KEY(race_id) REFERENCES races(id)
        )
    ''')
    
    conn.commit()
    
    # Standaard admin aanmaken indien niet aanwezig ('Jurgen Kessels')
    cursor.execute("SELECT * FROM gebruikers WHERE email = 'admin@f1vangrail.nl'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO gebruikers (naam, wachtwoord, email, telefoon, is_goedgekeurd, is_admin)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ADMIN_NAAM, "admin123", "admin@f1vangrail.nl", "0612345678", 1, 1))
        conn.commit()

    # Standaard coureurs vullen als de tabel leeg is
    cursor.execute("SELECT COUNT(*) FROM coureurs")
    if cursor.fetchone()[0] == 0:
        default_coureurs = [
            ("Max Verstappen", "Red Bull Racing"), ("Lando Norris", "McLaren"),
            ("Charles Leclerc", "Ferrari"), ("Lewis Hamilton", "Ferrari"),
            ("Oscar Piastri", "McLaren"), ("George Russell", "Mercedes"),
            ("Kimi Antonelli", "Mercedes"), ("Carlos Sainz", "Williams"),
            ("Fernando Alonso", "Aston Martin"), ("Sergio Perez", "Red Bull Racing"),
            ("Alexander Albon", "Williams"), ("Liam Lawson", "RB")
        ]
        cursor.executemany("INSERT INTO coureurs (naam, team) VALUES (?, ?)", default_coureurs)
        conn.commit()

    # Standaard races vullen als de tabel leeg is
    cursor.execute("SELECT COUNT(*) FROM races")
    if cursor.fetchone()[0] == 0:
        default_races = [
            ("Bahrain GP", "2027-03-21", 0),
            ("Chinese GP", "2027-04-04", 1),  # Voorbeeld Sprintweekend
            ("Monaco GP", "2027-05-23", 0)
        ]
        cursor.executemany("INSERT INTO races (naam, datum, is_sprint) VALUES (?, ?, ?)", default_races)
        conn.commit()
        
    conn.close()

init_db()

# Haal actuele coureurs en races op uit de database
def get_coureurs():
    conn = sqlite3.connect('f1_poule.db')
    cursor = conn.cursor()
    cursor.execute("SELECT naam FROM coureurs")
    lijst = [row[0] for row in cursor.fetchall()]
    conn.close()
    return lijst

def get_races():
    conn = sqlite3.connect('f1_poule.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, naam, datum, is_sprint FROM races")
    lijst = cursor.fetchall()
    conn.close()
    return lijst

coureurs_lijst = get_coureurs()

# Standaard Head-to-Head duels
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
            st.markdown("---")
            
            races_data = get_races()
            if not races_data:
                st.info("Geen races beschikbaar in de kalender.")
            else:
                race_dict = {f"{r[1]} ({r[2]}) {'⚡ [Sprint]' if r[3]==1 else ''}": r[0] for r in races_data}
                selected_race_label = st.selectbox("Selecteer Grand Prix voor voorspelling", list(race_dict.keys()))
                selected_race_id = race_dict[selected_race_label]
                
                # Check of geselecteerde race een sprintweekend is
                conn = sqlite3.connect('f1_poule.db')
                cursor = conn.cursor()
                cursor.execute("SELECT is_sprint FROM races WHERE id = ?", (selected_race_id,))
                is_sprint_race = cursor.fetchone()[0] == 1
                conn.close()

                st.subheader(f"🎯 Voorspelling indienen voor: **{selected_race_label}**")

                with st.form("form_race_voorspelling"):
                    # 1. Kwalificatie Top 3
                    st.subheader("1. Kwalificatie Top 3")
                    kwali_top3 = []
                    for i in range(1, 4):
                        c = st.selectbox(f"Kwalificatie P{i}", coureurs_lijst, key=f"kwali_p{i}")
                        kwali_top3.append(c)

                    # Sprint Weekend Extra's (indien van toepassing)
                    sprint_kwali_list = []
                    sprint_race_list = []
                    if is_sprint_race:
                        st.subheader("⚡ Sprintweekend Extra's")
                        st.write("**Sprint Kwalificatie / Shootout Top 3**")
                        for i in range(1, 4):
                            sc = st.selectbox(f"Sprint Kwali P{i}", coureurs_lijst, key=f"sprint_kwali_p{i}")
                            sprint_kwali_list.append(sc)
                        
                        st.write("**Sprintrace Top 3**")
                        for i in range(1, 4):
                            sr = st.selectbox(f"Sprintrace P{i}", coureurs_lijst, key=f"sprint_race_p{i}")
                            sprint_race_list.append(sr)

                    # 2. Race Top 5
                    st.subheader("2. Race Top 5")
                    race_top5 = []
                    col3, col4 = st.columns(2)
                    for i in range(1, 6):
                        with col3 if i <= 3 else col4:
                            c = st.selectbox(f"Race P{i}", coureurs_lijst, key=f"race_p{i}")
                            race_top5.append(c)

                    # 3. Losse Categorieën
                    st.subheader("3. Losse Categorieën per Race")
                    c_col1, c_col2 = st.columns(2)
                    with c_col1:
                        fastest_lap = st.selectbox("Fastest Lap (20 pt)", coureurs_lijst, key="fl")
                    with c_col2:
                        driver_of_the_day = st.selectbox("Driver of the Day (10 pt)", coureurs_lijst, key="dotd")
                    
                    dnf_coureurs = st.multiselect("Failed to Finish / DNF (15 pt per correcte coureur)", coureurs_lijst, key="dnf")

                    # 4. Head-to-Head Duels
                    st.subheader("4. Head-to-Head Duels")
                    h2h_keuzes_dict = {}
                    for idx, (c1, c2) in enumerate(huidige_gp_duels):
                        st.markdown(f"**Duel {idx+1}:**")
                        keuze = st.radio(
                            f"Wie wint: {c1} vs {c2}?", 
                            [c1, c2], 
                            key=f"h2h_duel_{idx}",
                            horizontal=True
                        )
                        h2h_keuzes_dict[f"{c1}_vs_{c2}"] = keuze
                        st.markdown("---")

                    submit_voorspelling = st.form_submit_button(label="Mijn Voorspelling Opslaan")

                    if submit_voorspelling:
                        conn = sqlite3.connect('f1_poule.db')
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM voorspellingen WHERE email = ? AND race_id = ?", (huidige_email, selected_race_id))
                        bestaat = cursor.fetchone()
                        
                        sprint_q_json = json.dumps(sprint_kwali_list) if is_sprint_race else json.dumps([])
                        sprint_r_json = json.dumps(sprint_race_list) if is_sprint_race else json.dumps([])

                        if bestaat:
                            cursor.execute('''
                                UPDATE voorspellingen 
                                SET kwali_top3 = ?, race_top5 = ?, fastest_lap = ?, driver_of_the_day = ?, 
                                    dnf_coureurs = ?, h2h_keuzes = ?, sprint_kwali = ?, sprint_race = ?
                                WHERE email = ? AND race_id = ?
                            ''', (
                                json.dumps(kwali_top3), json.dumps(race_top5), fastest_lap, driver_of_the_day, 
                                json.dumps(dnf_coureurs), json.dumps(h2h_keuzes_dict), sprint_q_json, sprint_r_json,
                                huidige_email, selected_race_id
                            ))
                        else:
                            cursor.execute('''
                                INSERT INTO voorspellingen (email, race_id, kwali_top3, race_top5, fastest_lap, driver_of_the_day, dnf_coureurs, h2h_keuzes, sprint_kwali, sprint_race)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                huidige_email, selected_race_id, json.dumps(kwali_top3), json.dumps(race_top5), fastest_lap, 
                                driver_of_the_day, json.dumps(dnf_coureurs), json.dumps(h2h_keuzes_dict), sprint_q_json, sprint_r_json
                            ))
                            
                        conn.commit()
                        conn.close()
                        st.success("Je voorspelling is succesvol opgeslagen!")
        else:
            st.warning("Jouw account is nog **niet goedgekeurd** door de beheerder (wacht op betaling). Zodra dit in orde is, verschijnt hier je voorspellingsformulier.")

    else:
        auth_optie = st.radio("Kies een optie:", ["Inloggen", "Nieuw account registreren"], horizontal=True)
        
        if auth_optie == "Nieuw account registreren":
            st.subheader("📝 Registreren voor de Poule")
            st.info(f"Alle velden zijn verplicht! Als je registreert met de naam '{ADMIN_NAAM}', krijg je automatisch beheerdersrechten.")
            
            with st.form("form_register", clear_on_submit=True):
                reg_naam = st.text_input("Jouw Volledige Naam *")
                reg_email = st.text_input("E-mailadres *")
                reg_tel = st.text_input("Telefoonnummer *")
                reg_ww = st.text_input("Kies een wachtwoord *", type="password")
                reg_submit = st.form_submit_button("Registreren")
                
                if reg_submit:
                    if not reg_naam.strip() or not reg_email.strip() or not reg_tel.strip() or not reg_ww.strip():
                        st.error("⚠️ Alle velden zijn verplicht! Vul alsjeblieft alles in.")
                    else:
                        is_adm = 1 if reg_naam.strip().lower() == ADMIN_NAAM.lower() else 0
                        is_goed = 1 if is_adm == 1 else 0
                        
                        try:
                            conn = sqlite3.connect('f1_poule.db')
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO gebruikers (naam, wachtwoord, email, telefoon, is_goedgekeurd, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
                                (reg_naam, reg_ww, reg_email, reg_tel, is_goed, is_adm)
                            )
                            conn.commit()
                            conn.close()
                            st.success(f"Account voor {reg_naam} succesvol aangemaakt! Je kunt nu inloggen met je e-mailadres.")
                        except sqlite3.IntegrityError:
                            st.error("⚠️ Dit e-mailadres is al geregistreerd in het systeem.")
        
        else:
            st.subheader("🔑 Inloggen met E-mailadres")
            with st.form("form_login"):
                login_email = st.text_input("Jouw E-mailadres")
                login_ww = st.text_input("Jouw Wachtwoord", type="password")
                login_submit = st.form_submit_button("Inloggen")
                
                if login_submit:
                    conn = sqlite3.connect('f1_poule.db')
                    cursor = conn.cursor()
                    
                    cursor.execute("SELECT naam, wachtwoord, is_goedgekeurd, is_admin FROM gebruikers WHERE email = ?", (login_email.strip(),))
                    res = cursor.fetchone()
                    conn.close()
                    
                    if not res:
                        st.error("Geen account gevonden met dit e-mailadres.")
                    elif res[1] != login_ww:
                        st.error("Onjuist wachtwoord!")
                    else:
                        st.session_state["ingelogde_email"] = login_email.strip()
                        st.session_state["ingelogde_naam"] = res[0]
                        st.session_state["is_goedgekeurd"] = res[2]
                        
                        if res[0].strip().lower() == ADMIN_NAAM.lower():
                            st.session_state["is_admin"] = 1
                            st.session_state["is_goedgekeurd"] = 1
                        else:
                            st.session_state["is_admin"] = res[3]
                            
                        st.success(f"Welkom terug, {res[0]}!")
                        st.rerun()

with tab2:
    st.header("📊 Score Berekening Testen")
    st.write("Test hier of de puntentelling via `scoring.py` correct werkt op basis van een voorbeeld-uitslag.")

    uitslag_voorbeeld = {
        "kwali_top3": ["Max Verstappen", "Lando Norris", "Charles Leclerc"],
        "race_top5": ["Max Verstappen", "Charles Leclerc", "Lando Norris", "Oscar Piastri", "George Russell"],
        "fastest_lap": "Max Verstappen",
        "driver_of_the_day": "Lando Norris",
        "dnf_coureurs": ["Sergio Perez", "Carlos Sainz"]
    }

    if st.button("Bereken testpunten"):
        kwali_pnt = scoring.bereken_top5_punten(
            ["Max Verstappen", "Lando Norris", "Charles Leclerc"], 
            uitslag_voorbeeld["kwali_top3"]
        )
        race_pnt = scoring.bereken_top5_punten(
            ["Max Verstappen", "Charles Leclerc", "Lando Norris", "Oscar Piastri", "George Russell"], 
            uitslag_voorbeeld["race_top5"]
        )
        extra_pnt = scoring.bereken_race_gebeurtenissen({
            "fastest_lap": "Max Verstappen",
            "driver_of_the_day": "Lando Norris",
            "dnf_coureurs": ["Sergio Perez"],
            "h2h_keuzes": {"Lewis_Hamilton_vs_Carlos_Sainz": "Lewis Hamilton"}
        }, uitslag_voorbeeld)
        
        totaal = kwali_pnt + race_pnt + extra_pnt
        st.success(f"Totale punten berekend: {totaal}")
        st.write(f"- Kwalificatie punten (Top 3): {kwali_pnt}")
        st.write(f"- Race punten: {race_pnt}")
        st.write(f"- Extra categorieën punten: {extra_pnt}")

# Beheerderspaneel
if is_admin_ingelogd:
    with tab3:
        st.header("🛠 Beheerderspaneel")
        st.success("Je bent ingelogd als beheerder.")
        
        beheer_tab1, beheer_tab2, beheer_tab3, beheer_tab4 = st.tabs([
            "👥 Gebruikers & Betalingen", 
            "🏎️ Coureurs Beheer", 
            "📅 Kalender & Sprint Beheer", 
            "🏆 Uitslagen & Leaderboard"
        ])
        
        # 1. Gebruikers & Betalingen
        with beheer_tab1:
            st.subheader("Goedkeuring Betalingen & Accounts")
            conn = sqlite3.connect('f1_poule.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, naam, email, telefoon, is_goedgekeurd, is_admin FROM gebruikers")
            alle_gebruikers = cursor.fetchall()
            conn.close()
            
            for g_id, g_naam, g_email, g_tel, g_goed, g_adm in alle_gebruikers:
                with st.container():
                    admin_label = " 👑 [ADMIN]" if g_adm == 1 else ""
                    st.write(f"**Naam:** {g_naam}{admin_label} | **E-mail:** {g_email} | **Tel:** {g_tel}")
                    col_status, col_actie1, col_actie2 = st.columns([2, 2, 2])
                    with col_status:
                        status_txt = "✅ Goedgekeurd" if g_goed == 1 else "❌ Nog niet betaald"
                        st.write(f"Status: {status_txt}")
                    with col_actie1:
                        conn = sqlite3.connect('f1_poule.db')
                        cursor = conn.cursor()
                        if g_goed == 0:
                            if st.button(f"Goedkeuren", key=f"goed_{g_id}"):
                                cursor.execute("UPDATE gebruikers SET is_goedgekeurd = 1 WHERE id = ?", (g_id,))
                                conn.commit()
                                conn.close()
                                st.rerun()
                        else:
                            if st.button(f"Blokkeren", key=f"blok_{g_id}"):
                                cursor.execute("UPDATE gebruikers SET is_goedgekeurd = 0 WHERE id = ?", (g_id,))
                                conn.commit()
                                conn.close()
                                st.rerun()
                        conn.close()
                    with col_actie2:
                        conn = sqlite3.connect('f1_poule.db')
                        cursor = conn.cursor()
                        if g_adm == 0:
                            if st.button(f"Maak Admin", key=f"makest_admin_{g_id}"):
                                cursor.execute("UPDATE gebruikers SET is_admin = 1 WHERE id = ?", (g_id,))
                                conn.commit()
                                conn.close()
                                st.rerun()
                        else:
                            if g_naam.lower() != ADMIN_NAAM.lower():
                                if st.button(f"Ontneem Admin", key=f"rem_admin_{g_id}"):
                                    cursor.execute("UPDATE gebruikers SET is_admin = 0 WHERE id = ?", (g_id,))
                                    conn.commit()
                                    conn.close()
                                    st.rerun()
                        conn.close()
                    st.markdown("---")

        # 2. Coureurs Beheer
        with beheer_tab2:
            st.subheader("Coureurs Toevoegen of Verwijderen")
            with st.form("add_driver_form"):
                new_driver_name = st.text_input("Naam Coureur")
                new_driver_team = st.text_input("Team")
                add_driver_btn = st.form_submit_button("Coureur Toevoegen")
                if add_driver_btn and new_driver_name and new_driver_team:
                    try:
                        conn = sqlite3.connect('f1_poule.db')
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO coureurs (naam, team) VALUES (?, ?)", (new_driver_name, new_driver_team))
                        conn.commit()
                        conn.close()
                        st.success(f"Coureur {new_driver_name} toegevoegd!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Deze coureur bestaat al.")
            
            st.markdown("---")
            st.subheader("Bestaande Coureurs")
            conn = sqlite3.connect('f1_poule.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, naam, team FROM coureurs")
            all_drivers = cursor.fetchall()
            conn.close()
            
            for d in all_drivers:
                col1, col2 = st.columns([4, 1])
                col1.text(f"{d[1]} ({d[2]})")
                if col2.button("Verwijder", key=f"del_driver_{d[0]}"):
                    conn = sqlite3.connect('f1_poule.db')
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM coureurs WHERE id = ?", (d[0],))
                    conn.commit()
                    conn.close()
                    st.rerun()

        # 3. Kalender & Sprint Beheer
        with beheer_tab3:
            st.subheader("Races & Sprintweekenden Beheren")
            with st.form("add_race_form"):
                new_race_name = st.text_input("Naam Grand Prix (bijv. Spa GP)")
                new_race_date = st.date_input("Datum")
                is_sprint_race = st.checkbox("Dit is een Sprintweekend")
                add_race_btn = st.form_submit_button("Race Toevoegen")
                
                if add_race_btn and new_race_name:
                    try:
                        conn = sqlite3.connect('f1_poule.db')
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO races (naam, datum, is_sprint) VALUES (?, ?, ?)", 
                                       (new_race_name, str(new_race_date), 1 if is_sprint_race else 0))
                        conn.commit()
                        conn.close()
                        st.success(f"Race {new_race_name} toegevoegd!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Deze race bestaat al.")
                        
            st.markdown("---")
            st.subheader("Kalender Overzicht")
            all_races = get_races()
            for r in all_races:
                col1, col2, col3 = st.columns([3, 2, 1])
                sprint_label = "⚡ Sprint" if r[3] == 1 else ""
                col1.text(f"{r[1]} ({r[2]}) {sprint_label}")
                
                new_status = col2.checkbox("Sprintweekend", value=bool(r[3]), key=f"sprint_toggle_{r[0]}")
                if new_status != bool(r[3]):
                    conn = sqlite3.connect('f1_poule.db')
                    cursor = conn.cursor()
                    cursor.execute("UPDATE races SET is_sprint = ? WHERE id = ?", (int(new_status), r[0]))
                    conn.commit()
                    conn.close()
                    st.rerun()
                    
                if col3.button("Verwijder", key=f"del_race_{r[0]}"):
                    conn = sqlite3.connect('f1_poule.db')
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM races WHERE id = ?", (r[0],))
                    conn.commit()
                    conn.close()
                    st.rerun()

        # 4. Uitslagen & Leaderboard
        with beheer_tab4:
            st.subheader("🏁 Officiële Uitslag & Leaderboard Berekenen per Race")
            races_data = get_races()
            
            if not races_data:
                st.info("Geen races beschikbaar om uitslagen voor in te voeren.")
            else:
                res_race_dict = {f"{r[1]} ({r[2]})": r[0] for r in races_data}
                sel_res_label = st.selectbox("Selecteer Race voor Uitslag", list(res_race_dict.keys()), key="res_race_select")
                sel_res_id = res_race_dict[sel_res_label]
                
                with st.form("form_officiële_uitslag"):
                    st.subheader("1. Officiële Kwalificatie Top 3")
                    off_kwali = []
                    for i in range(1, 4):
                        off_kwali.append(st.selectbox(f"Officiële Kwalificatie P{i}", coureurs_lijst, key=f"off_kwali_p{i}"))

                    st.subheader("2. Officiële Race Top 5")
                    off_race = []
                    c3, c4 = st.columns(2)
                    for i in range(1, 6):
                        with c3 if i <= 3 else c4:
                            off_race.append(st.selectbox(f"Officiële Race P{i}", coureurs_lijst, key=f"off_race_p{i}"))

                    st.subheader("3. Officiële Extra Categorieën")
                    b_col1, b_col2 = st.columns(2)
                    with b_col1:
                        off_fl = st.selectbox("Officiële Fastest Lap", coureurs_lijst, key="off_fl")
                    with b_col2:
                        off_dotd = st.selectbox("Officiële Driver of the Day", coureurs_lijst, key="off_dotd")
                    
                    off_dnf = st.multiselect("Uitvallers (DNF)", coureurs_lijst, key="off_dnf")
                    
                    bereken_leaderboard = st.form_submit_button(label="Bereken Leaderboard")

                    if bereken_leaderboard:
                        officiële_uitslag = {
                            "kwali_top3": off_kwali,
                            "race_top5": off_race,
                            "fastest_lap": off_fl,
                            "driver_of_the_day": off_dotd,
                            "dnf_coureurs": off_dnf
                        }

                        conn = sqlite3.connect('f1_poule.db')
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT u.naam, v.kwali_top3, v.race_top5, v.fastest_lap, v.driver_of_the_day, v.dnf_coureurs, v.h2h_keuzes 
                            FROM voorspellingen v
                            JOIN gebruikers u ON v.email = u.email
                            WHERE v.race_id = ?
                        """, (sel_res_id,))
                        alle_voorspellingen = cursor.fetchall()
                        conn.close()

                        if not alle_voorspellingen:
                            st.warning("Er zijn voor deze race nog geen voorspellingen ingediend!")
                        else:
                            st.subheader("🏆 Totaal Klassement (Leaderboard)")
                            resultaten_lijst = []
                            for row in alle_voorspellingen:
                                deelnemer, v_kwali, v_race, v_fl, v_dotd, v_dnf, v_h2h = row
                                
                                v_kwali_list = json.loads(v_kwali)
                                v_race_list = json.loads(v_race)
                                v_dnf_list = json.loads(v_dnf)
                                v_h2h_dict = json.loads(v_h2h) if v_h2h else {}
                                
                                pnt_kwali = scoring.bereken_top5_punten(v_kwali_list, off_kwali)
                                pnt_race = scoring.bereken_top5_punten(v_race_list, off_race)
                                
                                voorspelling_dict = {
                                    "fastest_lap": v_fl,
                                    "driver_of_the_day": v_dotd,
                                    "dnf_coureurs": v_dnf_list,
                                    "h2h_keuzes": v_h2h_dict
                                }
                                pnt_extra = scoring.bereken_race_gebeurtenissen(voorspelling_dict, officiële_uitslag)
                                
                                totaal_score = pnt_kwali + pnt_race + pnt_extra
                                resultaten_lijst.append({"Deelnemer": deelnemer, "Punten": totaal_score, "Kwali": pnt_kwali, "Race": pnt_race, "Extra": pnt_extra})

                            resultaten_lijst = sorted(resultaten_lijst, key=lambda x: x["Punten"], reverse=True)

                            for idx, res in enumerate(resultaten_lijst, 1):
                                st.write(f"**{idx}. {res['Deelnemer']}** — Totaal: **{res['Punten']} punten** *(Kwali: {res['Kwali']}, Race: {res['Race']}, Extra: {res['Extra']})*")

        if st.button("🗑️ Wis alle voorspellingen"):
            conn = sqlite3.connect('f1_poule.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM voorspellingen")
            conn.commit()
            conn.close()
            st.success("Alle voorspellingen gewist!")
            st.rerun()