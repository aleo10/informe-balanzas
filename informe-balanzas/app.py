import base64
import json
import os
import random
import datetime
import pandas as pd
import streamlit as st

from database import (get_clientes, get_cliente_info, get_balanzas_de_cliente, get_balanza_info,
                       update_precintos, get_config, update_config, add_cliente, add_balanza,
                       update_cliente, update_balanza, parse_cliente_key)
from weight_rules import get_weight_config, get_excentricidad_camiones
from pdf_generator import generate_pdf, generate_informe_servicio
from report_counter import get_next_number, save_number

PREFS_PATH = os.path.join(os.path.dirname(__file__), "data", "prefs.json")


def load_prefs() -> dict:
    if os.path.exists(PREFS_PATH):
        with open(PREFS_PATH) as f:
            return json.load(f)
    return {"cert_pesas": ""}


def save_prefs(prefs: dict):
    os.makedirs(os.path.dirname(PREFS_PATH), exist_ok=True)
    with open(PREFS_PATH, "w") as f:
        json.dump(prefs, f)


# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Informe de Calibración", page_icon="⚖️", layout="wide")

# ── LOGIN ─────────────────────────────────────────────────────────────────────
if not st.session_state.get("autenticado"):
    st.title("⚖️ Generador de Informes de Calibración")
    st.subheader("Iniciar sesión")
    pwd = st.text_input("Contraseña", type="password")
    if st.button("Ingresar", type="primary"):
        if pwd == st.secrets["app"]["password"]:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.stop()

st.title("⚖️ Generador de Informes de Calibración")

# Barra de acciones rápidas (botones duplicados arriba)
_top_btn, _top_d1, _top_d2 = st.columns([2, 2, 2])
with _top_btn:
    _top_generate = st.button("📄 Generar documentos", type="primary",
                               use_container_width=True, key="gen_top")
with _top_d1:
    if "docs_is_bytes" in st.session_state:
        st.download_button(
            label="⬇️ Descargar Informe de Servicio",
            data=st.session_state["docs_is_bytes"],
            file_name=st.session_state["docs_is_name"],
            mime="application/pdf",
            key="dl_is_top",
        )
with _top_d2:
    if st.session_state.get("docs_hacer_ensayo") and st.session_state.get("docs_if_bytes"):
        st.download_button(
            label="⬇️ Descargar Informe de Ensayo",
            data=st.session_state["docs_if_bytes"],
            file_name=st.session_state["docs_if_name"],
            mime="application/pdf",
            key="dl_if_top",
        )

st.divider()

prefs = load_prefs()

# ── 1. DATOS GENERALES ───────────────────────────────────────────────────────
st.header("1. Datos generales")
col1, col2, col3 = st.columns(3)
with col1:
    fecha = st.date_input("Fecha", value=datetime.date.today())
with col2:
    nro_is_default = get_next_number("IS")
    nro_is = st.number_input("N° Informe de Servicio (IS)", min_value=1, value=nro_is_default, step=1)
with col3:
    nro_if_default = get_next_number("IF")
    nro_if = st.number_input("N° Informe de Ensayo (IF)", min_value=1, value=nro_if_default, step=1)

st.divider()

# ── 2. CLIENTE Y BALANZA ─────────────────────────────────────────────────────
st.header("2. Cliente y Balanza")
clientes = get_clientes()
_lista = bool(clientes)

if not clientes:
    st.warning("No hay clientes cargados aún. Usá la sección '🗄️ Base de Datos' al final de la página para agregar.")

if _lista:
    cliente_sel = st.selectbox("Cliente", clientes)
    cliente_info = get_cliente_info(cliente_sel)
    st.write(f"**Dirección:** {cliente_info.get('direccion', '')}  |  **Localidad:** {cliente_info.get('localidad', '')}")

    balanzas = get_balanzas_de_cliente(cliente_sel)
    if not balanzas:
        st.warning("Este cliente no tiene balanzas en la base de datos.")
        _lista = False

