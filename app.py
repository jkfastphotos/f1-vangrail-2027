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

# Zijbalk navigatie
menu = st.sidebar.selectbox("Menu", ["Voorspelling Indienen", "Punten & Score Testen"])

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

if menu == "Voorspelling Indienen":
    st.header("✍️ Race Voorspelling Indienen")
    
    gekozen_deelnemer = st.sidebar.selectbox("Kies jouw naam:", deelnemers_lijst)
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
            
            # Opslaan in de SQLite database
            conn = sqlite3.connect('f1_poule.db')
            cursor = conn.cursor()
            
            # Controleer of deze deelnemer al een voorspelling heeft ingediend en update of insert
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

elif menu == "Punten & Score Testen":
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