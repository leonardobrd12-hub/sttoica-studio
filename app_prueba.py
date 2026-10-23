import hmac
import json
import re
import time
from datetime import datetime, date, timedelta, time as dtime
from html import escape
from urllib.parse import quote

import altair as alt
import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from gspread.utils import rowcol_to_a1

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("America/Monterrey")
except Exception:
    TZ = None

# ------------------------------------------------------------------
# 1. CONFIGURACIÓN DEL SISTEMA
# ------------------------------------------------------------------
st.set_page_config(page_title="Sttoica Studio", page_icon="✨", layout="centered")

NOMBRE_SPREADSHEET = "Prueba Sttoica"

HORARIOS = ["08:00 AM", "09:30 AM", "05:00 PM", "06:30 PM", "08:00 PM"]
INSTRUCTORAS = ["Aby", "Dulce", "Jennifer"]
CUPO_MAX = 8
HORAS_MIN_CANCELAR = 2
DIAS_ADELANTE = 30

TARIFAS = {
    "DICTADAS": 300.0,
    "EN EL ESTUDIO SIN RESERVA": 250.0,
    "NO FUE AL ESTUDIO": 200.0,
}

PAQUETES = {
    "4 clases": {"clases": 4, "dias": 30},
    "8 clases": {"clases": 8, "dias": 30},
    "12 clases": {"clases": 12, "dias": 45},
}

MAX_INTENTOS = 5
BLOQUEO_SEG = 60

ALUMNAS_COLS = ["ID", "Nombre", "Telefono", "Estatus_Pago", "Paquete", "Clases_Restantes", "Vencimiento"]
RESERVAS_COLS = [
    "Fecha", "Hora", "Alumna", "Instructor", "Estatus", "Timestamp",
    "ID_Alumna", "Asistencia", "Pago_Registrado"
]

# Paleta Sttoica
GUINDA = "#4A1525"
GUINDA_HOVER = "#631D31"
ROSA_PALO = "#B07A8A"
CREMA = "#F8F6F0"
CREMA_OSCURO = "#EFEBE1"
BORDE = "#DED7CB"
TEXTO = "#2C2A29"
TEXTO_SUAVE = "#7A726E"
VERDE = "#2E7D32"
ROJO = "#C62828"