if _lista:
    balanza_sel = st.selectbox("Balanza (Código interno)", balanzas)
    b = get_balanza_info(balanza_sel)

    if b:
        col_b1, col_b2, col_b3, col_b4 = st.columns(4)
        col_b1.metric("Tipo", b["tipo_balanza"])
        col_b2.metric("Cap. Máx", f"{b['cap_max']} kg")
        col_b3.metric("Div. Mín", f"{b['div_min']} kg")
        col_b4.metric("Ult. Verificación", b["ult_verificacion"] or "—")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Indicador**")
            st.write(f"Marca: {b['marca']}  |  Modelo: {b['mod_indicador']}  |  "
                     f"N° Serie: {b['n_serie_indicador']}  |  Cod. Aprob.: {b['cod_aprobacion_indicador']}")
        with c2:
            st.markdown("**Plataforma**")
            st.write(f"Tipo: {b['plataforma']}  |  Medidas: {b['medidas']}  |  "
                     f"N° Serie: {b['n_serie_plataforma']}  |  Cod. Aprob.: {b['cod_aprobacion_plataforma']}")

        st.write(f"**Ubicación:** {b['ubicacion']}  |  **Cod. Interno:** {b['cod_interno']}")

        st.markdown("**Precintos**")
        st.caption("Si se reemplazaron precintos, editá los valores nuevos. Al generar el PDF se actualizará la base de datos automáticamente.")
        pc1, pc2 = st.columns(2)
        with pc1:
            st.markdown("*Parte base del Instrumento*")
            nuevo_vig_plataforma = st.text_input(
                "Precintos vigentes (plataforma)",
                value=b["precintos_vig_plataforma"],
                key=f"prec_vig_plat_{balanza_sel}"
            )
        with pc2:
            st.markdown("*Indicador Electrónico*")
            nuevo_vig_indicador = st.text_input(
                "Precintos vigentes (indicador)",
                value=b["precintos_vig_indicador"],
                key=f"prec_vig_ind_{balanza_sel}"
            )

        plat_cambio = nuevo_vig_plataforma.strip() != b["precintos_vig_plataforma"].strip()
        ind_cambio  = nuevo_vig_indicador.strip()  != b["precintos_vig_indicador"].strip()
        precintos_cambiados = plat_cambio or ind_cambio
        if precintos_cambiados:
            st.warning("⚠️ Los precintos fueron modificados. Al generar el PDF se actualizará la base de datos.")

        cap_max   = float(b.get("cap_max", 100) or 100)
        tipo      = b.get("tipo_balanza", "")
        es_camion = "camion" in tipo.lower()
        div_min   = float(b.get("div_min", 1) or 1)
        apoyos_db = int(b.get("apoyos") or 4) if b.get("apoyos") else 4

        # ── 3. INFORME DE SERVICIO ────────────────────────────────────────────────────
        st.header("3. Informe de Servicio")
        resumen_falla       = st.text_area("Resumen de la Falla", value="Control de peso", height=80)
        trabajos_realizados = st.text_area("Trabajos Realizados", value="Limpieza y control", height=80)
        resultado_servicio  = st.text_area("Resultado / Recomendaciones",
                                           value="La balanza se encuentra operativa.", height=60)

        # ── 4. INFORME DE ENSAYO ──────────────────────────────────────────────────────
        st.header("4. Informe de Ensayo")
        hacer_ensayo = st.checkbox("¿Se realizaron ensayos? (genera Informe de Ensayo)", value=True)

        if hacer_ensayo:

            # ── 4a. PESAS Y CARGA ────────────────────────────────────────────────────
            st.subheader("Pesas y Carga de Ensayo")

            wc = get_weight_config(tipo, cap_max)

            if wc["user_chooses_load"]:
                carga_elegida = st.number_input(
                    "Carga máxima de ensayo (kg)",
                    min_value=int(wc["pesa_kg"]),
                    max_value=int(cap_max),
                    value=int(wc["carga_max_kg"]),
                    step=20 if es_camion else int(wc["pesa_kg"]),
                    key=f"carga_elegida_{balanza_sel}",
                )
                wc = get_weight_config(tipo, cap_max, carga_elegida_kg=carga_elegida)

            col_p1, col_p2, col_p3 = st.columns(3)
            col_p1.metric("Pesa unitaria", f"{wc['pesa_kg']} kg")
            col_p2.metric("Carga máxima ensayo", f"{wc['carga_max_kg']} kg")
            col_p3.metric("Pasos de linealidad", len(wc["linealidad_cargas"]))

            cfg = get_config()
            st.markdown("**Certificados de pesas**")
            with st.form("form_certificados"):
                cc1, cc2 = st.columns(2)
                with cc1:
                    st.caption("🔵 Pesas pequeñas")
                    cfg_desc_peq  = st.text_input("Descripción", value=cfg.get("desc_pesas_pequenas", ""), key="cfg_desc_peq")
                    cfg_cert_peq  = st.text_input("N° Certificado", value=cfg.get("cert_pesas_pequenas", ""), key="cfg_cert_peq")
                with cc2:
                    st.caption("🟠 Pesas grandes")
                    cfg_desc_gran = st.text_input("Descripción", value=cfg.get("desc_pesas_grandes", ""), key="cfg_desc_gran")
                    cfg_cert_gran = st.text_input("N° Certificado", value=cfg.get("cert_pesas_grandes", ""), key="cfg_cert_gran")
                if st.form_submit_button("💾 Guardar certificados"):
                    update_config("desc_pesas_pequenas", cfg_desc_peq)
                    update_config("cert_pesas_pequenas", cfg_cert_peq)
                    update_config("desc_pesas_grandes",  cfg_desc_gran)
                    update_config("cert_pesas_grandes",  cfg_cert_gran)
                    st.success("Certificados actualizados.")
                    st.rerun()

            st.markdown("**Firma del Verificador**")
            firma_actual = prefs.get("firma_img_b64", "")
            if firma_actual:
                st.image(base64.b64decode(firma_actual), width=200, caption="Firma guardada")
            firma_upload = st.file_uploader("Subir imagen de firma (PNG/JPG, fondo transparente recomendado)",
                                            type=["png", "jpg", "jpeg"], key="firma_upload")
            if firma_upload:
                firma_b64 = base64.b64encode(firma_upload.read()).decode()
                prefs["firma_img_b64"] = firma_b64
                save_prefs(prefs)
                st.success("Firma guardada.")
                st.rerun()
            if firma_actual:
                if st.button("🗑️ Eliminar firma guardada", key="del_firma"):
                    prefs.pop("firma_img_b64", None)
                    save_prefs(prefs)
                    st.rerun()

            nombre_actual = prefs.get("firma_nombre", "")
            nombre_input = st.text_input("Aclaración (nombre del verificador)", value=nombre_actual, key="firma_nombre_input")
            if nombre_input != nombre_actual:
                prefs["firma_nombre"] = nombre_input
                save_prefs(prefs)
                st.rerun()

            # ── 4b. TEMPERATURA Y PUESTA A CERO ─────────────────────────────────────
            st.subheader("Temperatura y Puesta a Cero")
            tc1, tc2, tc3 = st.columns(3)
            with tc1:
                temp_inicial = st.number_input("Temp. Inicial (°C)", value=20.0, step=0.1, format="%.1f")
            with tc2:
                temp_final   = st.number_input("Temp. Final (°C)",   value=20.0, step=0.1, format="%.1f")
            with tc3:
                temp_promedio = round((temp_inicial + temp_final) / 2, 2)
                st.metric("Temp. Promedio (°C)", temp_promedio)
            st.caption(f"PUESTA A CERO 4% CAPACIDAD MÁXIMA: **OK**")

            # ── 4d. EXCENTRICIDAD ────────────────────────────────────────────────────
            st.subheader("Excentricidad")

            if es_camion:
                exc_cfg = get_excentricidad_camiones(cap_max, apoyos_db)
                n_posiciones_def = exc_cfg["n_posiciones"]
                pesa_exc_def     = exc_cfg["pesa_exc_kg"]
                st.caption(f"Balanza de camiones: {apoyos_db} apoyos → {pesa_exc_def} kg por posición")
            else:
                n_posiciones_def = 4
                pesa_exc_def     = wc["excentricidad_carga"]

            ec1, ec2 = st.columns(2)
            with ec1:
                n_posiciones = st.number_input(
                    "N° de posiciones", min_value=1, max_value=20,
                    value=n_posiciones_def, step=1,
                    disabled=es_camion,
                    key=f"exc_n_pos_{balanza_sel}"
                )
            with ec2:
                pesa_exc = st.number_input(
                    "Peso por posición (kg)", min_value=1,
                    value=int(pesa_exc_def), step=1,
                    disabled=es_camion,
                    key=f"exc_pesa_{balanza_sel}"
                )

            _s = f"{div_min:.10f}".rstrip("0")
            _dec = len(_s.split(".")[1]) if "." in _s else 0

            def _fmt(v):
                return f"{float(v):.{_dec}f}"

            def _sim(total_kg):
                v = float(total_kg)
                if random.random() < 0.10:
                    v += random.choice([-1, 1]) * div_min
                return _fmt(v)

            exc_df_init = pd.DataFrame([
                {
                    "N°": i,
                    "Posición": str(i),
                    "Pesas (kg)": _fmt(pesa_exc),
                    "C/AUX": "",
                    "Total (kg)": _fmt(pesa_exc),
                    "Indicador (kg)": _sim(int(pesa_exc)),
                }
                for i in range(1, int(n_posiciones) + 1)
            ])
            exc_edited = st.data_editor(
                exc_df_init,
                hide_index=True,
                use_container_width=True,
                key=f"exc_table_{balanza_sel}_{int(pesa_exc)}_{int(n_posiciones)}",
                column_config={
                    "N°": st.column_config.NumberColumn(width="small", disabled=True),
                },
            )
            exc_filas = [
                {
                    "n": int(row["N°"]),
                    "posicion": str(row["Posición"]),
                    "pesas": str(row["Pesas (kg)"]),
                    "c_aux": str(row["C/AUX"]),
                    "total": str(row["Total (kg)"]),
                    "indicador": str(row["Indicador (kg)"]),
                }
                for _, row in exc_edited.iterrows()
            ]

            # ── 4e. LINEALIDAD ───────────────────────────────────────────────────────
            st.subheader("Linealidad")

            if es_camion:
                cap_min_db = int(float(b.get("cap_min") or 1000))
                st.caption("Fase 1: pesas propias desde cap. mínima en pasos de 2000 kg hasta 20.000 kg. "
                           "Fase 2: carga sustituta (camión vacío + autoelevador) + pesas en pasos de 4.000 kg.")
                lc1, lc2, lc3 = st.columns(3)
                with lc1:
                    cap_min_lin = st.number_input("Cap. mínima fase 1 (kg)", value=cap_min_db, step=20, min_value=20, key=f"cap_min_lin_{balanza_sel}")
                with lc2:
                    carga_sust  = st.number_input("Carga sustituta (kg)", value=19600, step=20, min_value=20, key=f"carga_sust_{balanza_sel}")
                with lc3:
                    pesas_disp  = st.number_input("Pesas disponibles (kg)", value=20000, step=20, min_value=20, key=f"pesas_disp_{balanza_sel}")

                fase1 = list(range(int(cap_min_lin), 20001, 2000))
                if fase1[-1] < 20000:
                    fase1.append(20000)
                fase2_pesas = list(range(0, int(pesas_disp) + 1, 4000))[1:]
                fase2_rows  = [(0, int(carga_sust))] + [(p, int(carga_sust) + p) for p in fase2_pesas]

                lin_rows_def = []
                for p in fase1:
                    lin_rows_def.append({"pesas": p, "c_aux": "", "total": p})
                for pesas, total in fase2_rows:
                    lin_rows_def.append({"pesas": pesas, "c_aux": int(carga_sust), "total": total})

            else:
                carga_max_def = int(wc["carga_max_kg"])
                pesa_step     = int(wc["pesa_kg"])
                carga_max_lin = st.number_input(
                    "Carga máxima de linealidad (kg)",
                    value=carga_max_def, step=pesa_step, min_value=pesa_step,
                    key=f"carga_max_lin_{balanza_sel}",
                )
                n_pasos = max(1, round(carga_max_lin / pesa_step))
                lin_rows_def = [{"pesas": pesa_step * i, "c_aux": "", "total": pesa_step * i}
                                for i in range(1, n_pasos + 1)]

            lin_df_init = pd.DataFrame([
                {
                    "N°": i,
                    "Posición": f"1-{apoyos_db}",
                    "Pesas (kg)": _fmt(r["pesas"]),
                    "C/AUX": _fmt(r["c_aux"]) if r["c_aux"] != "" else "",
                    "Total (kg)": _fmt(r["total"]),
                    "Indicador (kg)": _sim(r["total"]),
                }
                for i, r in enumerate(lin_rows_def, start=1)
            ])
            lin_edited = st.data_editor(
                lin_df_init,
                hide_index=True,
                use_container_width=True,
                key=f"lin_table_{balanza_sel}_{len(lin_rows_def)}",
                column_config={
                    "N°": st.column_config.NumberColumn(width="small", disabled=True),
                },
            )
            lin_filas = [
                {
                    "n": int(row["N°"]),
                    "posicion": str(row["Posición"]),
                    "pesas": str(row["Pesas (kg)"]),
                    "c_aux": str(row["C/AUX"]),
                    "total": str(row["Total (kg)"]),
                    "indicador": str(row["Indicador (kg)"]),
                }
                for _, row in lin_edited.iterrows()
            ]

            # ── 4f. MOVILIDAD ────────────────────────────────────────────────────────
            if es_camion:
                st.subheader("Movilidad")
                sobrecarga_camion_kg = round(1.4 * div_min, 2)
                carga_min_mov = int(cap_min_lin)
                carga_int_mov = 20000
                carga_max_mov = int(carga_sust) + int(pesas_disp)

                st.caption(f"Sobrecarga = 1,4 × div. mín ({div_min} kg) = **{sobrecarga_camion_kg} kg**")
                mov_df_init = pd.DataFrame([
                    {
                        "Punto": label,
                        "Carga aplicada (kg)": str(carga_def),
                        "Indicación (kg)": str(carga_def),
                        "Sobrecarga (kg)": str(sobrecarga_camion_kg),
                        "Indicación 2 (kg)": str(round(carga_def + div_min, 2)),
                    }
                    for label, carga_def in [
                        ("Carga mínima", carga_min_mov),
                        ("Carga intermedia", carga_int_mov),
                        ("Carga máxima", carga_max_mov),
                    ]
                ])
                mov_edited = st.data_editor(
                    mov_df_init,
                    hide_index=True,
                    use_container_width=True,
                    key=f"mov_table_{balanza_sel}",
                    column_config={
                        "Punto": st.column_config.TextColumn(disabled=True),
                    },
                )
                movilidad_camion = [
                    {
                        "label": row["Punto"],
                        "carga": row["Carga aplicada (kg)"],
                        "indicacion": row["Indicación (kg)"],
                        "sobrecarga": row["Sobrecarga (kg)"],
                        "indicacion2": row["Indicación 2 (kg)"],
                    }
                    for _, row in mov_edited.iterrows()
                ]
                movilidad_data = {"tipo": "camion", "filas": movilidad_camion}
            else:
                movilidad_data = {"tipo": "ninguna"}

            # ── 4g. RESULTADO DEL ENSAYO ─────────────────────────────────────────────
            st.subheader("Resultado del Ensayo")
            resultado = st.selectbox("Resultado del ensayo", [
                "LA BALANZA ENCUADRA DENTRO DE NORMAS METROLÓGICAS VIGENTES",
                "LA BALANZA NO ENCUADRA DENTRO DE NORMAS METROLÓGICAS VIGENTES",
            ])
            observaciones = st.text_area("Observaciones del ensayo", value="", height=60)

        else:
            resultado = ""
            observaciones = ""
            wc  = get_weight_config(b.get("tipo_balanza", ""), float(b.get("cap_max", 100) or 100)) if b else None
            cfg = get_config()

        # ── GENERAR ───────────────────────────────────────────────────────────────────
        st.divider()
        _bottom_generate = st.button("📄 Generar documentos", type="primary",
                                      use_container_width=True, key="gen_bottom")
        if _top_generate or _bottom_generate:
            balanza_para_pdf = dict(b)
            balanza_para_pdf["precintos_ant_plataforma"] = b["precintos_vig_plataforma"] if plat_cambio else ""
            balanza_para_pdf["precintos_vig_plataforma"] = nuevo_vig_plataforma
            balanza_para_pdf["precintos_ant_indicador"]  = b["precintos_vig_indicador"] if ind_cambio else ""
            balanza_para_pdf["precintos_vig_indicador"]  = nuevo_vig_indicador

            datos_base = {
                "fecha":    fecha.strftime("%d/%m/%Y"),
                "cliente":  cliente_info,
                "balanza":  balanza_para_pdf,
            }

            try:
                _firma_b64    = prefs.get("firma_img_b64", None)
                _firma_nombre = prefs.get("firma_nombre", "")
                is_data = {
                    **datos_base,
                    "nro_is":              int(nro_is),
                    "resumen_falla":       resumen_falla,
                    "trabajos_realizados": trabajos_realizados,
                    "resultado_servicio":  resultado_servicio,
                    "nro_if":              int(nro_if) if hacer_ensayo else None,
                    "firma_img_b64":       _firma_b64,
                    "firma_nombre":        _firma_nombre,
                }
                is_bytes = generate_informe_servicio(is_data)
                save_number(int(nro_is), "IS")

                if hacer_ensayo:
                    if_data = {
                        **datos_base,
                        "nro_informe":         int(nro_if),
                        "firma_img_b64":       _firma_b64,
                        "firma_nombre":        _firma_nombre,
                        "pesa_kg":             wc["pesa_kg"],
                        "cert_pesas_pequenas": cfg.get("cert_pesas_pequenas", ""),
                        "desc_pesas_pequenas": cfg.get("desc_pesas_pequenas", ""),
                        "cert_pesas_grandes":  cfg.get("cert_pesas_grandes", ""),
                        "desc_pesas_grandes":  cfg.get("desc_pesas_grandes", ""),
                        "excentricidad_carga": _fmt(pesa_exc),
                        "div_min":             div_min,
                        "carga_max_kg":        wc["carga_max_kg"],
                        "excentricidad_filas": exc_filas,
                        "linealidad_filas":    lin_filas,
                        "movilidad":           movilidad_data,
                        "temp_inicial":        temp_inicial,
                        "temp_final":          temp_final,
                        "temp_promedio":       temp_promedio,
                        "resultado":           resultado,
                        "observaciones":       observaciones,
                    }
                    if_bytes = generate_pdf(if_data)
                    save_number(int(nro_if), "IF")

                if precintos_cambiados:
                    update_precintos(
                        balanza_sel,
                        nuevo_vig_plataforma, nuevo_vig_indicador,
                        plat_cambio=plat_cambio, ind_cambio=ind_cambio,
                    )

                msg = "✅ Documentos generados."
                if precintos_cambiados:
                    msg += " Precintos actualizados en la base de datos."
                st.success(msg)

                st.session_state["docs_is_bytes"]     = is_bytes
                st.session_state["docs_is_name"]      = f"IS-01-{nro_is:04d}_{balanza_sel}.pdf"
                st.session_state["docs_if_bytes"]     = if_bytes if hacer_ensayo else None
                st.session_state["docs_if_name"]      = f"IF-01-{nro_if:04d}_{balanza_sel}.pdf" if hacer_ensayo else None
                st.session_state["docs_hacer_ensayo"] = hacer_ensayo
                st.rerun()

            except Exception as e:
                st.error(f"Error al generar documentos: {e}")
                raise

        # ── DESCARGAS (persisten tras el clic) ───────────────────────────────────────
        if "docs_is_bytes" in st.session_state:
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button(
                    label="⬇️ Descargar Informe de Servicio",
                    data=st.session_state["docs_is_bytes"],
                    file_name=st.session_state["docs_is_name"],
                    mime="application/pdf",
                    key="dl_is",
                )
            if st.session_state.get("docs_hacer_ensayo") and st.session_state.get("docs_if_bytes"):
                with col_d2:
                    st.download_button(
                        label="⬇️ Descargar Informe de Ensayo",
                        data=st.session_state["docs_if_bytes"],
                        file_name=st.session_state["docs_if_name"],
                        mime="application/pdf",
                        key="dl_if",
                    )

