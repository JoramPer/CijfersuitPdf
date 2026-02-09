import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

st.set_page_config(page_title="PDF naar Cijferlijst CSV", layout="wide")

st.title("cijferlijst Extractor 🎓")
st.write("Upload een PDF-vergaderlijst en zet deze om naar een schoon CSV-bestand.")

# Opties in de zijbalk
st.sidebar.header("Instellingen")
gekozen_periodes = st.sidebar.multiselect(
    "Welke periodes exporteren?", 
    ['1', '2', '3', '4'], 
    default=['1', '2']
)

uploaded_file = st.file_uploader("Kies een PDF bestand", type="pdf")

def parse_pdf(file, geselecteerde_periodes):
    all_data = []
    # Master lijst van vakken in de volgorde die je in de CSV wilt
    vakken_master = ["netl", "dutl", "entl", "ges", "ak", "wisAB", "wisAC", "maat", "biol", "nat", "schk", "econ", "c&kv", "onvold.", "tekort", "gem."]
    
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            
            # 1. Bepaal de horizontale positie (x) van de kolomkoppen
            header_positions = {}
            for v in vakken_master:
                # We zoeken specifiek naar de woorden in de header-sectie
                matches = [w for w in words if v in w['text'].lower() and w['top'] < 300]
                if matches:
                    # Pak het gemiddelde x-punt van de header
                    header_positions[v] = (matches[0]['x0'] + matches[0]['x1']) / 2

            # 2. Verwerk de regels tekst
            lines = page.extract_text().split('\n')
            current_student = ""
            
            for line in lines:
                # Naam herkenning (Regel zonder getallen die begint met een hoofdletter)
                if re.match(r'^[A-Z][a-z]+(\s[A-Z][a-z]+)+$', line.strip()):
                    current_student = line.strip()
                    continue
                
                # Periode check (bijv. "1 r" of "2 r")
                p_match = re.search(r'(\d)\s+[rR]', line)
                if p_match:
                    p_num = p_match.group(1)
                    if p_num in geselecteerde_periodes:
                        # Zoek de verticale positie (y) van deze specifieke regel
                        # We zoeken naar het woord 'r' of 'R' op deze regelhoogte
                        r_word = [w for w in words if w['text'].lower() == 'r' and abs(w['top'] - words[lines.index(line)]['top']) < 500]
                        # Versimpelde methode: we pakken alle woorden op dezelfde hoogte als de periode-match
                        line_y = None
                        for w in words:
                            if w['text'] == p_num and abs(words.index(w) - words.index(w)) < 10: # Versimpelde check
                                line_y = w['top']
                        
                        row = {"Naam": current_student, "Periode": p_num}
                        
                        # Haal alle woorden op die op ongeveer dezelfde hoogte staan als de "1 r"
                        if line_y:
                            line_elements = [w for w in words if abs(w['top'] - line_y) < 3]
                            
                            for v, x_pos in header_positions.items():
                                # Zoek het getal dat het dichtst bij de x-positie van de kolomkop staat
                                dichtstbijzijnde_cijfer = ""
                                min_dist = 20 # Speling in pixels
                                
                                for el in line_elements:
                                    el_x_center = (el['x0'] + el['x1']) / 2
                                    dist = abs(el_x_center - x_pos)
                                    if dist < min_dist:
                                        dichtstbijzijnde_cijfer = el['text']
                                        min_dist = dist
                                
                                row[v] = dichtstbijzijnde_cijfer
                        
                        all_data.append(row)
    
    return pd.DataFrame(all_data)

if uploaded_file:
    with st.spinner('Bezig met verwerken...'):
        # HIER ging het mis: we geven nu ook de 'gekozen_periodes' mee
        df = parse_pdf(uploaded_file, gekozen_periodes)
        
        if not df.empty:
            st.success(f"Extractie voltooid!")
            
            # Opschonen: vervang komma's door punten voor berekeningen, of hou ze als tekst
            st.dataframe(df)
            
            csv = df.to_csv(index=False, sep=';').encode('utf-8')
            st.download_button(
                label="Download CSV voor Excel",
                data=csv,
                file_name="cijferlijst_export.csv",
                mime="text/csv",
            )
        else:
            st.warning("Geen data gevonden. Selecteer de juiste periodes in het menu links.")