# ------------------------------------------------------------------
# 2. ESTILOS CSS
# ------------------------------------------------------------------
st.markdown(f"""
<style>
:root {{ color-scheme: light !important; }}
.stApp {{ background-color: {CREMA} !important; color: {TEXTO} !important; font-family: 'Helvetica Neue', sans-serif; }}
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}
div.block-container {{ padding-top: 1.5rem; max-width: 550px; margin: 0 auto; }}

html {{ -webkit-text-size-adjust: 100%; }}
input, select, textarea,
div[data-baseweb="input"] input,
div[data-baseweb="select"] input,
div[data-baseweb="select"] div {{ font-size: 16px !important; }}
button, a, label, [role="tab"], [role="radio"] {{ touch-action: manipulation; }}

/* CONTENEDOR DE PESTAÑAS (varios selectores para distintas versiones de Streamlit) */
div[data-testid="stTabs"],
div[data-baseweb="tabs"] {{
    background: transparent !important;
}}

div[data-testid="stTabs"] div[role="tablist"],
div[data-baseweb="tab-list"] {{
    background: transparent !important;
    gap: 8px !important;
    border-bottom: none !important;
    padding-bottom: 12px !important;
    display: flex !important;
    flex-wrap: wrap !important;
}}

/* BOTÓN DE PESTAÑA INACTIVO (FONDO BLANCO, BORDE Y TEXTO GUINDA) */
div[data-testid="stTabs"] button[role="tab"],
button[data-baseweb="tab"],
button[data-testid="stTab"],
[data-testid="stTab"] {{
    background-color: #FFFFFF !important;
    border: 1px solid {BORDE} !important;
    border-radius: 999px !important;
    padding: 6px 14px !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05) !important;
    opacity: 1 !important;
    color: {GUINDA} !important;
    -webkit-text-fill-color: {GUINDA} !important;
    height: auto !important;
}}

/* FORZAR COLOR DE TEXTO E ICONOS EN PESTAÑAS INACTIVAS (incluye p, span, div internos) */
div[data-testid="stTabs"] button[role="tab"] *,
button[data-baseweb="tab"] *,
button[data-testid="stTab"] *,
[data-testid="stTab"] *,
div[data-testid="stTabs"] button[role="tab"] p,
button[data-baseweb="tab"] p,
button[data-baseweb="tab"] span,
button[data-baseweb="tab"] div {{
    color: {GUINDA} !important;
    -webkit-text-fill-color: {GUINDA} !important;
    fill: {GUINDA} !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    opacity: 1 !important;
}}

div[data-testid="stTabs"] button[role="tab"]:hover,
button[data-baseweb="tab"]:hover,
[data-testid="stTab"]:hover {{
    border-color: {GUINDA} !important;
    background-color: {CREMA_OSCURO} !important;
}}

/* PESTAÑA ACTIVA / SELECCIONADA */
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"],
button[data-baseweb="tab"][aria-selected="true"],
[data-testid="stTab"][aria-selected="true"] {{
    background-color: {GUINDA} !important;
    border-color: {GUINDA} !important;
}}

div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] *,
button[data-baseweb="tab"][aria-selected="true"] *,
button[data-testid="stTab"][aria-selected="true"] *,
[data-testid="stTab"][aria-selected="true"] *,
button[data-baseweb="tab"][aria-selected="true"] p,
button[data-baseweb="tab"][aria-selected="true"] span,
button[data-baseweb="tab"][aria-selected="true"] div {{
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    fill: #FFFFFF !important;
    font-weight: 800 !important;
}}

/* OCULTAR LÍNEAS DECORATIVAS DE STREAMLIT */
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"], [data-testid="stTabs"] hr,
div[data-testid="stTabs"] div[role="tablist"] > div:not([role="tab"]),
div[data-baseweb="tab-list"] > div:not([role="tab"]) {{
    display: none !important;
    height: 0 !important;
    background: transparent !important;
    background-color: transparent !important;
    opacity: 0 !important;
}}
button[role="tab"]::before, button[role="tab"]::after,
button[data-baseweb="tab"]::before, button[data-baseweb="tab"]::after {{
    display: none !important;
    content: none !important;
    border: none !important;
    background: transparent !important;
}}

/* ELEMENTOS DE FORMULARIO */
div[data-testid="stWidgetLabel"] p, div[data-testid="stWidgetLabel"] label, label {{
    color: {GUINDA} !important; font-weight: 600 !important; font-size: 0.9rem !important;
}}
div[role="radiogroup"] label p {{ color: {TEXTO} !important; }}
div[data-baseweb="select"] > div, div[data-testid="stNumberInputContainer"],
div[data-baseweb="input"], div[data-baseweb="base-input"] {{
    background-color: #FFFFFF !important; color: {TEXTO} !important;
    border: 1px solid {BORDE} !important; border-radius: 12px !important;
}}
div[data-baseweb="input"] input, div[data-baseweb="base-input"] input {{
    color: {TEXTO} !important; -webkit-text-fill-color: {TEXTO} !important; background: transparent !important;
}}
div[data-baseweb="select"] span, div[data-baseweb="select"] div {{ color: {TEXTO} !important; }}
div[data-baseweb="select"] svg {{ fill: {GUINDA} !important; }}
div[data-baseweb="popover"] ul, div[data-baseweb="popover"] li {{ background-color: #FFFFFF !important; color: {TEXTO} !important; }}
div[data-baseweb="popover"] li:hover {{ background-color: {CREMA} !important; }}
div[data-testid="stNumberInputContainer"] button {{ background-color: {CREMA} !important; color: {GUINDA} !important; }}
div[data-testid="stNumberInputContainer"] button svg {{ fill: {GUINDA} !important; }}

div[data-testid="stAlert"] p {{ color: {TEXTO} !important; }}

div[data-testid="stExpander"] {{
    background: #FFFFFF !important; border: 1px solid {CREMA_OSCURO} !important;
    border-radius: 16px !important; margin-bottom: 10px !important;
}}
div[data-testid="stExpander"] summary p {{ color: {GUINDA} !important; font-weight: 700 !important; }}
div[data-testid="stForm"] {{
    border: 1px solid {CREMA_OSCURO} !important; border-radius: 16px !important; background: #FFFFFF !important;
}}

div.stButton > button, div.stDownloadButton > button,
div[data-testid="stFormSubmitButton"] > button, a[data-testid="stLinkButton"] {{
    background-color: {GUINDA} !important; color: #FFFFFF !important; border-radius: 14px !important;
    padding: 0.85rem 1.5rem !important; width: 100% !important; border: none !important;
    box-shadow: 0 6px 15px rgba(74, 21, 37, 0.25) !important; display: flex !important;
    justify-content: center !important; align-items: center !important; transition: all 0.2s ease-in-out !important;
}}
div.stButton > button p, div.stButton > button span, div.stDownloadButton > button p,
div.stDownloadButton > button span, div[data-testid="stFormSubmitButton"] > button p,
a[data-testid="stLinkButton"] p, a[data-testid="stLinkButton"] span {{
    color: #FFFFFF !important; font-weight: 600 !important; font-size: 1rem !important;
    letter-spacing: 0.5px !important; margin: 0 !important;
}}
div.stButton > button:hover, div.stDownloadButton > button:hover,
div[data-testid="stFormSubmitButton"] > button:hover, a[data-testid="stLinkButton"]:hover {{
    background-color: {GUINDA_HOVER} !important; transform: translateY(-2px) !important;
}}
div.stButton > button:disabled {{ background-color: {BORDE} !important; box-shadow: none !important; }}

div[data-testid="stVegaLiteChart"], div[data-testid="stArrowVegaLiteChart"] {{
    background-color: #FFFFFF !important; border: 1px solid {CREMA_OSCURO} !important;
    border-radius: 20px !important; padding: 14px 16px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03) !important; overflow: hidden !important; margin-bottom: 8px !important;
}}
div[data-testid="stDataFrame"] {{ border: 1px solid {CREMA_OSCURO} !important; border-radius: 16px !important; overflow: hidden !important; }}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------
# 3. UTILIDADES
# ------------------------------------------------------------------
def ahora() -> datetime:
    return datetime.now(TZ).replace(tzinfo=None) if TZ else datetime.now()


def hoy() -> date:
    return ahora().date()


def formato_moneda(valor: float) -> str:
    signo = "-" if valor < 0 else ""
    return f"{signo}${abs(valor):,.2f}"


def hora_a_time(h: str) -> dtime:
    t, ap = h.strip().split()
    hh, mm = (int(x) for x in t.split(":"))
    if ap.upper() == "PM" and hh != 12:
        hh += 12
    if ap.upper() == "AM" and hh == 12:
        hh = 0
    return dtime(hh, mm)


def slot_dt(fecha: str, hora: str):
    try:
        return datetime.combine(date.fromisoformat(str(fecha).strip()), hora_a_time(hora))
    except Exception:
        return None


def parse_fecha(v):
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None


def parse_int(v):
    try:
        return int(float(str(v).strip()))
    except Exception:
        return None


def html(s: str):
    st.markdown(s, unsafe_allow_html=True)


def titulo(txt: str) -> str:
    return (f"<p style='font-size:0.8rem;color:{TEXTO_SUAVE} !important;font-weight:700;"
            f"letter-spacing:1px;margin:14px 0 10px 0;'>{txt}</p>")


def tarjeta(contenido: str) -> str:
    return (f"<div style='background-color:#FFFFFF;border-radius:16px;padding:14px 18px;margin-bottom:10px;"
            f"border:1px solid {CREMA_OSCURO};box-shadow:0 2px 6px rgba(0,0,0,0.03);'>{contenido}</div>")


def mini_cards(items) -> str:
    cajas = "".join(
        f"<div style='flex:1;background:#FFFFFF;border:1px solid {CREMA_OSCURO};border-radius:16px;padding:12px 8px;text-align:center;"
        f"box-shadow:0 2px 6px rgba(0,0,0,0.03);'>"
        f"<p style='margin:0;font-size:0.68rem;color:{TEXTO_SUAVE} !important;letter-spacing:0.5px;'>{etq}</p>"
        f"<p style='margin:4px 0 0 0;font-size:1.05rem;font-weight:800;color:{GUINDA} !important;'>{val}</p></div>"
        for etq, val in items)
    return f"<div style='display:flex;gap:10px;margin-bottom:16px;'>{cajas}</div>"


BADGES = {
    "Activa": ("#E3F2E5", VERDE), "Pendiente": ("#FFF3E0", "#E65100"),
    "Vencida": ("#FDE7E7", ROJO), "Sin clases": ("#FDE7E7", ROJO),
    "Por vencer": ("#FFF8E1", "#B26A00"), "Asistió": ("#E3F2E5", VERDE),
    "No asistió": ("#FDE7E7", ROJO), "Por marcar": (CREMA_OSCURO, TEXTO_SUAVE),
}


def badge(txt: str) -> str:
    bg, fg = BADGES.get(txt, (CREMA_OSCURO, GUINDA))
    return (f"<span style='background:{bg};color:{fg} !important;padding:3px 10px;border-radius:999px;"
            f"font-size:0.72rem;font-weight:700;white-space:nowrap;'>{txt}</span>")


def barra_ocupacion(n: int, cupo: int) -> str:
    pct = min(100, int(n / cupo * 100)) if cupo else 0
    return (f"<div style='background:{CREMA_OSCURO};border-radius:999px;height:8px;margin-top:8px;'>"
            f"<div style='width:{pct}%;background:{GUINDA};height:8px;border-radius:999px;'></div></div>")


def grafica_barras(serie: pd.Series, color: str, fmt: str = "$,.0f"):
    data = serie.reset_index()
    data.columns = ["Etiqueta", "Monto"]
    data = data.sort_values("Monto", ascending=False)
    maximo = float(data["Monto"].max()) or 1.0
    base = alt.Chart(data).encode(
        y=alt.Y("Etiqueta:N", sort="-x", title=None,
                axis=alt.Axis(labelColor=GUINDA, labelFontSize=12, labelFontWeight=600, labelLimit=140,
                              ticks=False, domain=False, labelPadding=8)),
        x=alt.X("Monto:Q", title=None, axis=None, scale=alt.Scale(domain=[0, maximo * 1.3])),
        tooltip=[alt.Tooltip("Etiqueta:N", title="Concepto"), alt.Tooltip("Monto:Q", title="Total", format=fmt)],
    )
    barras = base.mark_bar(cornerRadiusEnd=8, size=24, color=color)
    textos = base.mark_text(align="left", dx=8, color=TEXTO, fontWeight="bold", fontSize=12).encode(
        text=alt.Text("Monto:Q", format=fmt))
    return ((barras + textos).properties(height=max(70, 46 * len(data)), background="#FFFFFF")
            .configure_view(stroke=None).configure_axis(grid=False))


def grafica_mensual(df: pd.DataFrame):
    d = (df[df["Tipo"].isin(["Ingreso", "Gasto"])]
         .groupby(["Mes", "Tipo"])["Monto_Num"].sum().reset_index())
    return (alt.Chart(d)
            .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
            .encode(
                x=alt.X("Mes:N", title=None, axis=alt.Axis(labelColor=GUINDA, labelAngle=0, ticks=False, domain=False)),
                xOffset="Tipo:N",
                y=alt.Y("Monto_Num:Q", title=None,
                        axis=alt.Axis(labelColor=TEXTO_SUAVE, gridColor=CREMA_OSCURO, domain=False, ticks=False, format="$,.0f")),
                color=alt.Color("Tipo:N",
                                scale=alt.Scale(domain=["Ingreso", "Gasto"], range=["#7FB58A", GUINDA]),
                                legend=alt.Legend(orient="bottom", title=None, labelColor=TEXTO)),
                tooltip=[alt.Tooltip("Mes:N"), alt.Tooltip("Tipo:N"),
                         alt.Tooltip("Monto_Num:Q", title="Total", format="$,.2f")],
            )
            .properties(height=240, background="#FFFFFF")
            .configure_view(stroke=None))


# ------------------------------------------------------------------
# 4. GOOGLE SHEETS (HÍBRIDO: NUBE O LOCAL)
# ------------------------------------------------------------------
def asegurar_hoja(ss, nombre, columnas):
    try:
        ws = ss.worksheet(nombre)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=nombre, rows=300, cols=len(columnas) + 2)
        ws.append_row(columnas)
        return ws
    header = ws.row_values(1)
    faltan = [c for c in columnas if c not in header]
    if faltan:
        nuevo = header + faltan
        if ws.col_count < len(nuevo):
            ws.resize(cols=len(nuevo))
        ws.update(values=[nuevo], range_name="A1")
    return ws


@st.cache_resource
def hojas():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = None

    # 1. Modo Nube: Lee credenciales de Streamlit Secrets
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    except Exception:
        pass

    # 2. Modo Local: Si no está en Secrets, lee credentials.json
    if not creds:
        with open("credentials.json", "r") as f:
            creds_data = json.load(f)
        creds = Credentials.from_service_account_info(creds_data, scopes=scope)

    ss = gspread.authorize(creds).open(NOMBRE_SPREADSHEET)
    return {
        "finanzas": ss.sheet1,
        "alumnas": asegurar_hoja(ss, "Alumnas", ALUMNAS_COLS),
        "reservas": asegurar_hoja(ss, "Reservas", RESERVAS_COLS),
    }


@st.cache_data(ttl=20, show_spinner=False)
def leer(nombre: str):
    return hojas()[nombre].get_all_values()


def refrescar():
    leer.clear()


def terminar(mensaje: str):
    refrescar()
    st.session_state["flash"] = mensaje
    st.rerun()


def df_hoja(nombre: str, fila_header: int = 0) -> pd.DataFrame:
    rows = leer(nombre)
    if len(rows) <= fila_header:
        return pd.DataFrame()
    return pd.DataFrame(rows[fila_header + 1:], columns=rows[fila_header])


def preparar_fin() -> pd.DataFrame:
    df = df_hoja("finanzas", 5)
    if not df.empty and "Monto" in df.columns:
        df["Monto_Num"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0)
    for col in ["Categoria", "Instructor"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.capitalize()
    if "Fecha" in df.columns:
        df["Mes"] = df["Fecha"].astype(str).str[:7]
    return df


def estado_alumna(row) -> str:
    pago = str(row.get("Estatus_Pago", "")).strip().capitalize()
    venc = parse_fecha(row.get("Vencimiento", ""))
    rest = parse_int(row.get("Clases_Restantes", ""))
    if pago != "Pagado":
        return "Pendiente"
    if venc and venc < hoy():
        return "Vencida"
    if rest is not None and rest <= 0:
        return "Sin clases"
    return "Activa"


def preparar_alumnas() -> pd.DataFrame:
    df = df_hoja("alumnas")
    if not df.empty:
        df["Estado"] = df.apply(estado_alumna, axis=1)
    return df


def fila_por_header(nombre: str, datos: dict) -> list:
    header = leer(nombre)[0]
    return [datos.get(c, "") for c in header]


def actualizar_celdas(nombre: str, fila: int, valores: dict):
    header = leer(nombre)[0]
    lote = [{"range": rowcol_to_a1(fila, header.index(c) + 1), "values": [[v]]} for c, v in valores.items()]
    hojas()[nombre].batch_update(lote, value_input_option="RAW")


def fila_finanza(tipo, tipo_clase, categoria, detalle, monto, instructor, n=0) -> list:
    t = ahora()
    id_mov = t.strftime("%Y%m%d%H%M%S") + (f"{n:02d}" if n else "")
    return [id_mov, t.strftime("%Y-%m-%d"), t.strftime("%H:%M:%S"), tipo, tipo_clase or "N/A",
            categoria, detalle, monto, instructor or "N/A", "", ""]


def siguiente_id(df: pd.DataFrame) -> str:
    nums = []
    if not df.empty:
        for v in df["ID"]:
            m = re.search(r"(\d+)$", str(v))
            if m:
                nums.append(int(m.group(1)))
    return f"STTOICA-{(max(nums) if nums else 0) + 1:02d}"


def ajustar_clases(id_alumna: str, nombre: str, delta: int):
    al = df_hoja("alumnas")
    if al.empty:
        return
    m = al["ID"].str.strip().str.upper() == str(id_alumna).strip().upper() if str(id_alumna).strip() else al["Nombre"] == nombre
    if not m.any():
        return
    idx = al[m].index[0]
    actual = parse_int(al.loc[idx, "Clases_Restantes"])
    if actual is None:
        return
    actualizar_celdas("alumnas", idx + 2, {"Clases_Restantes": max(0, actual + delta)})


def ocupacion(res: pd.DataFrame, fecha, hora, instructor) -> int:
    if res.empty:
        return 0
    m = ((res["Fecha"] == str(fecha)) & (res["Hora"] == hora) &
         (res["Instructor"] == instructor) & (res["Estatus"] == "Confirmada"))
    return int(m.sum())


def reservas_de(res: pd.DataFrame, id_al: str, nombre: str) -> pd.DataFrame:
    if res.empty:
        return res
    ids = res["ID_Alumna"].str.strip().str.upper()
    return res[(ids == id_al.upper()) | ((ids == "") & (res["Alumna"] == nombre))]


# ------------------------------------------------------------------
# 5. CONTROL DE ACCESO
# ------------------------------------------------------------------
def acceso_admin() -> bool:
    if st.session_state.get("admin_ok"):
        return True

    clave = None
    try:
        if "admin_password" in st.secrets:
            clave = str(st.secrets["admin_password"])
        elif "gcp_service_account" in st.secrets and "admin_password" in st.secrets["gcp_service_account"]:
            clave = str(st.secrets["gcp_service_account"]["admin_password"])
    except Exception:
        pass

    if not clave:
        clave = "sttoica2026"

    restante = st.session_state.get("bloqueo_hasta", 0) - time.time()
    if restante > 0:
        st.error(f"Demasiados intentos. Espera {int(restante)} segundos.")
        return False

    pwd = st.text_input("Ingresa tu contraseña de Dueño:", type="password")
    if pwd:
        if hmac.compare_digest(pwd.encode(), clave.encode()):
            st.session_state["admin_ok"] = True
            st.session_state["intentos"] = 0
            st.rerun()
        else:
            st.session_state["intentos"] = st.session_state.get("intentos", 0) + 1
            if st.session_state["intentos"] >= MAX_INTENTOS:
                st.session_state["bloqueo_hasta"] = time.time() + BLOQUEO_SEG
                st.session_state["intentos"] = 0
            st.error("Contraseña incorrecta.")
    else:
        st.warning("🔒 Ingresa la contraseña de administrador para ver el panel completo.")
    return False


# ------------------------------------------------------------------
# 6. VISTA ALUMNA
# ------------------------------------------------------------------
def vista_alumna():
    html(tarjeta(f"<p style='font-size:0.85rem;color:{GUINDA} !important;font-weight:700;letter-spacing:1px;margin:0;'>"
                 "PORTAL DE RESERVAS STTOICA</p>"))

    df_al = preparar_alumnas()
    if df_al.empty or "ID" not in df_al.columns:
        st.warning("⚠️ El sistema de matrículas se está configurando. Vuelve a intentarlo en un momento.")
        return

    matricula = st.text_input("Ingresa tu ID o Matrícula personal (Ej. STTOICA-01):").strip()
    if not matricula:
        return

    match = df_al[df_al["ID"].str.strip().str.upper() == matricula.upper()]
    if match.empty:
        st.warning("⚠️ Matrícula no encontrada. Verifica tu ID o comunícate al estudio.")
        return

    info = match.iloc[0]
    nombre = info.get("Nombre", "Alumna")
    id_al = str(info["ID"]).strip()
    estado = info["Estado"]
    restantes = parse_int(info.get("Clases_Restantes", ""))
    vence = parse_fecha(info.get("Vencimiento", ""))

    st.success(f"✨ ¡Hola, {nombre}!")

    ur = st.session_state.get("ultima_reserva")
    if ur and ur["id"] == id_al:
        st.success(f"Reserva confirmada: {ur['fecha']} a las {ur['hora']} con {ur['instructora']}.")
        numero = ""
        try:
            numero = str(st.secrets.get("whatsapp_estudio", "")).strip()
        except Exception:
            pass
        if numero:
            msg = (f"Hola, soy {nombre} ({id_al}). Confirmo mi clase del {ur['fecha']} "
                   f"a las {ur['hora']} con {ur['instructora']}.")
            st.link_button("📲 Enviar confirmación por WhatsApp", f"https://wa.me/{numero}?text={quote(msg)}", width="stretch")

    html(mini_cards([
        ("CLASES RESTANTES", restantes if restantes is not None else "—"),
        ("VENCE", vence.strftime("%d/%m/%Y") if vence else "—"),
        ("ESTATUS", estado),
    ]))

    res = df_hoja("reservas")

    # Mis reservas
    proximas = []
    mias = reservas_de(res, id_al, nombre)
    if not mias.empty:
        for idx, r in mias[mias["Estatus"] == "Confirmada"].iterrows():
            dt = slot_dt(r["Fecha"], r["Hora"])
            if dt and dt >= ahora():
                proximas.append((dt, idx, r))
        proximas.sort(key=lambda x: x[0])

    html(titulo("MIS PRÓXIMAS CLASES"))
    if not proximas:
        st.caption("Aún no tienes clases agendadas.")
    for dt, idx, r in proximas:
        puede = dt - ahora() >= timedelta(hours=HORAS_MIN_CANCELAR)
        html(tarjeta(
            f"<p style='margin:0;font-weight:700;color:#1A1817 !important;'>{dt.strftime('%d/%m/%Y')} · {escape(r['Hora'])}</p>"
            f"<p style='margin:0;font-size:0.8rem;color:{TEXTO_SUAVE} !important;'>Con {escape(r['Instructor'])}</p>"))
        if puede:
            if st.button("Cancelar esta clase", key=f"cx_{idx}", width="stretch"):
                actualizar_celdas("reservas", idx + 2, {"Estatus": "Cancelada"})
                ajustar_clases(id_al, nombre, +1)
                terminar("Clase cancelada. Tu lugar ha sido liberado y tu clase reintegrada.")
        else:
            st.caption(f"Solo se puede cancelar con {HORAS_MIN_CANCELAR} horas de anticipación.")

    # Agendar
    if estado != "Activa":
        mensajes = {
            "Pendiente": "❌ Tienes un pago pendiente. Comunícate a recepción para activar tu paquete.",
            "Vencida": "❌ Tu paquete de clases está VENCIDO. Comunícate a recepción para renovarlo.",
            "Sin clases": "❌ Ya usaste todas las clases de tu paquete. Comunícate a recepción para renovar.",
        }
        st.error(mensajes.get(estado, "Acceso denegado."))
        return

    html(titulo("AGENDAR NUEVA CLASE"))
    fecha = st.date_input("Fecha de la clase", value=hoy(), min_value=hoy(),
                          max_value=hoy() + timedelta(days=DIAS_ADELANTE))
    instructora = st.selectbox("Instructora", INSTRUCTORAS)

    horas_validas = [h for h in HORARIOS if slot_dt(str(fecha), h) and slot_dt(str(fecha), h) > ahora()]
    if not horas_validas:
        st.info("Ya no hay horarios disponibles para ese día. Elige otra fecha.")
        return

    def etiqueta(h):
        lugares = CUPO_MAX - ocupacion(res, fecha, h, instructora)
        return f"{h} · LLENO" if lugares <= 0 else f"{h} · quedan {lugares} lugares"

    horario = st.selectbox("Horario", horas_validas, format_func=etiqueta)
    lleno = CUPO_MAX - ocupacion(res, fecha, horario, instructora) <= 0
    if lleno:
        st.warning("Esa clase está llena. Elige otro horario o instructora.")

    if st.button("Confirmar Reserva", width="stretch", disabled=lleno):
        refrescar()
        res = df_hoja("reservas")
        mias = reservas_de(res, id_al, nombre)
        ya = (not mias.empty) and ((mias["Fecha"] == str(fecha)) & (mias["Hora"] == horario) &
                                   (mias["Estatus"] == "Confirmada")).any()

        if ya:
            st.error("Ya tienes una clase agendada a esa misma hora.")
        elif ocupacion(res, fecha, horario, instructora) >= CUPO_MAX:
            st.error("Lo sentimos, alguien tomó el último lugar. Elige otro horario.")
        elif restantes is not None and restantes <= 0:
            st.error("No cuentas con clases disponibles para agendar.")
        else:
            fila = fila_por_header("reservas", {
                "Fecha": str(fecha), "Hora": horario, "Alumna": nombre, "Instructor": instructora,
                "Estatus": "Confirmada", "Timestamp": ahora().strftime("%Y-%m-%d %H:%M:%S"),
                "ID_Alumna": id_al, "Asistencia": "", "Pago_Registrado": ""})
            hojas()["reservas"].append_row(fila, value_input_option="RAW")

            # Descuento inmediato de clase
            ajustar_clases(id_al, nombre, -1)

            st.session_state["ultima_reserva"] = {
                "id": id_al, "fecha": fecha.strftime("%d/%m/%Y"), "hora": horario, "instructora": instructora}
            terminar("¡Clase agendada con éxito!")


# ------------------------------------------------------------------
# 7. VISTA ADMINISTRADOR
# ------------------------------------------------------------------
def tab_inicio(fin, al, res):
    mes = hoy().strftime("%Y-%m")
    ing_mes = gas_mes = 0.0
    tiene_fin = not fin.empty and {"Monto_Num", "Tipo", "Mes"} <= set(fin.columns)
    if tiene_fin:
        fm = fin[fin["Mes"] == mes]
        ing_mes = fm[fm["Tipo"] == "Ingreso"]["Monto_Num"].sum()
        gas_mes = fm[fm["Tipo"] == "Gasto"]["Monto_Num"].sum()

    clases_hoy = 0 if res.empty else int(((res["Fecha"] == str(hoy())) & (res["Estatus"] == "Confirmada")).sum())
    activas = 0 if al.empty else int((al["Estado"] == "Activa").sum())
    html(mini_cards([("CLASES HOY", clases_hoy), ("ALUMNAS ACTIVAS", activas), ("GASTO DEL MES", formato_moneda(gas_mes))]))

    if tiene_fin:
        total_ing = fin[fin["Tipo"] == "Ingreso"]["Monto_Num"].sum()
        total_gas = fin[fin["Tipo"] == "Gasto"]["Monto_Num"].sum()
        html(f"""<div style="background-color:{GUINDA};border-radius:20px;padding:25px;color:white;display:flex;justify-content:space-between;align-items:center;box-shadow:0 8px 18px rgba(74,21,37,0.25);margin-bottom:20px;">
<div><p style="margin:0;font-size:0.75rem;color:{CREMA_OSCURO} !important;letter-spacing:1.5px;text-transform:uppercase;">Balance Actual</p>
<h1 style="margin:5px 0 0 0;font-size:2.1rem;font-weight:800;color:#FFFFFF !important;">{formato_moneda(total_ing - total_gas)}</h1>
<p style="margin:6px 0 0 0;font-size:0.72rem;color:{CREMA_OSCURO} !important;">Este mes: {formato_moneda(ing_mes - gas_mes)}</p></div>
<div style="text-align:right;"><p style="margin:0;font-size:0.75rem;color:{CREMA_OSCURO} !important;">Ingresos</p>
<p style="margin:0;font-size:0.95rem;color:#A5D6A7 !important;font-weight:bold;">+${total_ing:,.2f}</p>
<p style="margin:8px 0 0 0;font-size:0.75rem;color:{CREMA_OSCURO} !important;">Gastos</p>
<p style="margin:0;font-size:0.95rem;color:#EF9A9A !important;font-weight:bold;">-${total_gas:,.2f}</p></div></div>""")

    alertas = []
    if not al.empty:
        for _, a in al.iterrows():
            est, nom = a["Estado"], escape(str(a["Nombre"]))
            venc = parse_fecha(a.get("Vencimiento", ""))
            rest = parse_int(a.get("Clases_Restantes", ""))
            if est == "Pendiente":
                alertas.append((nom, "Pago pendiente", "Pendiente"))
            elif est == "Vencida":
                alertas.append((nom, f"Venció el {venc.strftime('%d/%m/%Y')}" if venc else "Paquete vencido", "Vencida"))
            elif est == "Sin clases":
                alertas.append((nom, "Sin clases disponibles", "Sin clases"))
            elif venc and (venc - hoy()).days <= 7:
                alertas.append((nom, f"Vence el {venc.strftime('%d/%m/%Y')}", "Por vencer"))
            elif rest is not None and rest <= 1:
                alertas.append((nom, f"Le queda {rest} clase", "Por vencer"))
    html(titulo("ALUMNAS QUE REQUIEREN ATENCIÓN"))
    if not alertas:
        st.caption("Todo en orden: no hay pagos pendientes ni paquetes por vencer. ✨")
    for nom, detalle, est in alertas[:8]:
        html(tarjeta(f"<div style='display:flex;justify-content:space-between;align-items:center;gap:10px;'>"
                     f"<div><p style='margin:0;font-weight:700;color:#1A1817 !important;font-size:0.95rem;'>{nom}</p>"
                     f"<p style='margin:0;font-size:0.75rem;color:{TEXTO_SUAVE} !important;'>{detalle}</p></div>{badge(est)}</div>"))
    if len(alertas) > 8:
        st.caption(f"y {len(alertas) - 8} más en la pestaña Alumnas.")

    if tiene_fin and "Tipo" in fin.columns:
        html(titulo("MOVIMIENTOS RECIENTES"))
        for _, row in fin.tail(4).iloc[::-1].iterrows():
            es_ing = row["Tipo"] == "Ingreso"
            color = VERDE if es_ing else ROJO
            inst = row.get("Instructor", "")
            valido = inst not in ["N/a", "N/A", "", "None", "nan", "Estudio"]
            sub = f"{inst} • {row.get('Fecha', '')}" if valido else row.get("Fecha", "")
            html(tarjeta(
                f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                f"<div style='display:flex;align-items:center;gap:14px;'>"
                f"<div style='background-color:{CREMA};border-radius:50%;width:44px;height:44px;display:flex;justify-content:center;align-items:center;font-size:1.2rem;'>{'💵' if es_ing else '🛒'}</div>"
                f"<div><p style='margin:0;font-weight:700;color:#1A1817 !important;font-size:0.95rem;'>{escape(str(row.get('Categoria', 'N/A')))}</p>"
                f"<p style='margin:0;font-size:0.75rem;color:{TEXTO_SUAVE} !important;'>{escape(str(sub))}</p></div></div>"
                f"<p style='margin:0;font-weight:700;color:{color} !important;'>{'+' if es_ing else '-'}${float(row['Monto_Num']):,.2f}</p></div>"))
    elif not tiene_fin:
        st.info("No hay movimientos registrados.")


def tab_asistencia(res):
    html(titulo("CONTROL DE ASISTENCIA Y RESERVAS"))
    fecha = st.date_input("Ver clases del día:", value=hoy(), key="filtro_fecha")
    if res.empty:
        st.info("Aún no hay reservas registradas en el sistema.")
        return

    dia = res[(res["Fecha"] == str(fecha)) & (res["Estatus"] != "Cancelada")]
    if dia.empty:
        st.info("No hay reservas para este día.")
        return

    asistieron = int((dia["Asistencia"] == "Asistió").sum())
    por_marcar = int((dia["Asistencia"] == "").sum())
    html(mini_cards([("AGENDADAS", len(dia)), ("ASISTIERON", asistieron), ("POR MARCAR", por_marcar)]))

    grupos = sorted(dia.groupby(["Hora", "Instructor"]), key=lambda g: (hora_a_time(g[0][0]), g[0][1]))
    for (hora, instr), g in grupos:
        html(tarjeta(
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<p style='margin:0;font-weight:700;color:{GUINDA} !important;'>{escape(hora)} · {escape(instr)}</p>"
            f"<p style='margin:0;font-size:0.8rem;color:{TEXTO_SUAVE} !important;'>{len(g)}/{CUPO_MAX} lugares</p></div>"
            f"{barra_ocupacion(len(g), CUPO_MAX)}"))

        for idx, r in g.iterrows():
            c1, c2, c3, c4 = st.columns([4, 1, 1, 1])
            estado = r["Asistencia"] or "Por marcar"
            c1.markdown(f"<p style='margin:6px 0;color:#1A1817 !important;font-weight:600;'>{escape(r['Alumna'])} &nbsp;{badge(estado)}</p>",
                        unsafe_allow_html=True)
            if c2.button("✔", key=f"ok_{idx}", help="Asistió"):
                actualizar_celdas("reservas", idx + 2, {"Asistencia": "Asistió"})
                terminar(f"{r['Alumna']}: Asistió")
            if c3.button("✖", key=f"no_{idx}", help="No asistió"):
                actualizar_celdas("reservas", idx + 2, {"Asistencia": "No asistió"})
                terminar(f"{r['Alumna']}: No asistió")
            if c4.button("🚫", key=f"cx_adm_{idx}", help="Cancelar reserva"):
                actualizar_celdas("reservas", idx + 2, {"Estatus": "Cancelada"})
                ajustar_clases(r["ID_Alumna"], r["Alumna"], +1)
                terminar("Reserva cancelada.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("Al registrar sueldos se paga una vez por clase: $300 si asistió alguien, $200 si nadie asistió.")
    if st.button("💸 Registrar sueldos de este día", width="stretch"):
        registrar_sueldos(dia, fecha)


def registrar_sueldos(dia: pd.DataFrame, fecha):
    filas, lote, omitidas, n = [], [], 0, 0
    header = leer("reservas")[0]
    col_pago = header.index("Pago_Registrado") + 1
    for (hora, instr), g in dia.groupby(["Hora", "Instructor"]):
        if (g["Pago_Registrado"] == "Sí").any():
            continue
        if (g["Asistencia"] == "").any():
            omitidas += 1
            continue
        tipo_clase = "DICTADAS" if (g["Asistencia"] == "Asistió").any() else "NO FUE AL ESTUDIO"
        n += 1
        filas.append(fila_finanza("Gasto", tipo_clase, "Sueldos", f"Sueldo {instr} {fecha} {hora}",
                                  TARIFAS[tipo_clase], instr, n))
        lote += [{"range": rowcol_to_a1(i + 2, col_pago), "values": [["Sí"]]} for i in g.index]
    if not filas:
        st.warning("No hay sueldos por registrar: ya se pagaron o faltan clases por marcar asistencia."
                   if omitidas else "No hay sueldos pendientes para este día.")
        return
    hojas()["finanzas"].append_rows(filas, value_input_option="RAW")
    hojas()["reservas"].batch_update(lote, value_input_option="RAW")
    total = sum(f[7] for f in filas)
    extra = f" ({omitidas} clase(s) sin completar)" if omitidas else ""
    terminar(f"Sueldos registrados: {len(filas)} clase(s), {formato_moneda(total)}{extra}")


def tab_alumnas(al):
    html(titulo("DIRECTORIO DE ALUMNAS"))
    if al.empty:
        st.info("Aún no hay alumnas registradas.")
    else:
        cards = ""
        for _, a in al.iterrows():
            rest = parse_int(a.get("Clases_Restantes", ""))
            venc = parse_fecha(a.get("Vencimiento", ""))
            cards += tarjeta(
                f"<div style='display:flex;justify-content:space-between;align-items:center;gap:10px;'>"
                f"<div><p style='margin:0;font-weight:700;color:#1A1817 !important;'>{escape(str(a['Nombre']))}</p>"
                f"<p style='margin:0;font-size:0.75rem;color:{TEXTO_SUAVE} !important;'>{escape(str(a['ID']))} · {escape(str(a.get('Paquete', '')) or 'Sin paquete')}</p>"
                f"<p style='margin:2px 0 0 0;font-size:0.75rem;color:{TEXTO_SUAVE} !important;'>"
                f"Clases: {rest if rest is not None else '—'} · Vence: {venc.strftime('%d/%m/%Y') if venc else '—'}</p></div>"
                f"{badge(a['Estado'])}</div>")
        html(cards)

    with st.expander("➕ Nueva alumna"):
        with st.form("form_nueva_alumna", clear_on_submit=True):
            nombre = st.text_input("Nombre completo")
            tel = st.text_input("Teléfono")
            paquete = st.selectbox("Paquete", list(PAQUETES.keys()))
            monto = st.number_input("Monto pagado ($ MXN). Deja 0 si aún no paga", min_value=0.0, step=50.0, value=0.0)
            enviar = st.form_submit_button("Guardar alumna", width="stretch")
        if enviar:
            if not nombre.strip():
                st.error("Escribe el nombre de la alumna.")
            else:
                nuevo_id = siguiente_id(al)
                datos = {"ID": nuevo_id, "Nombre": nombre.strip(), "Telefono": tel.strip(), "Estatus_Pago": "Pendiente"}
                if monto > 0:
                    pq = PAQUETES[paquete]
                    datos.update({"Estatus_Pago": "Pagado", "Paquete": paquete, "Clases_Restantes": pq["clases"],
                                  "Vencimiento": str(hoy() + timedelta(days=pq["dias"]))})
                    hojas()["finanzas"].append_row(
                        fila_finanza("Ingreso", f"Paquete {paquete}", "Paquete de clases", f"Pago {nombre.strip()}", monto, "Estudio"),
                        value_input_option="RAW")
                hojas()["alumnas"].append_row(fila_por_header("alumnas", datos), value_input_option="RAW")
                terminar(f"Alumna registrada con ID {nuevo_id}")

    if al.empty:
        return
    opciones = {f"{r['Nombre']} · {r['ID']}": idx for idx, r in al.iterrows()}

    with st.expander("💳 Registrar pago / renovar paquete"):
        with st.form("form_pago", clear_on_submit=True):
            sel = st.selectbox("Alumna", list(opciones.keys()))
            paquete = st.selectbox("Paquete", list(PAQUETES.keys()))
            monto = st.number_input("Monto pagado ($ MXN)", min_value=0.0, step=50.0, value=0.0)
            enviar = st.form_submit_button("Registrar pago", width="stretch")
        if enviar:
            if monto <= 0:
                st.error("Escribe el monto pagado.")
            else:
                idx = opciones[sel]
                a = al.loc[idx]
                pq = PAQUETES[paquete]
                rest = parse_int(a.get("Clases_Restantes", "")) or 0
                conserva = rest if a["Estado"] == "Activa" else 0
                actualizar_celdas("alumnas", idx + 2, {
                    "Estatus_Pago": "Pagado", "Paquete": paquete,
                    "Clases_Restantes": pq["clases"] + conserva,
                    "Vencimiento": str(hoy() + timedelta(days=pq["dias"]))})
                hojas()["finanzas"].append_row(
                    fila_finanza("Ingreso", f"Paquete {paquete}", "Paquete de clases", f"Pago {a['Nombre']}", monto, "Estudio"),
                    value_input_option="RAW")
                terminar(f"Pago registrado para {a['Nombre']}")

    with st.expander("✏️ Cambiar estatus manualmente"):
        with st.form("form_estatus", clear_on_submit=True):
            sel = st.selectbox("Alumna ", list(opciones.keys()))
            nuevo = st.selectbox("Nuevo estatus", ["Pagado", "Pendiente", "Vencido"])
            enviar = st.form_submit_button("Actualizar estatus", width="stretch")
        if enviar:
            actualizar_celdas("alumnas", opciones[sel] + 2, {"Estatus_Pago": nuevo})
            terminar("Estatus actualizado.")


def tab_finanzas():
    html(tarjeta(f"<p style='font-size:0.85rem;color:{GUINDA} !important;font-weight:700;letter-spacing:1px;margin:0;'>"
                 "NUEVO REGISTRO FINANCIERO</p>"))
    tipo = st.selectbox("Tipo de Movimiento", ["Gasto", "Ingreso"])
    categoria, instructor, tipo_clase, monto = "", "", "", 0.0
    aviso = (f"background-color:{CREMA_OSCURO};padding:12px;border-radius:10px;color:{GUINDA};"
             "font-weight:600;text-align:center;margin-top:10px;")

    if tipo == "Gasto":
        categoria = st.selectbox("Categoría", ["Renta", "Servicios", "Sueldos"])
        if categoria in ["Renta", "Servicios"]:
            monto = st.number_input("Monto ($ MXN)", min_value=0.0, step=50.0, value=1000.0)
        else:
            personal = st.selectbox("Personal", ["Instructoras", "Contador"])
            if personal == "Instructoras":
                instructor = st.selectbox("Nombre de Instructora", INSTRUCTORAS)
                tipo_clase = st.selectbox("Estatus de Clase", list(TARIFAS.keys()))
                monto = TARIFAS[tipo_clase]
                html(f"<div style='{aviso}'>✨ Pago automático asignado: ${monto:,.2f} MXN</div>")
            else:
                instructor, tipo_clase, monto = "Contador", "Honorarios contables", 500.0
                html(f"<div style='{aviso}'>✨ Honorarios aplicados: $500.00 MXN</div>")
    else:
        categoria, instructor, tipo_clase = "Ingreso General", "Estudio", "Pago de cliente"
        monto = st.number_input("Monto del Ingreso ($ MXN)", min_value=0.0, step=50.0, value=500.0)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Guardar Movimiento", width="stretch"):
        hojas()["finanzas"].append_row(
            fila_finanza(tipo, tipo_clase, categoria, f"App - {categoria}", monto, instructor), value_input_option="RAW")
        terminar("¡Movimiento guardado con éxito!")


def tab_datos(fin, res):
    if fin.empty or "Monto_Num" not in fin.columns:
        st.info("Aún no hay registros suficientes para mostrar gráficas y datos.")
        return

    html(titulo("ANÁLISIS VISUAL DE GASTOS E INGRESOS"))
    meses = sorted(fin["Mes"].unique(), reverse=True)
    periodo = st.selectbox("Periodo", ["Todos"] + meses)
    df_p = fin if periodo == "Todos" else fin[fin["Mes"] == periodo]

    if fin["Mes"].nunique() > 0:
        st.markdown(f"<p style='font-size:0.9rem;color:{GUINDA} !important;font-weight:600;margin-bottom:6px;'>Ingresos vs Gastos por mes</p>",
                    unsafe_allow_html=True)
        st.altair_chart(grafica_mensual(fin), width="stretch", theme=None)

    gastos = df_p[df_p["Tipo"] == "Gasto"]
    ingresos = df_p[df_p["Tipo"] == "Ingreso"]

    def seccion(texto, serie, color, fmt="$,.0f"):
        st.markdown(f"<p style='font-size:0.9rem;color:{GUINDA} !important;font-weight:600;margin:15px 0 6px 0;'>{texto}</p>",
                    unsafe_allow_html=True)
        st.altair_chart(grafica_barras(serie, color, fmt), width="stretch", theme=None)

    if not gastos.empty and "Categoria" in gastos.columns:
        seccion("Distribución de gastos por categoría", gastos.groupby("Categoria")["Monto_Num"].sum(), GUINDA)
    if not ingresos.empty and "Categoria" in ingresos.columns:
        seccion("Ingresos por categoría", ingresos.groupby("Categoria")["Monto_Num"].sum(), "#7FB58A")
    if not gastos.empty and "Instructor" in gastos.columns:
        personal = gastos[~gastos["Instructor"].isin(["N/a", "N/A", "", "Estudio", "None", "Nan"])]
        if not personal.empty:
            seccion("Pagos acumulados por personal", personal.groupby("Instructor")["Monto_Num"].sum(), ROSA_PALO)

    if not res.empty:
        conf = res[res["Estatus"] != "Cancelada"]
        if periodo != "Todos":
            conf = conf[conf["Fecha"].str[:7] == periodo]
        if not conf.empty:
            seccion("Horarios más populares (reservas)", conf.groupby("Hora").size(), GUINDA, ",.0f")
            seccion("Reservas por instructora", conf.groupby("Instructor").size(), ROSA_PALO, ",.0f")

    html(f"<hr style='border-color:{CREMA_OSCURO};margin:20px 0;'>")
    html(titulo("HISTORIAL FINANCIERO Y FILTROS"))
    col1, col2 = st.columns(2)
    df_f = df_p.drop(columns=["Monto_Num", "Mes"], errors="ignore")
    with col1:
        if "Tipo" in df_f.columns:
            sel = st.selectbox("Filtrar Tipo", ["Todos"] + list(df_f["Tipo"].unique()))
            if sel != "Todos":
                df_f = df_f[df_f["Tipo"] == sel]
    with col2:
        if "Instructor" in df_f.columns:
            sel = st.selectbox("Filtrar Personal", ["Todos"] + list(df_f["Instructor"].unique()))
            if sel != "Todos":
                df_f = df_f[df_f["Instructor"] == sel]

    st.dataframe(df_f, width="stretch")
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button("📥 Descargar Reporte CSV", data=df_f.to_csv(index=False).encode("utf-8"),
                       file_name=f"reporte_sttoica_{hoy().strftime('%Y%m%d')}.csv", mime="text/csv", width="stretch")


def vista_admin():
    fin, al, res = preparar_fin(), preparar_alumnas(), df_hoja("reservas")
    t1, t2, t3, t4, t5 = st.tabs(["🏠 Inicio", "📅 Clases", "👩 Alumnas", "💰 Finanzas", "📊 Datos"])
    with t1:
        tab_inicio(fin, al, res)
    with t2:
        tab_asistencia(res)
    with t3:
        tab_alumnas(al)
    with t4:
        tab_finanzas()
    with t5:
        tab_datos(fin, res)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Cerrar sesión de administrador", width="stretch"):
        st.session_state["admin_ok"] = False
        st.rerun()


# ------------------------------------------------------------------
# 8. EJECUCIÓN PRINCIPAL
# ------------------------------------------------------------------
try:
    hojas()

    html(f"""<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;">
<div><h2 style="margin:0;color:{GUINDA} !important;font-size:1.7rem;font-weight:800;letter-spacing:1px;">STTOICA STUDIO</h2>
<p style="margin:0;color:{TEXTO_SUAVE} !important;font-size:0.85rem;letter-spacing:2px;text-transform:uppercase;">Elevate your essence</p></div>
<div style="background-color:{CREMA_OSCURO};border-radius:50%;width:45px;height:45px;display:flex;justify-content:center;align-items:center;font-size:1.3rem;border:1px solid {BORDE};">🧘‍♀️</div></div>""")

    if "flash" in st.session_state:
        st.toast(st.session_state.pop("flash"), icon="✅")

    modo = st.radio("¿Cómo deseas ingresar?", ["Soy Alumna (Agendar Clases)", "Administrador (Dueño)"], horizontal=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if modo == "Soy Alumna (Agendar Clases)":
        vista_alumna()
    elif acceso_admin():
        vista_admin()

except Exception as e:
    st.error(f"Error de conexión: {e}")
