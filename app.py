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
    
    # 2. Nieuwe tabel voor gebruikers, wachtwoorden en goedkeuring na betaling
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gebruikers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            naam TEXT UNIQUE,
            wachtwoord TEXT,
            is_goedgekeurd INTEGER DEFAULT 0
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

# Tabbladen boven aan het scherm (we voegen straks een Registratie/Login tab toe)
tab1, tab2, tab3 = st.tabs(["✍️ Voorspelling Indienen", "📊 Punten & Score Testen", "🛠 Beheer"])

with tab1:
    st.header("✍️ Race Voorspelling Indienen")
    st.info("Hier komt straks het inlogscherm voor goedgekeurde deelnemers!")

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
        st.success("Toegang verleend! Je kunt hieronder de uitslag invullen en betalingen beheren.")
        
        if st.button("🗑️ Wis alle voorspellingen uit database"):
            conn = sqlite3.connect('f1_poule.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM voorspellingen")
            conn.commit()
            conn.close()
            st.success("De database is volledig schoongemaakt!")
            st.rerun()
            
    elif ingevoerd_wachtwoord != "":
        st.error("Onjuist wachtwoord!")
    else:
        st.info("Voer het beheerderswachtwoord in om te ontgrendelen.")