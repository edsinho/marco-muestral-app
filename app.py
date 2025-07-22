
import streamlit as st
import pandas as pd
from sklearn.model_selection import train_test_split
from io import BytesIO
import plotly.express as px
import matplotlib.pyplot as plt
import tempfile
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Generador de Marco Muestral", layout="centered")
st.title("📊 Generador de Marco Muestral Equilibrado")

# --- Funciones ---
def parse_rangos(texto):
    rangos = []
    for r in texto.split(','):
        partes = r.strip().split('-')
        if len(partes) == 2 and partes[0].isdigit() and partes[1].isdigit():
            inicio, fin = int(partes[0]), int(partes[1])
            if inicio < fin:
                rangos.append((inicio, fin))
    return rangos

def clasificar_rango_personalizado(edad, rangos_tuplas):
    for (inicio, fin) in rangos_tuplas:
        if inicio <= edad <= fin:
            return f"{inicio}-{fin}"
    return None

def convertir_excel_config(cuotas_df, reglas_df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        cuotas_df.to_excel(writer, sheet_name="Cuotas", index=Fa_
