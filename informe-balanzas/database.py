"""
Base de datos en Supabase (PostgreSQL).
Misma interfaz que la versión Excel — app.py no cambia.
"""
import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def _client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def _cliente_key(rs: str, loc: str) -> str:
    return f"{rs} — {loc}" if loc.strip() else rs.strip()


def parse_cliente_key(key: str) -> tuple[str, str]:
    if " — " in key:
        rs, loc = key.split(" — ", 1)
        return rs.strip(), loc.strip()
    return key.strip(), ""


# ── CLIENTES ──────────────────────────────────────────────────────────────────

def get_clientes() -> list[str]:
    rows = _client().table("clientes").select("razon_social, localidad").execute().data
    keys = [_cliente_key(r["razon_social"], r.get("localidad") or "") for r in rows if r["razon_social"]]
    return sorted(set(keys))


def get_cliente_info(key: str) -> dict:
    rs, loc = parse_cliente_key(key)
    q = _client().table("clientes").select("*").eq("razon_social", rs)
    if loc:
        q = q.eq("localidad", loc)
    rows = q.limit(1).execute().data
    if not rows:
        return {}
    r = rows[0]
    return {
        "razon_social": r.get("razon_social", ""),
        "direccion":    r.get("direccion", ""),
        "localidad":    r.get("localidad", ""),
    }


def add_cliente(razon_social: str, direccion: str, localidad: str):
    _client().table("clientes").insert({
        "razon_social": razon_social.strip(),
        "direccion":    direccion.strip(),
        "localidad":    localidad.strip(),
    }).execute()


def update_cliente(key_original: str, razon_social: str, direccion: str, localidad: str):
    rs_orig, loc_orig = parse_cliente_key(key_original)
    q = _client().table("clientes").update({
        "razon_social": razon_social.strip(),
        "direccion":    direccion.strip(),
        "localidad":    localidad.strip(),
    }).eq("razon_social", rs_orig)
    if loc_orig:
        q = q.eq("localidad", loc_orig)
    q.execute()
    # Propagar cambio de razón social a balanzas
    if rs_orig != razon_social.strip():
        uq = _client().table("balanzas").update({"razon_social": razon_social.strip()}).eq("razon_social", rs_orig)
        if loc_orig:
            uq = uq.eq("localidad_cliente", loc_orig)
        uq.execute()


# ── BALANZAS ──────────────────────────────────────────────────────────────────

def get_balanzas_de_cliente(key: str) -> list[str]:
    rs, loc = parse_cliente_key(key)
    q = _client().table("balanzas").select("cod_interno, cap_max_kg").eq("razon_social", rs)
    if loc:
        q = q.eq("localidad_cliente", loc)
    rows = q.execute().data

    def _cap(r):
        try:
            return float(r.get("cap_max_kg") or 0)
        except (TypeError, ValueError):
            return 0.0

    rows.sort(key=lambda r: (_cap(r), r["cod_interno"]))
    return [r["cod_interno"] for r in rows]


def get_balanza_info(cod_interno: str) -> dict:
    rows = _client().table("balanzas").select("*").eq("cod_interno", cod_interno).limit(1).execute().data
    if not rows:
        return {}
    r = rows[0]
    return {
        "tipo_balanza":              r.get("tipo_balanza", ""),
        "mod_indicador":             r.get("mod_indicador", ""),
        "marca":                     r.get("marca", ""),
        "n_serie_indicador":         r.get("n_serie_indicador", ""),
        "cod_aprobacion_indicador":  r.get("cod_aprobacion_indicador", ""),
        "ubicacion":                 r.get("ubicacion", ""),
        "plataforma":                r.get("plataforma", ""),
        "medidas":                   r.get("medidas", ""),
        "n_serie_plataforma":        r.get("n_serie_plataforma", ""),
        "cod_aprobacion_plataforma": r.get("cod_aprobacion_plataforma", ""),
        "ult_verificacion":          r.get("ult_verificacion", ""),
        "cap_max":                   r.get("cap_max_kg", ""),
        "cap_min":                   r.get("cap_min_kg", ""),
        "div_min":                   r.get("div_min_kg", ""),
        "apoyos":                    r.get("apoyos", ""),
        "cod_interno":               r.get("cod_interno", ""),
        "precintos_ant_plataforma":  r.get("precintos_ant_plataforma", ""),
        "precintos_vig_plataforma":  r.get("precintos_vig_plataforma", ""),
        "precintos_ant_indicador":   r.get("precintos_ant_indicador", ""),
        "precintos_vig_indicador":   r.get("precintos_vig_indicador", ""),
        "localidad_cliente":         r.get("localidad_cliente", ""),
        # alias legacy
        "n_serie":        r.get("n_serie_indicador", ""),
        "cod_aprobacion": r.get("cod_aprobacion_indicador", ""),
    }


