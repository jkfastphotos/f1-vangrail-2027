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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voorspellingen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deelnemer TEXT,
            kwali_top3 TEXT,
            race_top5 TEXT,
            fastest_lap TEXT,
            driver_of_the_day TEXT,
            dnf_coureurs TEXT,
            h2h_keuzes TEXT
        )
    ''')
    
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
    conn.commit()
    conn.close()

init_db()

st.title("🏁 F1 Vangrail - FastLine 2027")

# Lijst met coureurs
coureurs_lijst = [
    "Max Verstappen", "Lando Norris", "Charles Leclerc", "Oscar Piastri", 
    "Lewis Hamilton", "George Russell", "Carlos Sainz", "Fernando Alonso", 
    "Sergio Perez", "Alexander Albon", "Kimi Antonelli", "Liam Lawson"
]

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
    tab1, tab2, tab3 = st.tabs(["✍️ Inloggen & Voorspellen", "📊 Leaderboard", "🛠 Beheer"])
else:
    tab1, tab2 = st.tabs(["✍️ Inloggen & Voorspellen", "📊 Leaderboard"])

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
            st.subheader(f"🎯 Voorspelling indienen voor: **{huidige_naam}**")
            with st.form("form_race_voorspelling"):
                st.subheader("1. Kwalificatie Top 3 (25-18-15 punten staffel)")
                kwali_top3 = [st.selectbox(f"Kwalificatie P{i}", coureurs_lijst, key=f"kwali_p{i}") for i in range(1, 4)]

                st.subheader("2. Race Top 5 (25-18-15 punten staffel)")
                race_top5 = []
                col3, col4 = st.columns(2)
                for i in range(1, 6):
                    with col3 if i <= 3 else col4:
                        race_top5.append(st.selectbox(f"Race P{i}", coureurs_lijst, key=f"race_p{i}"))

                st.subheader("3. Losse Categorieën (Goed = 15 pt)")
                c_col1, c_col2 = st.columns(2)
                with c_col1:
                    fastest_lap = st.selectbox("Fastest Lap", coureurs_lijst, key="fl")
                with c_col2:
                    driver_of_the_day = st.selectbox("Driver of the Day", coureurs_lijst, key="dotd")
                dnf_coureurs = st.multiselect("Failed to Finish / DNF (15 pt per correcte coureur)", coureurs_lijst, key="dnf")

                st.subheader("4. Head-to-Head Duels (Goed = 15 pt)")
                h2h_keuzes_dict = {}
                for idx, (c1, c2) in enumerate(huidige_gp_duels):
                    st.markdown(f"**Duel {idx+1}:**")
                    keuze = st.radio(f"Wie wint: {c1} vs {c2}?", [c1, c2], key=f"h2h_duel_{idx}", horizontal=True)
                    h2h_keuzes_dict[f"{c1}_vs_{c2}"] = keuze

                if st.form_submit_button("Mijn Voorspelling Opslaan"):
                    conn = sqlite3.connect('f1_poule.db')
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM voorspellingen WHERE deelnemer = ?", (huidige_naam,))
                    bestaat = cursor.fetchone()
                    if bestaat:
                        cursor.execute("UPDATE voorspellingen SET kwali_top3=?, race_top5=?, fastest_lap=?, driver_of_the_day=?, dnf_coureurs=?, h2h_keuzes=? WHERE deelnemer=?", 
                                       (json.dumps(kwali_top3), json.dumps(race_top5), fastest_lap, driver_of_the_day, json.dumps(dnf_coureurs), json.dumps(h2h_keuzes_dict), huidige_naam))
                    else:
                        cursor.execute("INSERT INTO voorspellingen (deelnemer, kwali_top3, race_top5, fastest_lap, driver_of_the_day, dnf_coureurs, h2h_keuzes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                       (huidige_naam, json.dumps(kwali_top3), json.dumps(race_top5), fastest_lap, driver_of_the_day, json.dumps(dnf_coureurs), json.dumps(h2h_keuzes_dict)))
                    conn.commit()
                    conn.close()
                    st.success("Voorspelling opgeslagen!")
        else:
            st.warning("Je account is nog niet goedgekeurd door de beheerder.")
            
    else:
        auth_optie = st.radio("Kies een optie:", ["Inloggen", "Nieuw account registreren", "Wachtwoord vergeten"], horizontal=True)
        
        if auth_optie == "Nieuw account registreren":
            with st.form("form_register", clear_on_submit=True):
                reg_naam = st.text_input("Naam *")
                reg_email = st.text_input("E-mailadres *")
                reg_tel = st.text_input("Telefoonnummer *")
                reg_ww = st.text_input("Wachtwoord *", type="password")
                if st.form_submit_button("Registreren"):
                    if reg_naam and reg_email and reg_tel and reg_ww:
                        is_adm = 1 if reg_email.lower() == ADMIN_EMAIL.lower() else 0
                        conn = sqlite3.connect('f1_poule.db')
                        cursor = conn.cursor()
                        try:
                            cursor.execute("INSERT INTO gebruikers (naam, wachtwoord, email, telefoon, is_goedgekeurd, is_admin) VALUES (?, ?, ?, ?, ?, ?)", 
                                           (reg_naam, reg_ww, reg_email.lower(), reg_tel, is_adm, is_adm))
                            conn.commit()
                            st.success("Account aangemaakt! Wacht op goedkeuring door de beheerder na betaling.")
                        except sqlite3.IntegrityError:
                            st.error("E-mailadres is al in gebruik.")
                        conn.close()
                    else:
                        st.error("Vul alle velden in.")

        elif auth_optie == "Inloggen":
            with st.form("form_login"):
                login_email = st.text_input("E-mailadres", autocomplete="username")
                login_ww = st.text_input("Wachtwoord", type="password", autocomplete="current-password")
                if st.form_submit_button("Inloggen"):
                    conn = sqlite3.connect('f1_poule.db')
                    cursor = conn.cursor()
                    if login_email.lower() == ADMIN_EMAIL.lower():
                        cursor.execute("UPDATE gebruikers SET is_admin = 1, is_goedgekeurd = 1 WHERE email = ?", (login_email.lower(),))
                        conn.commit()
                    cursor.execute("SELECT naam, wachtwoord, is_goedgekeurd, is_admin FROM gebruikers WHERE email = ?", (login_email.lower(),))
                    res = cursor.fetchone()
                    conn.close()
                    
                    if not res:
                        st.error("Account niet gevonden.")
                    elif res[1] != login_ww:
                        st.error("Onjuist wachtwoord!")
                    else:
                        st.session_state.update({"ingelogde_email": login_email.lower(), "ingelogde_naam": res[0], "is_goedgekeurd": res[2], "is_admin": res[3]})
                        st.rerun()
                        
        elif auth_optie == "Wachtwoord vergeten":
            with st.form("form_ww_reset"):
                reset_email = st.text_input("E-mailadres")
                reset_tel = st.text_input("Telefoonnummer ter controle")
                nieuw_ww = st.text_input("Nieuw Wachtwoord", type="password")
                if st.form_submit_button("Wachtwoord Herstellen"):
                    conn = sqlite3.connect('f1_poule.db')
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM gebruikers WHERE email = ? AND telefoon = ?", (reset_email.lower(), reset_tel))
                    if cursor.fetchone():
                        cursor.execute("UPDATE gebruikers SET wachtwoord = ? WHERE email = ?", (nieuw_ww, reset_email.lower()))
                        conn.commit()
                        st.success("Wachtwoord succesvol gewijzigd! Je kunt nu inloggen.")
                    else:
                        st.error("Gegevens komen niet overeen.")
                    conn.close()

with tab2:
    st.header("📊 Leaderboard")
    st.info("Hier komt straks het score-overzicht.")

if is_admin_ingelogd:
    with tab3:
        st.header("📇 Deelnemers & Contactkaarten Beheren")
        
        conn = sqlite3
