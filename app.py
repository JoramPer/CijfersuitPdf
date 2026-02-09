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
    # De exacte koppen uit jouw PDF
    vakken_master = ["netl", "dutl", "entl", "ges", "ak", "wisAB", "wisAC", "maat", "biol", "nat", "schk", "econ", "c&kv", "onvold.", "tekort", "gem."]
    
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            
            # 1. Bepaal het horizontale bereik (x0 tot x1) van elke kolomkop
            header_ranges = {}
            for v in vakken_master:
                # We zoeken de koppen in het bovenste gedeelte van de pagina
                matches = [w for w in words if v in w['text'].lower() and w['top'] < 350]
                if matches:
                    # We slaan de begin- en eindpositie van het woord op
                    header_ranges[v] = (matches[0]['x0'] - 5, matches[0]['x1'] + 5)

            # 2. Haal de tekstregels op
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
                    p_num = p_match.group(1)
                    
                    # Vind de y-positie van deze specifieke regel tekst
                    # We zoeken een woord op deze regel om de hoogte te bepalen
                    line_text_parts = line.split()
                    sample_word = line_text_parts[-1] # Pak het laatste getal (gemiddelde)
                    
                    # Zoek dit specifieke woord in de 'words' lijst van de PDF
                    matching_words = [w for w in words if w['text'] == sample_word and w['top'] > 100]
                    if not matching_words: continue
                    
                    # Pak de hoogte van de regel
                    line_y = matching_words[0]['top']
                    line_elements = [w for w in words if abs(w['top'] - line_y) < 5]
                    
                    row = {"Naam": current_student, "Periode": p_num}
                    
                    for v, (x0, x1) in header_ranges.items():
                        # Zoek een element dat horizontaal "overlap" heeft met de header
                        cijfer = ""
                        for el in line_elements:
                            el_center = (el['x0'] + el['x1']) / 2
                            # Als het midden van het cijfer tussen de x0 en x1 van de header valt
                            if x0 <= el_center <= x1:
                                cijfer = el['text']
                                break
                        row[v] = cijfer
                    
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