# ── GESTIÓN DE BASE DE DATOS ──────────────────────────────────────────────────
st.divider()
st.header("🗄️ Base de Datos")

with st.expander("➕ Agregar Cliente"):
    with st.form("form_cliente"):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            new_razon = st.text_input("Razón Social *")
        with fc2:
            new_dir   = st.text_input("Dirección")
        with fc3:
            new_loc   = st.text_input("Localidad")
        submitted_c = st.form_submit_button("Guardar Cliente")
    if submitted_c:
        if not new_razon.strip():
            st.error("La Razón Social es obligatoria.")
        else:
            add_cliente(new_razon, new_dir, new_loc)
            st.success(f"Cliente '{new_razon.strip()}' agregado.")
            st.rerun()

with st.expander("➕ Agregar Balanza"):
    clientes_lista = get_clientes()
    if not clientes_lista:
        st.warning("Primero agregá al menos un cliente.")
    else:
        with st.form("form_balanza"):
            st.markdown("**Cliente y tipo**")
            fb1, fb2, fb3 = st.columns(3)
            with fb1:
                b_cliente   = st.selectbox("Cliente *", clientes_lista)
            with fb2:
                b_tipo      = st.text_input("Tipo Balanza", placeholder="CAMIONES / PISO / TOLVA …")
            with fb3:
                b_cod       = st.text_input("Cód. Interno *", placeholder="identificador único")

            st.markdown("**Indicador**")
            fi1, fi2, fi3, fi4, fi5 = st.columns(5)
            with fi1: b_marca     = st.text_input("Marca")
            with fi2: b_mod_ind   = st.text_input("Modelo Indicador")
            with fi3: b_ns_ind    = st.text_input("N° Serie Indicador")
            with fi4: b_ca_ind    = st.text_input("Cod. Aprobación Indicador")
            with fi5: b_ubic      = st.text_input("Ubicación")

            st.markdown("**Plataforma**")
            fp1, fp2, fp3, fp4 = st.columns(4)
            with fp1: b_plat      = st.text_input("Plataforma")
            with fp2: b_medidas   = st.text_input("Medidas")
            with fp3: b_ns_plat   = st.text_input("N° Serie Plataforma")
            with fp4: b_ca_plat   = st.text_input("Cod. Aprobación Plataforma")

            st.markdown("**Capacidades y división**")
            fs1, fs2, fs3, fs4, fs5, fs6 = st.columns(6)
            with fs1: b_cap_max   = st.number_input("Cap. Máx (kg)", min_value=0.0, step=1.0)
            with fs2: b_cap_min   = st.number_input("Cap. Mín (kg)", min_value=0.0, step=1.0)
            with fs3: b_div_min   = st.number_input("Div. Mín (kg)", min_value=0.0, step=0.001, format="%.3f")
            with fs4: b_apoyos    = st.number_input("Apoyos",        min_value=0,   step=1)
            with fs5: b_ult_verif = st.text_input("Ult. Verificación", placeholder="dd/mm/aaaa")
            with fs6: pass

            st.markdown("**Precintos (opcional)**")
            fpr1, fpr2 = st.columns(2)
            with fpr1:
                st.caption("Plataforma")
                b_prec_vig_plat = st.text_input("Vigentes plataforma", key="nb_prec_vig_plat")
            with fpr2:
                st.caption("Indicador")
                b_prec_vig_ind  = st.text_input("Vigentes indicador",  key="nb_prec_vig_ind")

            submitted_b = st.form_submit_button("Guardar Balanza")

        if submitted_b:
            if not b_cod.strip():
                st.error("El Código Interno es obligatorio.")
            else:
                _b_rs, _b_loc = parse_cliente_key(b_cliente)
                try:
                    add_balanza({
                        "razon_social":              _b_rs,
                        "localidad_cliente":         _b_loc,
                        "tipo_balanza":              b_tipo,
                        "mod_indicador":             b_mod_ind,
                        "marca":                     b_marca,
                        "n_serie_indicador":         b_ns_ind,
                        "cod_aprobacion_indicador":  b_ca_ind,
                        "ubicacion":                 b_ubic,
                        "plataforma":                b_plat,
                        "medidas":                   b_medidas,
                        "n_serie_plataforma":        b_ns_plat,
                        "cod_aprobacion_plataforma": b_ca_plat,
                        "ult_verificacion":          b_ult_verif,
                        "cap_max":                   str(int(b_cap_max)) if b_cap_max else "",
                        "cap_min":                   str(int(b_cap_min)) if b_cap_min else "",
                        "div_min":                   str(b_div_min) if b_div_min else "",
                        "apoyos":                    str(int(b_apoyos)) if b_apoyos else "",
                        "cod_interno":               b_cod.strip(),
                        "precintos_ant_plataforma":  "",
                        "precintos_vig_plataforma":  b_prec_vig_plat,
                        "precintos_ant_indicador":   "",
                        "precintos_vig_indicador":   b_prec_vig_ind,
                    })
                    st.success(f"Balanza '{b_cod.strip()}' agregada al cliente '{b_cliente}'.")
                    st.rerun()
                except Exception as e:
                    if "23505" in str(e) or "duplicate key" in str(e).lower():
                        st.error(f"Ya existe una balanza con el código interno '{b_cod.strip()}' para ese cliente. Usá un código diferente.")
                    else:
                        st.error(f"Error al guardar la balanza: {e}")

