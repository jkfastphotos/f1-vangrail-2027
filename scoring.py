def bereken_top5_punten(voorspelling_lijst, uitslag_lijst):
    """
    Berekent punten voor een Top 5 lijst (Race of Kwalificatie) op basis van de afwijking.
    Regel: 25 pt bij exacte voorspelling, aflopend bij afwijking.
    Afwijkingstabel per coureur:
    - 0 verschil (exact): 25 pt
    - 1 verschil: 18 pt
    - 2 verschil: 15 pt
    - 3 t/m 9 verschil: loopt af (bijv. 12, 10, 8, 6, 4, 2, 1 pt, of via een vaste staffel)
    """
    # Voorbeeld staffel op basis van positieverschil per coureur
    staffel = {0: 25, 1: 18, 2: 15, 3: 12, 4: 10, 5: 8, 6: 6, 7: 4, 8: 2, 9: 1}
    totaal_punten = 0

    # Maak een mapping van coureur -> positie in de uitslag (1 t/m 5)
    uitslag_posities = {coureur: pos for pos, coureur in enumerate(uitslag_lijst, start=1)}
    voorspelling_posities = {coureur: pos for pos, coureur in enumerate(voorspelling_lijst, start=1)}

    for coureur, v_pos in voorspelling_posities.items():
        if coureur in uitslag_posities:
            u_pos = uitslag_posities[coureur]
            verschil = abs(v_pos - u_pos)
            totaal_punten += staffel.get(verschil, 0)
        else:
            # Coureur zit niet in de Top 5 van de uitslag
            totaal_punten += 0

    return totaal_punten

def bereken_race_gebeurtenissen(voorspelling, uitslag):
    """
    Berekent punten voor losse categorieën per race.
    """
    punten = 0
    
    # Fastest Lap (20 pt)
    if voorspelling.get('fastest_lap') == uitslag.get('fastest_lap'):
        punten += 20

    # Driver of the Day (10 pt)
    if voorspelling.get('driver_of_the_day') == uitslag.get('driver_of_the_day'):
        punten += 10

    # Failed to Finish / DNF (15 pt per correct voorspelde DNF of totaal aantal)
    # Laten we hier aannemen dat het gaat om de juiste coureurs die uitvallen:
    gedefinieerd_dnf_voorspelling = set(voorspelling.get('dnf_coureurs', []))
    gedefinieerd_dnf_uitslag = set(uitslag.get('dnf_coureurs', []))
    juiste_dnfs = gedefinieerd_dnf_voorspelling.intersection(gedefinieerd_dnf_uitslag)
    punten += len(juiste_dnfs) * 15

    # Head-to-Head (15 pt, eventueel extra bonus bij Max Verstappen)
    h2h_voorspelling = voorspelling.get('h2h_keuzes', {}) # bijv. {'Verstappen_vs_Norris': 'Verstappen'}
    h2h_uitslag = uitslag.get('h2h_uitslagen', {})
    
    for duel, gekozen_coureur in h2h_voorspelling.items():
        if duel in h2h_uitslag and h2h_uitslag[duel] == gekozen_coureur:
            basis_h2h = 15
            # Extra bonuspunten als het om Max Verstappen gaat (bijv. +5 extra punten)
            if 'Verstappen' in gekozen_coureur:
                basis_h2h += 5
            punten += basis_h2h

    return punten

def bereken_seizoen_voorspellingen(voorspelling, uitslag):
    """
    Berekent eenmalige voorspellingen vooraf (Top 10 Kampioenschap & Top 5 Constructeurs).
    Max 50 punten per juiste plek, aflopend naarmate de afwijking groter is.
    """
    punten = 0
    
    # Top 10 Kampioenschap (Coureurs)
    k_staffel = {0: 50, 1: 40, 2: 30, 3: 20, 4: 10, 5: 5} # Voorbeeld staffel voor kampioenschap
    u_coureurs = uitslag.get('kampioenschap_coureurs', [])
    v_coureurs = voorspelling.get('kampioenschap_coureurs', [])
    
    u_pos = {c: i for i, c in enumerate(u_coureurs)}
    for i, c in enumerate(v_coureurs):
        if c in u_pos:
            diff = abs(i - u_pos[c])
            punten += k_staffel.get(diff, 0)

    return punten