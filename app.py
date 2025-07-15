if file:
    df = pd.read_excel(file)

    required_cols = ['ZONA', 'GSE', 'EDAD', 'NOMBRE_GENERO']
    if not all(col in df.columns for col in required_cols):
        st.error("⚠️ El archivo debe tener las columnas: ZONA, GSE, EDAD, NOMBRE_GENERO")
    else:
        # ... [MISMO código hasta antes del botón] ...

        # Sección de carga de configuración previa
        st.subheader("📁 Opcional: Cargar configuración de cuotas")
        cuotas_file = st.file_uploader("Sube archivo Excel con cuotas (ZONA, GSE, RANGO_EDAD_CUSTOM, NOMBRE_GENERO, Deseados)", type=["xlsx"], key="cuotas_file")

        base = df[
            df['ZONA'].isin(zonas) &
            df['GSE'].isin(gses) &
            df['RANGO_EDAD_CUSTOM'].isin(rangos) &
            df['NOMBRE_GENERO'].isin(generos)
        ].copy()

        segmentos = base.groupby(['ZONA', 'GSE', 'RANGO_EDAD_CUSTOM', 'NOMBRE_GENERO']).size().reset_index(name='Disponibles')

        if cuotas_file:
            try:
                cuotas_df = pd.read_excel(cuotas_file)
                cuotas_df = cuotas_df.merge(segmentos, on=['ZONA', 'GSE', 'RANGO_EDAD_CUSTOM', 'NOMBRE_GENERO'], how='left')
                cuotas_df['Deseados'] = cuotas_df['Deseados'].fillna(0).astype(int)
                st.success("✅ Configuración de cuotas cargada correctamente.")
            except Exception as e:
                st.error(f"❌ Error al leer archivo de cuotas: {e}")
                cuotas_df = segmentos.copy()
                cuotas_df['Deseados'] = 0
        else:
            cuotas_df = segmentos.copy()
            cuotas_df['Deseados'] = 0

        st.info("✏️ Edita la cantidad de casos deseados por segmento (máximo lo disponible).")
        edited_df = st.data_editor(cuotas_df, num_rows="dynamic")

        # Botón para exportar la configuración
        def convertir_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            return output.getvalue()

        st.download_button(
            label="💾 Descargar configuración de cuotas",
            data=convertir_excel(edited_df[['ZONA', 'GSE', 'RANGO_EDAD_CUSTOM', 'NOMBRE_GENERO', 'Deseados']]),
            file_name="cuotas_configuracion.xlsx"
        )

        total_deseado = edited_df['Deseados'].sum()
        st.markdown(f"**🎯 Total de casos deseados: {total_deseado}**")

        if st.button("🎲 Generar muestra"):
            if total_deseado == 0:
                st.warning("⚠️ Debes asignar al menos un caso en algún segmento.")
            else:
                muestras = []
                for _, row in edited_df.iterrows():
                    if row['Deseados'] > 0:
                        subset = base[
                            (base['ZONA'] == row['ZONA']) &
                            (base['GSE'] == row['GSE']) &
                            (base['RANGO_EDAD_CUSTOM'] == row['RANGO_EDAD_CUSTOM']) &
                            (base['NOMBRE_GENERO'] == row['NOMBRE_GENERO'])
                        ]
                        n = min(int(row['Deseados']), len(subset))
                        muestras.append(subset.sample(n, random_state=42))

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

                st.success(f"✅ Muestra generada con {total_deseado} casos y dividida en {partes} partes.")
                for idx, df_part in enumerate(partes_data):
                    st.download_button(
                        label=f"📥 Descargar Parte {idx+1}",
                        data=convertir_excel(df_part),
                        file_name=f"marco_parte_{idx+1}.xlsx"
                    )
