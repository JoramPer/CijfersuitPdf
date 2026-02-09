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

def parse_pdf(file):
    all_data = []
    # De kolomkoppen gebaseerd op de brondocument structuur
    columns = ["Naam", "Periode", "netl", "dutl", "entl", "ges", "ak", "wisAB", "wisAC", "maat", "biol", "nat", "schk", "econ", "ckv", "onv", "tek", "gem"]
    
    with pdfplumber.open(file) as pdf:
        current_student = ""
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            
            lines = text.split('\n')
            for line in lines:
                # 1. Zoek naar leerlingnamen (staan vaak bovenaan een blok)
                if "Klas:" in line or "Vergaderlijst" in line or "Pagina" in line:
                    continue
                
                # Check of regel een naam is (geen cijfers, begint met hoofdletter)
                if re.match(r'^[A-Z][a-z]+(\s[A-Z][a-z]+)+$', line.strip()):
                    current_student = line.strip()
                
                # 2. Zoek naar perioderegels (bijv "1 r" of "4 R")
                p_match = re.search(r'(\d)\s+[rR]', line)
                if p_match:
                    p_num = p_match.group(1)
                    if p_num in periodes:
                        # Haal alle getallen uit de regel (cijfers)
                        grades = re.findall(r'\d+,\d+|\d+', line)
                        # Verwijder de periode-indicator uit de gevonden getallen
                        if grades and grades[0] == p_num:
                            grades.pop(0)
                        
                        # Voeg toe aan lijst (hier zou nog kolom-specifieke logica komen)
                        row = [current_student, f"Periode {p_num}"] + grades
                        # Opvullen met 'Leeg' als er minder cijfers zijn dan kolommen
                        row += [""] * (len(columns) - len(row))
                        all_data.append(row[:len(columns)])

    return pd.DataFrame(all_data, columns=columns)

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