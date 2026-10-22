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
                    veilig_c1 = c1 if c1 in coureurs_lijst else cou
