import streamlit as st
import sqlite3
import json
import scoring

# Pagina configuratie
st.set_page_config(page_title="F1 Vangrail - FastLine 2027", layout="wide")

# Vaste naam die automatisch beheerder wordt bij registratie (pas dit aan naar jouw naam als je wilt)
ADMIN_NAAM = "Jurgen Kessels" 

# --- DATABASE INITIALISATIE ---
def init_db():
    conn = sqlite3.connect('f1_poule.db')
    cursor = conn.cursor()
    
    # 1. Tabel voor voorspellingen
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voorspellingen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deelnemer TEXT,
            kwali_top5 TEXT,
            race_top5 TEXT,
            fastest_lap TEXT,
            driver_of_the_day TEXT,
            dnf_coureurs TEXT,
            h2h_keuzes TEXT
        )
    ''')
    
    # 2. Tabel voor gebruikers controleren en aanmaken met is_admin kolom
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gebruikers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            naam TEXT UNIQUE,
            wachtwoord TEXT,
            email TEXT,
            telefoon TEXT,
            is_goedgekeurd INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    # Controleer of de kolom 'is_admin' al bestaat
    cursor.execute("PRAGMA table_info(gebruikers)")
    kolommen = [col[1] for col in cursor.fetchall()]
    if "is_admin" not in kolommen:
        cursor.execute("ALTER TABLE gebruikers ADD COLUMN is_admin INTEGER DEFAULT 0")
        
    conn.commit()
    conn.close()

init_db()

st.title("🏁 F1 Vangrail - FastLine 2027")

# Lijst met coureurs voor het seizoen 2027
coureurs_lijst = [
    "Max Verstappen", "Lando Norris", "Charles Leclerc", "Oscar Piastri", 
    "Lewis Hamilton", "George Russell", "Carlos Sainz", "Fernando Alonso", 
    "Sergio Perez", "Alexander Albon", "Kimi Antonelli", "Liam Lawson"
]

# We controleren of de ingelogde gebruiker een admin is via de session_state
is_admin_ingelogd = st.session_state.get("is_admin", 0) == 1

# Dynamisch tabbladen tonen: het beheertabblad verschijnt ALLEEN als de beheerder is ingelogd!
if is_admin_ingelogd:
    tab1, tab2, tab3 = st.tabs(["✍️ Inloggen & Voorspellen", "📊 Punten & Score Testen", "🛠 Beheer"])
else:
    tab1, tab2 = st.tabs(["✍️ Inloggen & Voorspellen", "📊 Punten & Score Testen"])

with tab1:
    st.header("✍️ Deelnemers Portaal")
    
    # Als er iemand is ingelogd, tonen we de gebruikersinfo en uitlogknop
    if "ingelogde_gebruiker" in st.session_state:
        huidige_gebruiker = st.session_state["ingelogde_gebruiker"]
        st.success(f"Ingelogd als: **{huidige_gebruiker}**")
        
        col_uitlog, col_admin_tip = st.columns([1, 3])
        with col_uitlog:
            if st.button("Uitloggen"):
                del st.session_state["ingelogde_gebruiker"]
                st.session_state["is_admin"] = 0
                st.session_state["is_goedgekeurd"] = 0
                st.rerun()
                
        # Als de gebruiker goedgekeurd is, tonen we het voorspellingsformulier
        if st.session_state.get("is_goedgekeurd", 0) == 1:
            st.markdown(f"---")
            st.subheader(f"🎯 Voorspelling indienen voor: **{huidige_gebruiker}**")

            with st.form("form_race_voorspelling"):
                # 1. Kwalificatie Top 5
                st.subheader("1. Kwalificatie Top 5")
                kwali_top5 = []
                col1, col2 = st.columns(2)
                for i in range(1, 6):
                    with col1 if i <= 3 else col2:
                        c = st.selectbox(f"Kwalificatie P{i}", coureurs_lijst, key=f"kwali_p{i}")
                        kwali_top5.append(c)

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

                # 4. Head-to-Head
                st.subheader("4. Head-to-Head (15 pt)")
                h2h_optie = st.selectbox(
                    "Kies het duel:",
                    ["Max Verstappen vs Lando Norris", "Charles Leclerc vs Oscar Piastri"],
                    key="h2h_duel"
                )
                h2h_winnaar = st.radio("Wie verslaat wie in dit duel?", h2h_optie.split(" vs "), key="h2h_winnaar")

                submit_voorspelling = st.form_submit_button(label="Mijn Voorspelling Opslaan")

                if submit_voorspelling:
                    h2h_key = h2h_optie.replace(" ", "_")
                    
                    conn = sqlite3.connect('f1_poule.db')
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM voorspellingen WHERE deelnemer = ?", (huidige_gebruiker,))
                    bestaat = cursor.fetchone()
                    
                    if bestaat:
                        cursor.execute('''
                            UPDATE voorspellingen 
                            SET kwali_top5 = ?, race_top5 = ?, fastest_lap = ?, driver_of_the_day = ?, dnf_coureurs = ?, h2h_keuzes = ?
                            WHERE deelnemer = ?
                        ''', (
                            json.dumps(kwali_top5), json.dumps(race_top5), fastest_lap, driver_of_the_day, 
                            json.dumps(dnf_coureurs), json.dumps({h2h_key: h2h_winnaar}), huidige_gebruiker
                        ))
                    else:
                        cursor.execute('''
                            INSERT INTO voorspellingen (deelnemer, kwali_top5, race_top5, fastest_lap, driver_of_the_day, dnf_coureurs, h2h_keuzes)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            huidige_gebruiker, json.dumps(kwali_top5), json.dumps(race_top5), fastest_lap, 
                            driver_of_the_day, json.dumps(dnf_coureurs), json.dumps({h2h_key: h2h_winnaar})
                        ))
                        
                    conn.commit()
                    conn.close()
                    st.success("Je voorspelling is succesvol opgeslagen!")
        else:
            st.warning("Jouw account is nog **niet goedgekeurd** door de beheerder (wacht op betaling). Zodra dit in orde is, verschijnt hier je voorspellingsformulier.")

    else:
        # Keuze tussen Inloggen of Registreren als je nog niet bent ingelogd
        auth_optie = st.radio("Kies een optie:", ["Inloggen", "Nieuw account registreren"], horizontal=True)
        
        if auth_optie == "Nieuw account registreren":
            st.subheader("📝 Registreren voor de Poule")
            st.info(f"Registreer je hier. Als je de naam '{ADMIN_NAAM}' gebruikt, word je automatisch beheerder!")
            
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
                        # Als de naam gelijk is aan ADMIN_NAAM, krijgt deze direct is_goedgekeurd = 1 en is_admin = 1
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
                            if is_adm == 1:
                                st.success(f"Beheerdersaccount voor {reg_naam} succesvol aangemaakt! Je kunt nu direct inloggen.")
                            else:
                                st.success(f"Account voor {reg_naam} succesvol aangemaakt! Wacht op goedkeuring door de beheerder na betaling.")
                        except sqlite3.IntegrityError:
                            st.error("⚠️ Deze naam bestaat al in het systeem. Kies een andere naam of log in.")
        
        else:
            st.subheader("🔑 Inloggen")
            with st.form("form_login"):
                login_naam = st.text_input("Jouw Naam")
                login_ww = st.text_input("Jouw Wachtwoord", type="password")
                login_submit = st.form_submit_button("Inloggen")
                
                if login_submit:
                    conn = sqlite3.connect('f1_poule.db')
                    cursor = conn.cursor()
                    cursor.execute("SELECT wachtwoord, is_goedgekeurd, is_admin FROM gebruikers WHERE naam = ?", (login_naam,))
                    res = cursor.fetchone()
                    conn.close()
                    
                    if not res:
                        st.error("Gebruiker niet gevonden. Registreer je eerst via het tabje hierboven.")
                    elif res[0] != login_ww:
                        st.error("Onjuist wachtwoord!")
                    else:
                        st.session_state["ingelogde_gebruiker"] = login_naam
                        st.session_state["is_goedgekeurd"] = res[1]
                        st.session_state["is_admin"] = res[2]
                        st.success(f"Welkom terug, {login_naam}!")
                        st.rerun()

