import streamlit as st
import sqlite3

# Pagina configuratie
st.set_page_config(page_title="F1 Vangrail - FastLine 2026", layout="wide")

# --- DATABASE INITIALISATIE ---
def init_db():
    conn = sqlite3.connect('f1_poule.db')
    cursor = conn.cursor()
    
    # 1. Gebruikers-tabel
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            inleg_paid BOOLEAN DEFAULT 0
        )
    ''')
    
    # 2. Voorspellingen-tabel
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            grand_prix TEXT,
            p1 TEXT,
            p2 TEXT,
            p3 TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 3. Scores-tabel voor het klassement
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            grand_prix TEXT,
            points INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Functie om gebruiker op te slaan/ophalen
def get_or_create_user(name):
    conn = sqlite3.connect('f1_poule.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (name) VALUES (?)', (name,))
    conn.commit()
    cursor.execute('SELECT id, name, inleg_paid FROM users WHERE name = ?', (name,))
    user = cursor.fetchone()
    conn.close()
    return user

# Functie om voorspelling op te slaan
def save_prediction(user_id, gp, p1, p2, p3):
    conn = sqlite3.connect('f1_poule.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM predictions WHERE user_id = ? AND grand_prix = ?
    ''', (user_id, gp))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute('''
            UPDATE predictions SET p1 = ?, p2 = ?, p3 = ? WHERE user_id = ? AND grand_prix = ?
        ''', (p1, p2, p3, user_id, gp))
    else:
        cursor.execute('''
            INSERT INTO predictions (user_id, grand_prix, p1, p2, p3) VALUES (?, ?, ?, ?, ?)
        ''', (user_id, gp, p1, p2, p3))
        
    conn.commit()
    conn.close()

# Functie om alle voorspellingen op te halen voor een GP
def get_all_predictions_for_gp(grand_prix):
    conn = sqlite3.connect('f1_poule.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.name, p.p1, p.p2, p.p3 
        FROM predictions p
        JOIN users u ON p.user_id = u.id
        WHERE p.grand_prix = ?
    ''', (grand_prix,))
    results = cursor.fetchall()
    conn.close()
    return results

# Functie om alle gebruikers op te halen
def get_all_users():
    conn = sqlite3.connect('f1_poule.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, inleg_paid FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

# Functie om betaalstatus te updaten
def update_inleg_status(user_id, status):
    conn = sqlite3.connect('f1_poule.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET inleg_paid = ? WHERE id = ?', (status, user_id))
    conn.commit()
    conn.close()

# --- STREAMLIT INTERFACE ---
def main():
    st.title("🏎️ F1 Vangrail - FastLine 2026")

    # Sessie beheer voor login
    if 'user' not in st.session_state:
        st.session_state['user'] = None

    if st.session_state['user'] is None:
        st.markdown("### Inloggen / Deelnemen")
        username_input = st.text_input("Vul je voornaam of nickname in:")
        
        if st.button("Start met voorspellen"):
            if username_input.strip() != "":
                user_data = get_or_create_user(username_input.strip())
                st.session_state['user'] = {
                    'id': user_data[0],
                    'name': user_data[1],
                    'inleg_paid': user_data[2]
                }
                st.success(f"Welkom, {user_data[1]}! Je bent ingelogd.")
                st.rerun()
            else:
                st.warning("Voer alstublieft een geldige naam in.")
        return

    # Als de gebruiker is ingelogd, tonen we de navigatie-tabbladen
    user = st.session_state['user']
    st.sidebar.markdown(f"👤 Ingelogd als: **{user['name']}**")
    if st.sidebar.button("Uitloggen"):
        st.session_state['user'] = None
        st.rerun()

    # Tabbladen structuur
    tab1, tab2, tab3 = st.tabs(["✍️ Voorspellen", "🏆 Klassement & Uitslagen", "💰 Inleg & Deelnemers"])

    # --- TAB 1: VOORSPELLEN ---
    with tab1:
        st.subheader("🎯 Grand Prix Voorspelling Indienen")
        
        gp_list = ["Bahrein GP", "Saoedi-Arabië GP", "Australië GP", "Japan GP", "China GP", "Miami GP"]
        selected_gp = st.selectbox("Selecteer Grand Prix", gp_list)
        
        coureurs = [
            "Max Verstappen", "Lando Norris", "Charles Leclerc", "Oscar Piastri",
            "Lewis Hamilton", "George Russell", "Carlos Sainz", "Fernando Alonso",
            "Sergio Perez", "Alexander Albon", "Kimi Antonelli", "Liam Lawson"
        ]
        
        with st.form("prediction_form"):
            st.write(f"Voorspel de Top 3 voor de **{selected_gp}**:")
            p1 = st.selectbox("P1 (Winnaar)", coureurs)
            p2 = st.selectbox("P2", coureurs)
            p3 = st.selectbox("P3", coureurs)
            
            submit_button = st.form_submit_button("Voorspelling Opslaan")
            
            if submit_button:
                if p1 == p2 or p1 == p3 or p2 == p3:
                    st.error("⚠️ Je kunt niet dezelfde coureur op meerdere podiumplekken zetten!")
                else:
                    save_prediction(user['id'], selected_gp, p1, p2, p3)
                    st.success("Je voorspelling is succesvol opgeslagen!")

    # --- TAB 2: KLASSEMENT & UITSLAGEN ---
    with tab2:
        st.subheader("🏆 Klassement & Weekend Uitslagen")
        
        gp_list = ["Bahrein GP", "Saoedi-Arabië GP", "Australië GP", "Japan GP", "China GP", "Miami GP"]
        selected_gp_view = st.selectbox("Bekijk voorspellingen voor GP:", gp_list, key="view_gp")
        
        st.markdown(f"### Voorspellingen voor de {selected_gp_view}")
        predictions = get_all_predictions_for_gp(selected_gp_view)
        
        if not predictions:
            st.info("Er zijn voor deze Grand Prix nog geen voorspellingen ingediend.")
        else:
            for pred in predictions:
                name, p1, p2, p3 = pred
                st.write(f"👤 **{name}** ➔ 🥇 {p1} | 🥈 {p2} | 🥉 {p3}")

        st.markdown("---")
        st.subheader("📊 Totaal Stand (Seizoen)")
        st.info("Het puntenklassement wordt automatisch bijgewerkt zodra de race-uitslagen door de beheerder zijn ingevoerd.")

    # --- TAB 3: INLEG & DEELNEMERS ---
    with tab3:
        st.subheader("💰 Overzicht Inleg & Deelnemers")
        st.write("Hier zie je alle deelnemers en of de inleg reeds voldaan is.")
        
        users = get_all_users()
        for u in users:
            u_id, u_name, u_paid = u
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"👤 **{u_name}**")
            with col2:
                new_status = st.checkbox("Betaald", value=bool(u_paid), key=f"paid_{u_id}")
                if new_status != bool(u_paid):
                    update_inleg_status(u_id, int(new_status))
                    st.rerun()

if __name__ == '__main__':
    main()