def add_balanza(d: dict):
    _client().table("balanzas").insert({
        "razon_social":              d.get("razon_social", ""),
        "localidad_cliente":         d.get("localidad_cliente", ""),
        "tipo_balanza":              d.get("tipo_balanza", ""),
        "mod_indicador":             d.get("mod_indicador", ""),
        "marca":                     d.get("marca", ""),
        "n_serie_indicador":         d.get("n_serie_indicador", ""),
        "cod_aprobacion_indicador":  d.get("cod_aprobacion_indicador", ""),
        "ubicacion":                 d.get("ubicacion", ""),
        "plataforma":                d.get("plataforma", ""),
        "medidas":                   d.get("medidas", ""),
        "n_serie_plataforma":        d.get("n_serie_plataforma", ""),
        "cod_aprobacion_plataforma": d.get("cod_aprobacion_plataforma", ""),
        "ult_verificacion":          d.get("ult_verificacion", ""),
        "cap_max_kg":                d.get("cap_max", ""),
        "cap_min_kg":                d.get("cap_min", ""),
        "div_min_kg":                d.get("div_min", ""),
        "apoyos":                    d.get("apoyos", ""),
        "cod_interno":               d.get("cod_interno", ""),
        "precintos_ant_plataforma":  d.get("precintos_ant_plataforma", ""),
        "precintos_vig_plataforma":  d.get("precintos_vig_plataforma", ""),
        "precintos_ant_indicador":   d.get("precintos_ant_indicador", ""),
        "precintos_vig_indicador":   d.get("precintos_vig_indicador", ""),
    }).execute()


def update_balanza(cod_interno_original: str, d: dict):
    _client().table("balanzas").update({
        "razon_social":              d.get("razon_social", ""),
        "localidad_cliente":         d.get("localidad_cliente", ""),
        "tipo_balanza":              d.get("tipo_balanza", ""),
        "mod_indicador":             d.get("mod_indicador", ""),
        "marca":                     d.get("marca", ""),
        "n_serie_indicador":         d.get("n_serie_indicador", ""),
        "cod_aprobacion_indicador":  d.get("cod_aprobacion_indicador", ""),
        "ubicacion":                 d.get("ubicacion", ""),
        "plataforma":                d.get("plataforma", ""),
        "medidas":                   d.get("medidas", ""),
        "n_serie_plataforma":        d.get("n_serie_plataforma", ""),
        "cod_aprobacion_plataforma": d.get("cod_aprobacion_plataforma", ""),
        "ult_verificacion":          d.get("ult_verificacion", ""),
        "cap_max_kg":                d.get("cap_max", ""),
        "cap_min_kg":                d.get("cap_min", ""),
        "div_min_kg":                d.get("div_min", ""),
        "apoyos":                    d.get("apoyos", ""),
        "cod_interno":               d.get("cod_interno", ""),
        "precintos_ant_plataforma":  d.get("precintos_ant_plataforma", ""),
        "precintos_vig_plataforma":  d.get("precintos_vig_plataforma", ""),
        "precintos_ant_indicador":   d.get("precintos_ant_indicador", ""),
        "precintos_vig_indicador":   d.get("precintos_vig_indicador", ""),
    }).eq("cod_interno", cod_interno_original).execute()


def update_precintos(cod_interno: str,
                     nuevo_vig_plataforma: str | None,
                     nuevo_vig_indicador: str | None,
                     plat_cambio: bool = False,
                     ind_cambio: bool = False):
    if not plat_cambio and not ind_cambio:
        return
    current = get_balanza_info(cod_interno)
    patch = {}
    if plat_cambio:
        patch["precintos_ant_plataforma"] = current.get("precintos_vig_plataforma", "")
        patch["precintos_vig_plataforma"] = nuevo_vig_plataforma or ""
    if ind_cambio:
        patch["precintos_ant_indicador"] = current.get("precintos_vig_indicador", "")
        patch["precintos_vig_indicador"] = nuevo_vig_indicador or ""
    _client().table("balanzas").update(patch).eq("cod_interno", cod_interno).execute()


# ── CONFIGURACION ─────────────────────────────────────────────────────────────

def get_config() -> dict:
    rows = _client().table("configuracion").select("clave, valor").execute().data
    return {r["clave"]: r["valor"] for r in rows}


def update_config(clave: str, valor: str):
    _client().table("configuracion").upsert({"clave": clave, "valor": valor}).execute()
