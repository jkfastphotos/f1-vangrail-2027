import streamlit as st
import sqlite3
import json
import scoring

# Pagina configuratie
st.set_page_config(page_title="F1 Vangrail - FastLine 2027", layout="wide")

# --- DATABASE INITIALISATIE ---
def init_db():
    conn = sqlite3.connect('f1_poule.db')
    cursor = conn.cursor()
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

# Deelnemerslijst (gebaseerd op jullie poule)
deelnemers_lijst = [
    "Jurgen Kessels", "Mark Geerlings", "Bart Venner", "Pascal Vervuurt", 
    "Tamara van Rijt", "John Slaats", "Linda Wijnen", "Rob van Heugten"
]

# Tabbladen boven aan het scherm
tab1, tab2, tab3 = st.tabs(["✍️ Voorspelling Indienen", "📊 Punten & Score Testen", "🛠 Beheer"])

with tab1:
    st.header("✍️ Race Voorspelling Indienen")
    
    gekozen_deelnemer = st.selectbox("Kies jouw naam:", deelnemers_lijst)
    st.write(f"Voorspelling indienen voor: **{gekozen_deelnemer}**")

    with st.form("form_race_voorspelling"):
        
        # 1. Kwalificatie Top 5
        st.subheader("1. Kwalificatie Top 5")
        st.info("Exact goed = 25 punten, per positie afwijking loopt het af.")
        kwali_top5 = []
        col1, col2 = st.columns(2)
        for i in range(1, 6):
            with col1 if i <= 3 else col2:
                c = st.selectbox(f"Kwalificatie P{i}", coureurs_lijst, key=f"kwali_p{i}")
                kwali_top5.append(c)

        # 2. Race Top 5
        st.subheader("2. Race Top 5")
        st.info("Voorspel de top 5 van de race.")
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
        st.subheader("4. Head-to-Head (15 pt + Verstappen bonus)")
        h2h_optie = st.selectbox(
            "Kies het duel:",
            ["Max Verstappen vs Lando Norris", "Charles Leclerc vs Oscar Piastri"],
            key="h2h_duel"
        )
        h2h_winnaar = st.radio("Wie verslaat wie in dit duel?", h2h_optie.split(" vs "), key="h2h_winnaar")

        submit_voorspelling = st.form_submit_button(label="Voorspelling Opslaan")

        if submit_voorspelling:
            h2h_key = h2h_optie.replace(" ", "_")
            
            conn = sqlite3.connect('f1_poule.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM voorspellingen WHERE deelnemer = ?", (gekozen_deelnemer,))
            bestaat = cursor.fetchone()
            
            if bestaat:
                cursor.execute('''
                    UPDATE voorspellingen 
                    SET kwali_top5 = ?, race_top5 = ?, fastest_lap = ?, driver_of_the_day = ?, dnf_coureurs = ?, h2h_keuzes = ?
                    WHERE deelnemer = ?
                ''', (
                    json.dumps(kwali_top5), json.dumps(race_top5), fastest_lap, driver_of_the_day, 
                    json.dumps(dnf_coureurs), json.dumps({h2h_key: h2h_winnaar}), gekozen_deelnemer
                ))
            else:
                cursor.execute('''
                    INSERT INTO voorspellingen (deelnemer, kwali_top5, race_top5, fastest_lap, driver_of_the_day, dnf_coureurs, h2h_keuzes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    gekozen_deelnemer, json.dumps(kwali_top5), json.dumps(race_top5), fastest_lap, 
                    driver_of_the_day, json.dumps(dnf_coureurs), json.dumps({h2h_key: h2h_winnaar})
                ))
                
            conn.commit()
            conn.close()
            
            st.success(f"Bedankt {gekozen_deelnemer}! Je voorspelling is succesvol opgeslagen in de database.")

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

with tab3:
    st.header("🛠 Beheerdersscherm")
    
    # Wachtwoordbeveiliging
    beheerders_wachtwoord = "305710"
    ingevoerd_wachtwoord = st.text_input("Voer het beheerderswachtwoord in:", type="password")

    if ingevoerd_wachtwoord == beheerders_wachtwoord:
        st.success("Toegang verleend! Je kunt hieronder de uitslag invullen.")
        
        # Knop om database op te schonen direct zichtbaar na inloggen
        if st.button("🗑️ Wis alle voorspellingen uit database"):
            conn = sqlite3.connect('f1_poule.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM voorspellingen")
            conn.commit()
            conn.close()
            st.success("De database is volledig schoongemaakt! Alle testvoorspellingen zijn verwijderd.")
            st.rerun()

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
            
            st.subheader("4. Officiële Head-to-Head Uitslag")
            off_h2h_winnaar = st.selectbox("Max Verstappen vs Lando Norris - Winnaar", ["Max Verstappen", "Lando Norris"], key="off_h2h")

            bereken_leaderboard = st.form_submit_button(label="Bereken Leaderboard voor alle deelnemers")

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
                    st.warning("Er zijn nog geen voorspellingen ingediend in de database om te berekenen!")
                else:
                    st.subheader("🏆 Klassement (Leaderboard)")
                    
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
                        
    elif ingevoerd_wachtwoord != "":
        st.error("Onjuist wachtwoord! Alleen de beheerder heeft toegang tot dit scherm.")
    else:
        st.info("Voer het wachtwoord in om het beheerdersscherm te ontgrendelen.")