with tab2:
    st.header("📊 Score Berekening Testen")
    st.write("Test hier of de puntentelling via `scoring.py` correct werkt op basis van een voorbeeld-uitslag.")

    uitslag_voorbeeld = {
        "kwali_top5": ["Max Verstappen", "Lando Norris", "Charles Leclerc", "Oscar Piastri", "Lewis Hamilton"],
        "race_top5": ["Max Verstappen", "Charles Leclerc", "Lando Norris", "Oscar Piastri", "George Russell"],
        "fastest_lap": "Max Verstappen",
        "driver_of_the_day": "Lando Norris",
        "dnf_coureurs": ["Sergio Perez", "Carlos Sainz"]
    }

    if st.button("Bereken testpunten"):
        kwali_pnt = scoring.bereken_top5_punten(
            ["Max Verstappen", "Lando Norris", "Charles Leclerc", "Oscar Piastri", "Lewis Hamilton"], 
            uitslag_voorbeeld["kwali_top5"]
        )
        race_pnt = scoring.bereken_top5_punten(
            ["Max Verstappen", "Charles Leclerc", "Lando Norris", "Oscar Piastri", "George Russell"], 
            uitslag_voorbeeld["race_top5"]
        )
        extra_pnt = scoring.bereken_race_gebeurtenissen({
            "fastest_lap": "Max Verstappen",
            "driver_of_the_day": "Lando Norris",
            "dnf_coureurs": ["Sergio Perez"],
            "h2h_keuzes": {"Max_Verstappen_vs_Lando_Norris": "Max Verstappen"}
        }, uitslag_voorbeeld)
        
        totaal = kwali_pnt + race_pnt + extra_pnt
        st.success(f"Totale punten berekend: {totaal}")
        st.write(f"- Kwalificatie punten: {kwali_pnt}")
        st.write(f"- Race punten: {race_pnt}")
        st.write(f"- Extra categorieën punten: {extra_pnt}")

