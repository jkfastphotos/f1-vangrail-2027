import sqlite3
import streamlit as st
import hashlib

# Pagina configuratie
st.set_page_config(page_title="F1 Vangrail - FastLine 2027", page_icon="🏎️", layout="wide")

# Database initialisatie
def init_db():
    conn = sqlite3.connect("f1_vangrail.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Tabel voor gebruikers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            phone TEXT,
            password TEXT,
            is_approved INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0
        )
    """)
    
    # Tabel voor coureurs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            team TEXT
        )
    """)
    
    # Tabel voor races / kalender (met is_sprint vlag)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS races (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            date TEXT,
            is_sprint INTEGER DEFAULT 0
        )
    """)
    
    # Tabel voor voorspellingen
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            race_id INTEGER,
            q1 TEXT, q2 TEXT, q3 TEXT,
            r1 TEXT, r2 TEXT, r3 TEXT, r4 TEXT, r5 TEXT,
            fastest_lap TEXT,
            dotd TEXT,
            dnfs INTEGER,
            sprint_q1 TEXT, sprint_q2 TEXT, sprint_q3 TEXT,
            sprint_r1 TEXT, sprint_r2 TEXT, sprint_r3 TEXT,
            h2h_winner TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(race_id) REFERENCES races(id)
        )
    """)
    
    conn.commit()
    
    # Standaard admin aanmaken indien niet aanwezig ('Jurgen Kessels')
    cursor.execute("SELECT * FROM users WHERE email = 'admin@f1vangrail.nl'")
    if not cursor.fetchone():
        hashed_pw = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute("""
            INSERT INTO users (name, email, phone, password, is_approved, is_admin)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("Jurgen Kessels", "admin@f1vangrail.nl", "0612345678", hashed_pw, 1, 1))
        conn.commit()
        
    # Standaard coureurs vullen als de tabel leeg is
    cursor.execute("SELECT COUNT(*) FROM drivers")
    if cursor.fetchone()[0] == 0:
        default_drivers = [
            ("Max Verstappen", "Red Bull Racing"), ("Lando Norris", "McLaren"),
            ("Charles Leclerc", "Ferrari"), ("Lewis Hamilton", "Ferrari"),
            ("Oscar Piastri", "McLaren"), ("George Russell", "Mercedes"),
            ("Kimi Antonelli", "Mercedes"), ("Carlos Sainz", "Williams")
        ]
        cursor.executemany("INSERT INTO drivers (name, team) VALUES (?, ?)", default_drivers)
        conn.commit()

    # Standaard races vullen als de tabel leeg is
    cursor.execute("SELECT COUNT(*) FROM races")
    if cursor.fetchone()[0] == 0:
        default_races = [
            ("Bahrain GP", "2027-03-21", 0),
            ("Chinese GP", "2027-04-04", 1),  # Voorbeeld Sprintweekend
            ("Monaco GP", "2027-05-23", 0)
        ]
        cursor.executemany("INSERT INTO races (name, date, is_sprint) VALUES (?, ?, ?)", default_races)
        conn.commit()
        
    return conn

conn = init_db()
cursor = conn.cursor()

# Authenticatie state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""
    st.session_state.is_admin = False
    st.session_state.user_id = None

# --- AUTHENTICATIE SCHERM ---
if not st.session_state.logged_in:
    st.title("🏎️ F1 Vangrail - FastLine 2027")
    tab1, tab2 = st.tabs(["Inloggen", "Registreren"])
    
    with tab1:
        st.subheader("Inloggen bij jouw account")
        email = st.text_input("E-mailadres", key="login_email")
        password = st.text_input("Wachtwoord", type="password", key="login_pass")
        if st.button("Inloggen"):
            hashed_pw = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute("SELECT id, name, is_approved, is_admin FROM users WHERE email = ? AND password = ?", (email, hashed_pw))
            user = cursor.fetchone()
            if user:
                if user[2] == 1 or user[3] == 1:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0]
                    st.session_state.user_name = user[1]
                    st.session_state.is_admin = bool(user[3])
                    st.success(f"Welkom terug, {user[1]}!")
                    st.rerun()
                else:
                    st.warning("Je account is nog niet goedgekeurd door de beheerder.")
            else:
                st.error("Ongeldige inloggegevens.")
                
    with tab2:
        st.subheader("Nieuw account registreren")
        reg_name = st.text_input("Volledige naam")
        reg_email = st.text_input("E-mailadres", key="reg_email")
        reg_phone = st.text_input("Telefoonnummer")
        reg_pass = st.text_input("Wachtwoord", type="password", key="reg_pass")
        if st.button("Registreren"):
            if reg_name and reg_email and reg_phone and reg_pass:
                try:
                    hashed_pw = hashlib.sha256(reg_pass.encode()).hexdigest()
                    # Automatisch admin toekennen als naam Jurgen Kessels is
                    is_admin_flag = 1 if reg_name.strip() == "Jurgen Kessels" else 0
                    is_approved_flag = 1 if is_admin_flag == 1 else 0
                    
                    cursor.execute("""
                        INSERT INTO users (name, email, phone, password, is_approved, is_admin)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (reg_name, reg_email, reg_phone, hashed_pw, is_approved_flag, is_admin_flag))
                    conn.commit()
                    st.success("Registratie succesvol! Wacht op goedkeuring van de beheerder (tenzij je admin bent).")
                except sqlite3.IntegrityError:
                    st.error("Dit e-mailadres is al geregistreerd.")
            else:
                st.warning("Vul alle verplichte velden in.")
                
