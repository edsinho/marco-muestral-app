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
        cuotas_df.to_excel(writer, sheet_name="Cuotas", index=False)
        reglas_df.to_excel(writer, sheet_name="Reglas", index=False)
    return output.getvalue()

def guardar_grafico_barras(df, x_col, y_col, titulo, filename):
    fig, ax = plt.subplots()
    df.groupby(x_col)[y_col].sum().plot(kind='bar', ax=ax, color='skyblue')
    ax.set_title(titulo)
    ax.set_ylabel(y_col)
    plt.xticks(rotation=45)
    fig.tight_layout()
    plt.savefig(filename)
    plt.close(fig)

def generar_pdf_informe(cuotas_df, reglas_df):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        doc = SimpleDocTemplate(tmpfile.name, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("📊 Informe de Cuotas y Reglas", styles['Title']))
        elements.append(Spacer(1, 12))

        resumen = cuotas_df.groupby("ZONA")["Deseados"].sum().reset_index()
        data_cuotas = [resumen.columns.to_list()] + resumen.values.tolist()
        elements.append(Paragraph("Totales por Zona:", styles['Heading2']))
        elements.append(Table(data_cuotas))
        elements.append(Spacer(1, 12))

        if not reglas_df.empty:
            data_reglas = [reglas_df.columns.to_list()] + reglas_df.astype(str).values.tolist()
            elements.append(Paragraph("Reglas Globales Aplicadas:", styles['Heading2']))
            elements.append(Table(data_reglas))
            elements.append(Spacer(1, 12))

        charts = [
            ("ZONA", "Deseados", "Casos por Zona", "zona_chart.png"),
            ("GSE", "Deseados", "Casos por GSE", "gse_chart.png"),
            ("RANGO_EDAD_CUSTOM", "Deseados", "Casos por Rango de Edad", "edad_chart.png"),
            ("NOMBRE_GENERO", "Deseados", "Casos por Género", "genero_chart.png"),
        ]

        for x, y, title, fname in charts:
            guardar_grafico_barras(cuotas_df, x, y, title, fname)
            elements.append(Paragraph(title, styles['Heading3']))
            elements.append(Image(fname, width=400, height=200))
            elements.append(Spacer(1, 12))

        doc.build(elements)
        tmpfile.seek(0)
        return tmpfile.read()

# --- Interfaz Streamlit ---
file = st.file_uploader("📂 Sube tu archivo Excel (.xlsx)", type=["xlsx"])