# Het Beheerders-tabblad wordt alleen aangemaakt en getoond als de beheerder is ingelogd!
if is_admin_ingelogd:
    with tab3:
        st.header("🛠 Beheerderspaneel")
        st.success("Je bent ingelogd als beheerder.")
        
        # Goedkeuren van gebruikers na betaling en optie om admin te maken
        st.subheader("👥 Deelnemers & Betalingen Goedkeuren")
        conn = sqlite3.connect('f1_poule.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, naam, email, telefoon, is_goedgekeurd, is_admin FROM gebruikers")
        alle_gebruikers = cursor.fetchall()
        
        for g_id, g_naam, g_email, g_tel, g_goed, g_adm in alle_gebruikers:
            with st.container():
                admin_label = " 👑 [ADMIN]" if g_adm == 1 else ""
                st.write(f"**Naam:** {g_naam}{admin_label} | **E-mail:** {g_email} | **Tel:** {g_tel}")
                col_status, col_actie1, col_actie2 = st.columns([2, 2, 2])
                with col_status:
                    status_txt = "✅ Goedgekeurd" if g_goed == 1 else "❌ Nog niet betaald"
                    st.write(f"Status: {status_txt}")
                with col_actie1:
                    if g_goed == 0:
                        if st.button(f"Goedkeuren", key=f"goed_{g_id}"):
                            cursor.execute("UPDATE gebruikers SET is_goedgekeurd = 1 WHERE id = ?", (g_id,))
                            conn.commit()
                            st.rerun()
                    else:
                        if st.button(f"Blokkeren", key=f"blok_{g_id}"):
                            cursor.execute("UPDATE gebruikers SET is_goedgekeurd = 0 WHERE id = ?", (g_id,))
                            conn.commit()
                            st.rerun()
                with col_actie2:
                    if g_adm == 0:
                        if st.button(f"Maak Admin", key=f"makest_admin_{g_id}"):
                            cursor.execute("UPDATE gebruikers SET is_admin = 1 WHERE id = ?", (g_id,))
                            conn.commit()
                            st.rerun()
                    else:
                        if g_naam.lower() != ADMIN_NAAM.lower():
                            if st.button(f"Ontneem Admin", key=f"rem_admin_{g_id}"):
                                cursor.execute("UPDATE gebruikers SET is_admin = 0 WHERE id = ?", (g_id,))
                                conn.commit()
                                st.rerun()
                st.markdown("---")
        conn.close()

        st.subheader("🏁 Officiële Uitslag & Leaderboard Berekenen")
        
        with st.form("form_officiële_uitslag"):
            st.subheader("1. Officiële Kwalificatie Top 5")
            off_kwali = []
            c1, c2 = st.columns(2)
            for i in range(1, 6):
                with c1 if i <= 3 else c2:
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
                    "kwali_top5": off_kwali,
                    "race_top5": off_race,
                    "fastest_lap": off_fl,
                    "driver_of_the_day": off_dotd,
                    "dnf_coureurs": off_dnf
                }

                conn = sqlite3.connect('f1_poule.db')
                cursor = conn.cursor()
                cursor.execute("SELECT deelnemer, kwali_top5, race_top5, fastest_lap, driver_of_the_day, dnf_coureurs, h2h_keuzes FROM voorspellingen")
                alle_voorspellingen = cursor.fetchall()
                conn.close()

                if not alle_voorspellingen:
                    st.warning("Er zijn nog geen voorspellingen ingediend!")
                else:
                    st.subheader("🏆 Totaal Klassement (Leaderboard)")
                    resultaten_lijst = []
                    for row in alle_voorspellingen:
                        deelnemer, v_kwali, v_race, v_fl, v_dotd, v_dnf, v_h2h = row
                        
                        v_kwali_list = json.loads(v_kwali)
                        v_race_list = json.loads(v_race)
                        v_dnf_list = json.loads(v_dnf)
                        v_h2h_dict = json.loads(v_h2h)
                        
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