else:
    # --- HOOFDAPPLICATIE NA INLOGGEN ---
    st.sidebar.title(f"Welkom, {st.session_state.user_name}")
    
    menu = ["Voorspellingen", "Leaderboard"]
    if st.session_state.is_admin:
        menu.append("Beheer")
    
    choice = st.sidebar.selectbox("Navigatie", menu)
    
    if st.sidebar.button("Uitloggen"):
        st.session_state.logged_in = False
        st.session_state.user_name = ""
        st.session_state.is_admin = False
        st.session_state.user_id = None
        st.rerun()
        
    # Haal actuele coureurs en races op uit DB
    cursor.execute("SELECT name FROM drivers")
    driver_list = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT id, name, is_sprint FROM races")
    races_data = cursor.fetchall()

    if choice == "Voorspellingen":
        st.header("🏁 Grand Prix Voorspellingen")
        
        if not races_data:
            st.info("Geen races beschikbaar in de kalender.")
        else:
            race_dict = {f"{r[1]} {'(Sprintweekend)' if r[2]==1 else ''}": r[0] for r in races_data}
            selected_race_label = st.selectbox("Selecteer Race", list(race_dict.keys()))
            selected_race_id = race_dict[selected_race_label]
            
            # Controleren of het een sprintweekend is
            cursor.execute("SELECT is_sprint FROM races WHERE id = ?", (selected_race_id,))
            is_sprint = cursor.fetchone()[0] == 1
            
            with st.form("prediction_form"):
                st.subheader("Kwalificatie (Top 3)")
                q1 = st.selectbox("P1 Kwalificatie", driver_list, key="q1")
                q2 = st.selectbox("P2 Kwalificatie", driver_list, key="q2")
                q3 = st.selectbox("P3 Kwalificatie", driver_list, key="q3")
                
                if is_sprint:
                    st.subheader("⚡ Sprint Weekend Extra's")
                    sq1 = st.selectbox("Sprint Kwalificatie / Shootout P1", driver_list, key="sq1")
                    sq2 = st.selectbox("Sprint Kwalificatie / Shootout P2", driver_list, key="sq2")
                    sq3 = st.selectbox("Sprint Kwalificatie / Shootout P3", driver_list, key="sq3")
                    
                    sr1 = st.selectbox("Sprintrace P1", driver_list, key="sr1")
                    sr2 = st.selectbox("Sprintrace P2", driver_list, key="sr2")
                    sr3 = st.selectbox("Sprintrace P3", driver_list, key="sr3")
                else:
                    sq1 = sq2 = sq3 = sr1 = sr2 = sr3 = ""
                
                st.subheader("Race (Top 5)")
                r1 = st.selectbox("P1 Race", driver_list, key="r1")
                r2 = st.selectbox("P2 Race", driver_list, key="r2")
                r3 = st.selectbox("P3 Race", driver_list, key="r3")
                r4 = st.selectbox("P4 Race", driver_list, key="r4")
                r5 = st.selectbox("P5 Race", driver_list, key="r5")
                
                st.subheader("Losse Categorieën")
                fastest_lap = st.selectbox("Fastest Lap", driver_list, key="fl")
                dotd = st.selectbox("Driver of the Day", driver_list, key="dotd")
                dnfs = st.number_input("Aantal DNF's (Uitvallers)", min_value=0, max_value=20, value=2, step=1)
                
                submitted = st.form_submit_button("Voorspelling Opslaan")
                if submitted:
                    # Opslaan of updaten in database
                    cursor.execute("""
                        SELECT id FROM predictions WHERE user_id = ? AND race_id = ?
                    """, (st.session_state.user_id, selected_race_id))
                    existing = cursor.fetchone()
                    
                    if existing:
                        cursor.execute("""
                            UPDATE predictions SET q1=?, q2=?, q3=?, r1=?, r2=?, r3=?, r4=?, r5=?, 
                            fastest_lap=?, dotd=?, dnfs=?, sprint_q1=?, sprint_q2=?, sprint_q3=?, 
                            sprint_r1=?, sprint_r2=?, sprint_r3=? WHERE id=?
                        """, (q1, q2, q3, r1, r2, r3, r4, r5, fastest_lap, dotd, dnfs, sq1, sq2, sq3, sr1, sr2, sr3, existing[0]))
                    else:
                        cursor.execute("""
                            INSERT INTO predictions (user_id, race_id, q1, q2, q3, r1, r2, r3, r4, r5, 
                            fastest_lap, dotd, dnfs, sprint_q1, sprint_q2, sprint_q3, sprint_r1, sprint_r2, sprint_r3)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (st.session_state.user_id, selected_race_id, q1, q2, q3, r1, r2, r3, r4, r5, fastest_lap, dotd, dnfs, sq1, sq2, sq3, sr1, sr2, sr3))
                    
                    conn.commit()
                    st.success("Je voorspelling is succesvol opgeslagen!")

    elif choice == "Leaderboard":
        st.header("🏆 Leaderboard")
        st.info("Hier komt straks de puntentelling vanuit scoring.py te staan.")

    elif choice == "Beheer" and st.session_state.is_admin:
        st.header("⚙️ Beheerderspaneel")
        
        tab_users, tab_drivers, tab_races = st.tabs(["Betalingen & Gebruikers", "Coureurs Beheer", "Races & Kalender Beheer"])
        
        with tab_users:
            st.subheader("Goedkeuring Betalingen & Accounts")
            cursor.execute("SELECT id, name, email, phone, is_approved FROM users WHERE is_admin = 0")
            pending_users = cursor.fetchall()
            
            if not pending_users:
                st.write("Geen gebruikers in afwachting van goedkeuring.")
            else:
                for u in pending_users:
                    col1, col2, col3 = st.columns([3, 2, 2])
                    col1.text(f"{u[1]} ({u[2]}) - {u[3]}")
                    status_text = "Goedgekeurd" if u[4] == 1 else "In afwachting"
                    col2.text(status_text)
                    if u[4] == 0:
                        if col3.button("Goedkeuren", key=f"app_{u[0]}"):
                            cursor.execute("UPDATE users SET is_approved = 1 WHERE id = ?", (u[0],))
                            conn.commit()
                            st.success(f"Gebruiker {u[1]} goedgekeurd!")
                            st.rerun()
                    else:
                        if col3.button("Blokkeren", key=f"blok_{u[0]}"):
                            cursor.execute("UPDATE users SET is_approved = 0 WHERE id = ?", (u[0],))
                            conn.commit()
                            st.warning(f"Gebruiker {u[1]} geblokkeerd.")
                            st.rerun()

        with tab_drivers:
            st.subheader("Coureurs Toevoegen / Verwijderen")
            
            with st.form("add_driver_form"):
                new_driver_name = st.text_input("Naam Coureur")
                new_driver_team = st.text_input("Team")
                add_driver_btn = st.form_submit_button("Coureur Toevoegen")
                if add_driver_btn and new_driver_name and new_driver_team:
                    try:
                        cursor.execute("INSERT INTO drivers (name, team) VALUES (?, ?)", (new_driver_name, new_driver_team))
                        conn.commit()
                        st.success(f"Coureur {new_driver_name} toegevoegd!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Deze coureur bestaat al.")
            
            st.markdown("---")
            st.subheader("Bestaande Coureurs")
            cursor.execute("SELECT id, name, team FROM drivers")
            all_drivers = cursor.fetchall()
            for d in all_drivers:
                col1, col2 = st.columns([4, 1])
                col1.text(f"{d[1]} ({d[2]})")
                if col2.button("Verwijder", key=f"del_driver_{d[0]}"):
                    cursor.execute("DELETE FROM drivers WHERE id = ?", (d[0],))
                    conn.commit()
                    st.rerun()

        with tab_races:
            st.subheader("Races & Sprintweekenden Beheren")
            
            with st.form("add_race_form"):
                new_race_name = st.text_input("Naam Grand Prix (bijv. Spa GP)")
                new_race_date = st.date_input("Datum")
                is_sprint_race = st.checkbox("Dit is een Sprintweekend")
                add_race_btn = st.form_submit_button("Race Toevoegen")
                
                if add_race_btn and new_race_name:
                    try:
                        cursor.execute("INSERT INTO races (name, date, is_sprint) VALUES (?, ?, ?)", 
                                       (new_race_name, str(new_race_date), 1 if is_sprint_race else 0))
                        conn.commit()
                        st.success(f"Race {new_race_name} toegevoegd!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Deze race bestaat al.")
                        
            st.markdown("---")
            st.subheader("Kalender Overzicht")
            cursor.execute("SELECT id, name, date, is_sprint FROM races")
            all_races = cursor.fetchall()
            for r in all_races:
                col1, col2, col3 = st.columns([3, 2, 1])
                sprint_label = "⚡ Sprint" * bool(r[3])
                col1.text(f"{r[1]} ({r[2]}) {sprint_label}")
                
                # Wissel sprint status direct vanuit beheer
                new_status = col2.checkbox("Sprintweekend", value=bool(r[3]), key=f"sprint_toggle_{r[0]}")
                if new_status != bool(r[3]):
                    cursor.execute("UPDATE races SET is_sprint = ? WHERE id = ?", (int(new_status), r[0]))
                    conn.commit()
                    st.rerun()
                    
                if col3.button("Verwijder", key=f"del_race_{r[0]}"):
                    cursor.execute("DELETE FROM races WHERE id = ?", (r[0],))
                    conn.commit()
                    st.rerun()