if file:
    df = pd.read_excel(file)
    required_cols = ['ZONA', 'GSE', 'EDAD', 'NOMBRE_GENERO']
    if not all(col in df.columns for col in required_cols):
        st.error("⚠️ El archivo debe tener las columnas: ZONA, GSE, EDAD, NOMBRE_GENERO")
    else:
        rangos_input = st.text_input("🎯 Rangos de edad (ej: 20-33,34-41,42-50):", value="20-33,34-41,42-50")
        rangos_tuplas = parse_rangos(rangos_input)
        df['RANGO_EDAD_CUSTOM'] = df['EDAD'].apply(lambda e: clasificar_rango_personalizado(e, rangos_tuplas))
        df = df[df['RANGO_EDAD_CUSTOM'].notnull()]

        zonas = st.multiselect("Zonas a incluir:", df['ZONA'].unique().tolist(), default=list(df['ZONA'].unique()))
        gses = st.multiselect("GSEs a incluir:", df['GSE'].unique().tolist(), default=list(df['GSE'].unique()))
        generos = st.multiselect("Géneros a incluir:", df['NOMBRE_GENERO'].unique().tolist(), default=list(df['NOMBRE_GENERO'].unique()))
        partes = st.number_input("¿En cuántas partes deseas dividir la muestra?", min_value=1, max_value=10, value=3)

        base = df[
            df['ZONA'].isin(zonas) &
            df['GSE'].isin(gses) &
            df['NOMBRE_GENERO'].isin(generos)
        ].copy()

        segmentos = base.groupby(['ZONA', 'GSE', 'RANGO_EDAD_CUSTOM', 'NOMBRE_GENERO']).size().reset_index(name='Disponibles')

        st.subheader("📁 Cargar configuración completa (opcional)")
        config_file = st.file_uploader("Archivo Excel con hojas 'Cuotas' y 'Reglas'", type=["xlsx"], key="config")

        if config_file:
            try:
                cuotas_df = pd.read_excel(config_file, sheet_name="Cuotas")
                reglas_data = pd.read_excel(config_file, sheet_name="Reglas")
                cuotas_df = cuotas_df.merge(segmentos, on=['ZONA', 'GSE', 'RANGO_EDAD_CUSTOM', 'NOMBRE_GENERO'], how='left')
                cuotas_df['Deseados'] = cuotas_df['Deseados'].fillna(0).astype(int)
                st.success("✅ Configuración cargada.")
            except Exception as e:
                st.error(f"❌ Error al leer configuración: {e}")
                cuotas_df = segmentos.copy()
                cuotas_df['Deseados'] = 0
                reglas_data = pd.DataFrame(columns=["Variable", "Valor", "Regla", "Porcentaje"])
        else:
            cuotas_df = segmentos.copy()
            cuotas_df['Deseados'] = 0
            reglas_data = pd.DataFrame(columns=["Variable", "Valor", "Regla", "Porcentaje"])

        st.info("✏️ Edita la cantidad deseada por segmento")
        edited_df = st.data_editor(cuotas_df, num_rows="dynamic")

        st.subheader("⚙️ Límites automáticos por segmento")
        cuota_min = st.number_input("✅ Mínimo por segmento:", min_value=0, value=0)
        cuota_max = st.number_input("🚫 Máximo por segmento:", min_value=0, value=0)

        if cuota_min > 0:
            edited_df['Deseados'] = edited_df.apply(
                lambda row: max(row['Deseados'], cuota_min) if row['Disponibles'] >= cuota_min else row['Deseados'],
                axis=1)

        if cuota_max > 0:
            edited_df['Deseados'] = edited_df.apply(
                lambda row: min(row['Deseados'], cuota_max), axis=1)

        edited_df['Deseados'] = edited_df.apply(
            lambda row: min(row['Deseados'], row['Disponibles']), axis=1
        )

        st.subheader("⚖️ Reglas globales de porcentaje")
        reglas_data = st.data_editor(reglas_data, use_container_width=True, key="reglas_editor", num_rows="dynamic")
        total_casos_actual = edited_df['Deseados'].sum()

        for _, regla in reglas_data.iterrows():
            var = regla['Variable']
            val = regla['Valor']
            tipo = regla['Regla']
            pct = regla['Porcentaje']
            if pct <= 0 or pct > 100 or var not in edited_df.columns:
                continue
            casos_necesarios = round((pct / 100) * total_casos_actual)
            filtro = edited_df[edited_df[var] == val]
            actuales = filtro['Deseados'].sum()
            diferencia = casos_necesarios - actuales

            if tipo == 'mínimo' and diferencia > 0:
                for idx in filtro.index:
                    disp = edited_df.at[idx, 'Disponibles']
                    actual = edited_df.at[idx, 'Deseados']
                    agregar = min(diferencia, disp - actual)
                    edited_df.at[idx, 'Deseados'] += agregar
                    diferencia -= agregar
                    if diferencia <= 0: break

            elif tipo == 'máximo' and diferencia < 0:
                for idx in filtro.index:
                    actual = edited_df.at[idx, 'Deseados']
                    reducir = min(abs(diferencia), actual)
                    edited_df.at[idx, 'Deseados'] -= reducir
                    diferencia += reducir
                    if diferencia >= 0: break

        st.markdown(f"🎯 **Total final: {edited_df['Deseados'].sum()} casos**")

        st.subheader("📊 Visualización")
        for var in ['ZONA', 'GSE', 'RANGO_EDAD_CUSTOM', 'NOMBRE_GENERO']:
            fig = px.bar(edited_df.groupby(var)['Deseados'].sum().reset_index(), x=var, y='Deseados', title=f'Casos por {var}')
            st.plotly_chart(fig, use_container_width=True)

        st.download_button("📅 Descargar configuración completa", convertir_excel_config(edited_df, reglas_data), "configuracion_completa.xlsx")

        if st.button("🎲 Generar muestra"):
            muestras = []
            for _, row in edited_df.iterrows():
                try:
                    n = int(row['Deseados'])
                    if n > 0:
                        subset = base[
                            (base['ZONA'] == row['ZONA']) &
                            (base['GSE'] == row['GSE']) &
                            (base['RANGO_EDAD_CUSTOM'] == row['RANGO_EDAD_CUSTOM']) &
                            (base['NOMBRE_GENERO'] == row['NOMBRE_GENERO'])
                        ]
                        if not subset.empty:
                            if len(subset) >= n:
                                muestras.append(subset.sample(n, random_state=42))
                            else:
                                st.warning(f"⚠️ Solo hay {len(subset)} casos disponibles para: {row['ZONA']}, {row['GSE']}, {row['RANGO_EDAD_CUSTOM']}, {row['NOMBRE_GENERO']}. Se incluirán todos.")
                                muestras.append(subset)
                        else:
                            st.warning(f"⚠️ No hay casos disponibles para: {row['ZONA']}, {row['GSE']}, {row['RANGO_EDAD_CUSTOM']}, {row['NOMBRE_GENERO']}")
                except Exception as e:
                    st.error(f"Error al procesar segmento: {e}")

            if muestras:
                muestra_final = pd.concat(muestras).sample(frac=1, random_state=42).reset_index(drop=True)
                muestra_final['estrato'] = (
                    muestra_final['ZONA'] + "_" + muestra_final['GSE'] +
                    "_" + muestra_final['RANGO_EDAD_CUSTOM'] + "_" + muestra_final['NOMBRE_GENERO']
                )

                partes_data = []
                temp = muestra_final.copy()
                for i in range(partes - 1):
                    temp, part = train_test_split(temp, test_size=1/(partes - i), stratify=temp['estrato'], random_state=42)
                    part.drop(columns='estrato', inplace=True)
                    partes_data.append(part)
                temp.drop(columns='estrato', inplace=True)
                partes_data.append(temp)

                for idx, df_part in enumerate(partes_data):
                    st.download_button(f"📅 Descargar Parte {idx+1}", convertir_excel_config(df_part, pd.DataFrame()), f"marco_parte_{idx+1}.xlsx")
            else:
                st.error("❌ No se pudo generar muestra: ningún segmento válido.")

        st.subheader("🧾 Informe PDF")
        pdf_bytes = generar_pdf_informe(edited_df, reglas_data)
        st.download_button("📄 Descargar Informe PDF", data=pdf_bytes, file_name="informe_muestra.pdf", mime="application/pdf")
