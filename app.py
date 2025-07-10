import streamlit as st
import pandas as pd
from sklearn.model_selection import train_test_split
from io import BytesIO

st.set_page_config(page_title="Generador de Marco Muestral", layout="centered")
st.title("📊 Generador de Marco Muestral Equilibrado")

file = st.file_uploader("📂 Sube tu archivo Excel (.xlsx)", type=["xlsx"])

if file:
    df = pd.read_excel(file)

    required_cols = ['ZONA', 'GSE', 'EDAD', 'NOMBRE_GENERO']
    if not all(col in df.columns for col in required_cols):
        st.error("⚠️ El archivo debe tener las columnas: ZONA, GSE, EDAD, NOMBRE_GENERO")
    else:
        # 🧠 Ingreso de rangos de edad personalizados
        rangos_input = st.text_input(
            "Ingresa los rangos de edad que quieres usar (ej: 20-30,31-40,41-60):",
            value="20-33,34-41,42-50"
        )

        def parse_rangos(texto):
            rangos = []
            for r in texto.split(','):
                partes = r.strip().split('-')
                if len(partes) == 2 and partes[0].isdigit() and partes[1].isdigit():
                    inicio, fin = int(partes[0]), int(partes[1])
                    if inicio < fin:
                        rangos.append((inicio, fin))
            return rangos

        rangos_tuplas = parse_rangos(rangos_input)

        def clasificar_rango_personalizado(edad):
            for (inicio, fin) in rangos_tuplas:
                if inicio <= edad <= fin:
                    return f"{inicio}-{fin}"
            return None

        df['RANGO_EDAD_CUSTOM'] = df['EDAD'].apply(clasificar_rango_personalizado)
        df = df[df['RANGO_EDAD_CUSTOM'].notnull()]

        zonas = st.multiselect("Zonas a incluir:", df['ZONA'].unique().tolist(), default=list(df['ZONA'].unique()))
        gses = st.multiselect("GSEs a incluir:", df['GSE'].unique().tolist(), default=list(df['GSE'].unique()))
        generos = st.multiselect("Géneros a incluir:", df['NOMBRE_GENERO'].unique().tolist(), default=list(df['NOMBRE_GENERO'].unique()))
        rangos = sorted(set(df['RANGO_EDAD_CUSTOM']))

        total_objetivo = st.number_input("Número total de casos:", min_value=300, max_value=20000, value=0, step=100)
        partes = st.number_input("¿En cuántas partes deseas dividir la muestra?", min_value=1, max_value=10, value=3, step=1)

        if st.button("Generar muestra"):
            base = df[
                df['ZONA'].isin(zonas) &
                df['GSE'].isin(gses) &
                df['RANGO_EDAD_CUSTOM'].isin(rangos) &
                df['NOMBRE_GENERO'].isin(generos)
            ].copy()

            grupo = base.groupby(['ZONA', 'GSE', 'RANGO_EDAD_CUSTOM', 'NOMBRE_GENERO'])
            proporciones = grupo.size() / grupo.size().sum()
            muestras_por_grupo = (proporciones * total_objetivo).round().astype(int)

            diferencia = total_objetivo - muestras_por_grupo.sum()
            if diferencia != 0:
                muestras_por_grupo[muestras_por_grupo.idxmax()] += diferencia

            muestras = []
            for (zona, gse, rango, genero), n in muestras_por_grupo.items():
                subset = base[
                    (base['ZONA'] == zona) &
                    (base['GSE'] == gse) &
                    (base['RANGO_EDAD_CUSTOM'] == rango) &
                    (base['NOMBRE_GENERO'] == genero)
                ]
                muestras.append(subset.sample(min(n, len(subset)), random_state=42))

            muestra_final = pd.concat(muestras).sample(frac=1, random_state=42).reset_index(drop=True)

            muestra_final['estrato'] = (
                muestra_final['ZONA'] + "_" +
                muestra_final['GSE'] + "_" +
                muestra_final['RANGO_EDAD_CUSTOM'] + "_" +
                muestra_final['NOMBRE_GENERO']
            )

            partes_data = []
            temp = muestra_final.copy()
            for i in range(partes - 1):
                temp, part = train_test_split(temp, test_size=1/(partes - i), stratify=temp['estrato'], random_state=42)
                part.drop(columns='estrato', inplace=True)
                partes_data.append(part)
            temp.drop(columns='estrato', inplace=True)
            partes_data.append(temp)

            def convertir_excel(df):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                return output.getvalue()

            st.success(f"✅ Muestra generada y dividida en {partes} partes.")
            for idx, df_part in enumerate(partes_data):
                st.download_button(
                    label=f"📥 Descargar Parte {idx+1}",
                    data=convertir_excel(df_part),
                    file_name=f"marco_parte_{idx+1}.xlsx"
                )