with st.expander("✏️ Modificar Cliente"):
    clientes_edit = get_clientes()
    if not clientes_edit:
        st.info("No hay clientes en la base de datos.")
    else:
        ec_sel = st.selectbox("Seleccionar cliente a modificar", clientes_edit, key="ec_sel")
        ec_info = get_cliente_info(ec_sel)
        with st.form("form_edit_cliente"):
            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                ec_razon = st.text_input("Razón Social *", value=ec_info.get("razon_social", ec_sel))
            with ec2:
                ec_dir   = st.text_input("Dirección",     value=ec_info.get("direccion", ""))
            with ec3:
                ec_loc   = st.text_input("Localidad",     value=ec_info.get("localidad", ""))
            submitted_ec = st.form_submit_button("Guardar cambios")
        if submitted_ec:
            if not ec_razon.strip():
                st.error("La Razón Social es obligatoria.")
            else:
                update_cliente(ec_sel, ec_razon, ec_dir, ec_loc)
                st.success(f"Cliente '{ec_razon.strip()}' actualizado.")
                st.rerun()

with st.expander("✏️ Modificar Balanza"):
    clientes_eb = get_clientes()
    if not clientes_eb:
        st.info("No hay clientes en la base de datos.")
    else:
        eb_cliente = st.selectbox("Cliente", clientes_eb, key="eb_cliente")
        balanzas_eb = get_balanzas_de_cliente(eb_cliente)
        if not balanzas_eb:
            st.info("Este cliente no tiene balanzas.")
        else:
            eb_sel = st.selectbox("Balanza (Cód. Interno)", balanzas_eb, key="eb_sel")
            eb = get_balanza_info(eb_sel)

            with st.form("form_edit_balanza"):
                st.markdown("**Cliente y tipo**")
                efb1, efb2, efb3 = st.columns(3)
                with efb1:
                    eb_cliente2 = st.selectbox("Cliente *", clientes_eb,
                                               index=clientes_eb.index(eb_cliente) if eb_cliente in clientes_eb else 0)
                with efb2:
                    eb_tipo = st.text_input("Tipo Balanza",  value=eb.get("tipo_balanza", ""))
                with efb3:
                    eb_cod  = st.text_input("Cód. Interno *", value=eb.get("cod_interno", ""))

                st.markdown("**Indicador**")
                efi1, efi2, efi3, efi4, efi5 = st.columns(5)
                with efi1: eb_marca   = st.text_input("Marca",                    value=eb.get("marca", ""))
                with efi2: eb_mod_ind = st.text_input("Modelo Indicador",          value=eb.get("mod_indicador", ""))
                with efi3: eb_ns_ind  = st.text_input("N° Serie Indicador",        value=eb.get("n_serie_indicador", ""))
                with efi4: eb_ca_ind  = st.text_input("Cod. Aprobación Indicador", value=eb.get("cod_aprobacion_indicador", ""))
                with efi5: eb_ubic    = st.text_input("Ubicación",                 value=eb.get("ubicacion", ""))

                st.markdown("**Plataforma**")
                efp1, efp2, efp3, efp4 = st.columns(4)
                with efp1: eb_plat    = st.text_input("Plataforma",                 value=eb.get("plataforma", ""))
                with efp2: eb_medidas = st.text_input("Medidas",                    value=eb.get("medidas", ""))
                with efp3: eb_ns_plat = st.text_input("N° Serie Plataforma",        value=eb.get("n_serie_plataforma", ""))
                with efp4: eb_ca_plat = st.text_input("Cod. Aprobación Plataforma", value=eb.get("cod_aprobacion_plataforma", ""))

                st.markdown("**Capacidades y división**")
                efs1, efs2, efs3, efs4, efs5 = st.columns(5)
                def _float(v):
                    try: return float(v)
                    except: return 0.0
                def _int(v):
                    try: return int(float(v))
                    except: return 0
                with efs1: eb_cap_max   = st.number_input("Cap. Máx (kg)",  value=_float(eb.get("cap_max", 0)),   min_value=0.0, step=1.0)
                with efs2: eb_cap_min   = st.number_input("Cap. Mín (kg)",  value=_float(eb.get("cap_min", 0)),   min_value=0.0, step=1.0)
                with efs3: eb_div_min   = st.number_input("Div. Mín (kg)",  value=_float(eb.get("div_min", 0)),   min_value=0.0, step=0.001, format="%.3f")
                with efs4: eb_apoyos    = st.number_input("Apoyos",         value=_int(eb.get("apoyos", 0)),      min_value=0,   step=1)
                with efs5: eb_ult_verif = st.text_input("Ult. Verificación", value=eb.get("ult_verificacion", ""))

                st.markdown("**Precintos**")
                efpr1, efpr2 = st.columns(2)
                with efpr1:
                    st.caption("Plataforma")
                    eb_prec_ant_plat = st.text_input("Anteriores plataforma", value=eb.get("precintos_ant_plataforma", ""), key=f"eb_prec_ant_plat_{eb_sel}")
                    eb_prec_vig_plat = st.text_input("Vigentes plataforma",   value=eb.get("precintos_vig_plataforma", ""), key=f"eb_prec_vig_plat_{eb_sel}")
                with efpr2:
                    st.caption("Indicador")
                    eb_prec_ant_ind  = st.text_input("Anteriores indicador",  value=eb.get("precintos_ant_indicador", ""),  key=f"eb_prec_ant_ind_{eb_sel}")
                    eb_prec_vig_ind  = st.text_input("Vigentes indicador",    value=eb.get("precintos_vig_indicador", ""),  key=f"eb_prec_vig_ind_{eb_sel}")

                submitted_eb = st.form_submit_button("Guardar cambios")

            if submitted_eb:
                if not eb_cod.strip():
                    st.error("El Código Interno es obligatorio.")
                else:
                    _eb_rs, _eb_loc = parse_cliente_key(eb_cliente2)
                    try:
                        update_balanza(eb_sel, eb.get("razon_social", ""), {
                            "razon_social":              _eb_rs,
                            "localidad_cliente":         _eb_loc,
                            "tipo_balanza":              eb_tipo,
                            "mod_indicador":             eb_mod_ind,
                            "marca":                     eb_marca,
                            "n_serie_indicador":         eb_ns_ind,
                            "cod_aprobacion_indicador":  eb_ca_ind,
                            "ubicacion":                 eb_ubic,
                            "plataforma":                eb_plat,
                            "medidas":                   eb_medidas,
                            "n_serie_plataforma":        eb_ns_plat,
                            "cod_aprobacion_plataforma": eb_ca_plat,
                            "ult_verificacion":          eb_ult_verif,
                            "cap_max":                   str(int(eb_cap_max)) if eb_cap_max else "",
                            "cap_min":                   str(int(eb_cap_min)) if eb_cap_min else "",
                            "div_min":                   str(eb_div_min) if eb_div_min else "",
                            "apoyos":                    str(int(eb_apoyos)) if eb_apoyos else "",
                            "cod_interno":               eb_cod.strip(),
                            "precintos_ant_plataforma":  eb_prec_ant_plat,
                            "precintos_vig_plataforma":  eb_prec_vig_plat,
                            "precintos_ant_indicador":   eb_prec_ant_ind,
                            "precintos_vig_indicador":   eb_prec_vig_ind,
                        })
                        st.success(f"Balanza '{eb_cod.strip()}' actualizada.")
                        st.rerun()
                    except Exception as e:
                        if "23505" in str(e) or "duplicate key" in str(e).lower():
                            st.error(f"Ya existe otra balanza con el código interno '{eb_cod.strip()}'. Usá un código diferente.")
                        else:
                            st.error(f"Error al actualizar la balanza: {e}")
