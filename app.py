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
periodes = st.sidebar.multiselect(
    "Welke periodes exporteren?", 
    ['1', '2', '3', '4'], 
    default=['1', '2', '3', '4']
)

uploaded_file = st.file_uploader("Kies een PDF bestand", type="pdf")

def parse_pdf(file, geselecteerde_periodes):
    all_data = []
    # Definieer alle mogelijke kolommen
    vakken_master = ["netl", "dutl", "entl", "ges", "ak", "wisAB", "wisAC", "maat", "biol", "nat", "schk", "econ", "c&kv"]
    
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            # We halen de woorden op inclusief hun x-positie (horizontaal)
            words = page.extract_words()
            
            # 1. Zoek de koppen op deze specifieke pagina om de x-coördinaten te bepalen
            header_positions = {}
            for v in vakken_master:
                match = next((w for w in words if v in w['text'].lower()), None)
                if match:
                    header_positions[v] = (match['x0'], match['x1'])

            # 2. Verwerk de regels
            lines = page.extract_text().split('\n')
            current_student = ""
            
            for line in lines:
                # Naam herkenning
                if re.match(r'^[A-Z][a-z]+(\s[A-Z][a-z]+)+$', line.strip()):
                    current_student = line.strip()
                    continue
                
                # Periode check
                p_match = re.search(r'(\d)\s+[rR]', line)
                if p_match and p_match.group(1) in geselecteerde_periodes:
                    # Hier gebeurt de magie: we pakken de getallen van deze specifieke regel
                    # en kijken naar hun positie op de pagina t.o.v. de headers
                    line_words = [w for w in words if w['top'] > (p_match_y_coord - 5) and w['top'] < (p_match_y_coord + 5)]
                    
                    row = {"Naam": current_student, "Periode": p_match.group(1)}
                    for v in vakken_master:
                        # Zoek een getal dat horizontaal ongeveer onder de header staat
                        if v in header_positions:
                            h_x0, h_x1 = header_positions[v]
                            cijfer = next((w['text'] for w in line_words if abs(w['x0'] - h_x0) < 10), "")
                            row[v] = cijfer
                    
                    all_data.append(row)
    
    return pd.DataFrame(all_data)

if uploaded_file:
    with st.spinner('Bezig met verwerken...'):
        df = parse_pdf(uploaded_file)
        
        if not df.empty:
            st.success(f"{len(df)} regels gevonden!")
            st.dataframe(df) # Toon voorbeeld in de browser
            
            # CSV download knop
            csv = df.to_csv(index=False, sep=';').encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="cijferlijst_geëxporteerd.csv",
                mime="text/csv",
            )
        else:
            st.warning("Geen data gevonden. Controleer of het format van de PDF klopt.")
