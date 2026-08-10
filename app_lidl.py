#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ThinkCore · Enterprise Retail Scheduling
Refactored UI – Streamlit interface for generatore_turni_v6.py
v2.0 – Design system aligned to shift & schedule domain
"""

import streamlit as st
import plotly.graph_objects as go
from write_engine import write_shifts_surgical
import cloud_storage
import plotly.express as px
import pandas as pd
import os, sys, types, io, contextlib, datetime

# ── PAGE CONFIG ──────────────────────────────────────────────
st.set_page_config(
    page_title="ThinkCore · Gestione Turni",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── DESIGN SYSTEM · COLOUR & TYPOGRAPHY ─────────────────────
NAVY    = "#0B1D2E"
SLATE   = "#1B2A3A"
STEEL   = "#1F3A56"
AZURE   = "#1C7EEA"    # primary accent
CYAN    = "#00B4D8"
MINT    = "#10B981"
AMBER   = "#F59E0B"
CRIMSON = "#EF4444"
ICE     = "#F8FAFC"
WHITE   = "#FFFFFF"
MUTED   = "#94A3B8"
BORDER  = "#E2E8F0"

# ══════════════════════════════════════════════════════════════
# GLOBAL CSS – enterprise look & feel
# ══════════════════════════════════════════════════════════════
CSS = f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400..700&display=swap');

  :root {{
    --navy: {NAVY};
    --steel: {STEEL};
    --azure: {AZURE};
    --mint: {MINT};
    --amber: {AMBER};
    --crimson: {CRIMSON};
    --ice: {ICE};
    --white: {WHITE};
    --muted: {MUTED};
    --border: {BORDER};
  }}

  html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
    background: {ICE};
    color: #1E293B;
  }}

  /* ── SIDEBAR ── */
  section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {NAVY} 0%, {SLATE} 100%);
    border-right: 1px solid rgba(255,255,255,0.05);
  }}
  section[data-testid="stSidebar"] * {{
    color: {WHITE} !important;
  }}
  section[data-testid="stSidebar"] label {{
    color: #94A3B8 !important;
    font-size: .72rem;
    letter-spacing: .08em;
    text-transform: uppercase;
    font-weight: 600;
  }}
  section[data-testid="stSidebar"] .stButton > button {{
    background: {AZURE} !important;
    border: none !important;
    color: white !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: 0.2s;
  }}
  section[data-testid="stSidebar"] .stButton > button:hover {{
    background: #1665C0 !important;
    box-shadow: 0 4px 12px rgba(28,126,234,0.4);
  }}
  section[data-testid="stSidebar"] .stButton > button:disabled {{
    background: #334155 !important;
    color: #94A3B8 !important;
    box-shadow: none;
  }}

  /* ── TOP BANNER ── */
  .top-banner {{
    background: linear-gradient(135deg, {NAVY} 0%, {STEEL} 100%);
    border-radius: 18px;
    padding: 36px 48px;
    margin-bottom: 28px;
    box-shadow: 0 12px 24px -8px rgba(11,29,46,0.25);
    position: relative;
    overflow: hidden;
  }}
  .top-banner::after {{
    content: '';
    position: absolute;
    right: -40px;
    bottom: -40px;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(255,255,255,0.06) 0%, transparent 70%);
    border-radius: 50%;
  }}
  .top-banner h1 {{
    color: {WHITE};
    margin: 0;
    font-size: 1.8rem;
    font-weight: 700;
    letter-spacing: -0.02em;
  }}
  .top-banner p {{
    color: #A0BDDB;
    margin: 6px 0 0;
    font-size: .95rem;
    font-weight: 400;
  }}

  /* ── KPI CARDS ── */
  .kpi-card {{
    background: {WHITE};
    border-radius: 14px;
    padding: 24px 28px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 8px rgba(0,0,0,0.03);
    border-left: 5px solid {AZURE};
    transition: box-shadow 0.2s;
  }}
  .kpi-card.warn  {{ border-left-color: {AMBER}; }}
  .kpi-card.ok    {{ border-left-color: {MINT}; }}
  .kpi-card.alert {{ border-left-color: {CRIMSON}; }}
  .kpi-value {{
    font-family: 'Inter', sans-serif;
    font-size: 2.2rem;
    font-weight: 700;
    color: {NAVY};
    line-height: 1;
    margin-bottom: 6px;
  }}
  .kpi-label {{
    font-size: .72rem;
    letter-spacing: .09em;
    text-transform: uppercase;
    color: {MUTED};
    font-weight: 600;
  }}
  .kpi-delta {{
    font-size: .85rem;
    font-weight: 500;
    margin-top: 8px;
    display: flex;
    align-items: center;
    gap: 4px;
  }}

  /* ── TYPOGRAPHY HELPERS ── */
  .section-title {{
    font-size: .7rem;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: {MUTED};
    margin: 28px 0 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid {BORDER};
  }}
  .viol-pill {{
    background: #FEF2F2;
    border: 1px solid #FECACA;
    color: #991B1B;
    border-radius: 8px;
    padding: 6px 16px;
    font-size: .82rem;
    font-weight: 500;
    margin: 4px 0;
    display: inline-block;
  }}
  .empty-state {{
    text-align: center;
    padding: 80px 40px;
    color: {MUTED};
  }}

  /* ── MISC ── */
  #MainMenu, footer {{ visibility: hidden; }}
  header[data-testid="stHeader"] {{ background: transparent; }}
  .block-container {{ padding-top: 1.8rem; }}
  .stTabs [data-baseweb="tab-list"] {{ gap: 2px; background: transparent; }}
  .stTabs [data-baseweb="tab"] {{
    border-radius: 10px 10px 0 0;
    padding: 12px 24px;
    font-weight: 600;
    background: transparent;
    color: {MUTED};
  }}
  .stTabs [aria-selected="true"] {{
    background: {WHITE} !important;
    color: {AZURE} !important;
    border-bottom: 3px solid {AZURE} !important;
  }}

  /* scenario selector styling */
  .scenario-selector {{
    background: {WHITE};
    border-radius: 12px;
    padding: 12px 20px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
  }}
</style>
"""


# ══════════════════════════════════════════════════════════════
# ENGINE & HELPERS (unchanged logic)
# ══════════════════════════════════════════════════════════════
ENGINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'generatore_turni_v6.py')

def run_engine(xlsx_path, extra_argv=None):
    argv = [ENGINE_PATH, xlsx_path, '--no-open'] + (extra_argv or [])
    old_argv, old_cwd = sys.argv[:], os.getcwd()
    out_buf, err_buf = io.StringIO(), io.StringIO()
    try:
        os.chdir(os.path.dirname(os.path.abspath(xlsx_path)))
        sys.argv = argv
        mod = types.ModuleType('_engine'); mod.__file__ = ENGINE_PATH
        src = open(ENGINE_PATH, encoding='utf-8').read()
        with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
            try:
                exec(compile(src, ENGINE_PATH, 'exec'), mod.__dict__)
            except SystemExit:
                pass
    finally:
        sys.argv = old_argv
        os.chdir(old_cwd)
    return mod, out_buf.getvalue(), err_buf.getvalue()

def kpi(value, label, delta=None, kind='default'):
    dc = MINT if (delta and ('✅' in str(delta) or '+' in str(delta))) else CRIMSON
    dh = f'<div class="kpi-delta" style="color:{dc}">{delta}</div>' if delta else ''
    return (f'<div class="kpi-card {kind}"><div class="kpi-value">{value}</div>'
            f'<div class="kpi-label">{label}</div>{dh}</div>')

def hms(h):
    hh = int(h)
    mm = int(round((h - hh) * 60))
    return f"{hh:02d}:{mm:02d}"

class ScenarioView:
    """Active view on a scenario produced by --compare."""
    def __init__(self, m, idx):
        sc = m.SCENARI[idx]
        self.idx = idx
        self.seed = sc['seed']
        self.cost = sc['cost']
        # Static fields from main module
        for attr in ('req_d', 'SLOTS', 'REQ', 'ENTRY', 'CLOSE', 'WEEK',
                     'ASSENTI', 'comp', 'YTD', 'A'):
            setattr(self, attr, getattr(m, attr, None))
        # Employees with scenario overtime / effective hours
        emp_ot, emp_mh = sc['emp_ot'], sc['emp_mh_eff']
        self.EMP = [dict(e, ot=emp_ot.get(e['id'], e['ot']),
                         mh_eff=emp_mh.get(e['id'], e.get('mh_eff', e['mh'])))
                   for e in m.EMP]
        self.shifts      = sc['shifts']
        self.P           = sc['P']
        self.PR          = sc['PR']
        self.OT_DAY      = sc['OT_DAY']
        self.DUR         = sc['DUR']
        self.SEAM_BRIDGE = sc['SEAM_BRIDGE']
        self.sched       = sc['sched']
        self.DAY_LABEL   = sc['day_label']
        self.viol        = sc['viol']

def scenario_label(sc, idx, is_best):
    base = f"Scenario {idx+1} (seed {sc['seed']})"
    tag = "  ⭐ scelto dal motore" if is_best else ""
    return f"{base} — violazioni: {sc['viol_n']}{tag}"

DAYS_FULL  = ['Lunedì','Martedì','Mercoledì','Giovedì','Venerdì','Sabato','Domenica']
DAYS_SHORT = ['Lun','Mar','Mer','Gio','Ven','Sab','Dom']

# ── CHARTS (identical logic, minor style refinements) ─────
def gantt(m, d):
    rows=[]
    for e in m.EMP:
        s = m.shifts[e['id']][d]
        if s is None: continue
        rows.append(dict(
            Dipendente=e['name'],
            Inizio=datetime.datetime(2000,1,1)+datetime.timedelta(hours=s[0]),
            Fine  =datetime.datetime(2000,1,1)+datetime.timedelta(hours=s[1]),
            Ore=round(s[1]-s[0],2),
            Ruolo=e['role'],
            OT='★ Straordinario' if m.OT_DAY[e['id']][d]>0 else 'Ordinario'))
    if not rows:
        return go.Figure().update_layout(paper_bgcolor='rgba(0,0,0,0)',
            annotations=[dict(text='Nessun turno', showarrow=False,
                              font=dict(color=MUTED, size=14))])
    df = pd.DataFrame(rows).sort_values('Inizio')
    fig = px.timeline(df, x_start='Inizio', x_end='Fine', y='Dipendente',
        color='Ruolo',
        color_discrete_map={'RESP': AZURE, 'ADDETTO': MINT},
        hover_data={'Ore':':.2f', 'OT':True, 'Inizio':False, 'Fine':False},
        labels={'Dipendente':'', 'Ruolo':'Ruolo'})
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', size=12, color=NAVY),
        margin=dict(l=10, r=10, t=10, b=10),
        height=max(300, len(rows)*34),
        xaxis=dict(tickformat='%H:%M', gridcolor=BORDER, title=''),
        yaxis=dict(autorange='reversed', title='', gridcolor=BORDER),
        legend=dict(orientation='h', y=1.04, x=1, xanchor='right',
                    bgcolor='rgba(0,0,0,0)'),
        bargap=0.28
    )
    entry = m.ENTRY[d]
    close = m.CLOSE[d] if isinstance(m.CLOSE, list) else m.CLOSE
    for hv, lb, col in [(entry, 'Apertura', '#A0BDDB'), (close, 'Chiusura', AMBER)]:
        t = datetime.datetime(2000,1,1) + datetime.timedelta(hours=hv)
        fig.add_vline(x=t, line_width=1.5, line_dash='dot', line_color=col,
            annotation_text=lb, annotation_position='top right',
            annotation_font_color=col, annotation_font_size=10)
    return fig

def heatmap(m):
    slots = m.SLOTS
    step = 2
    Z = []; TXT = []
    for d in range(7):
        rz = []; rt = []
        for i in range(0, min(len(slots), len(m.P[d]), len(m.REQ[d])), step):
            rz.append(m.P[d][i] - m.REQ[d][i])
            rt.append(f"{m.P[d][i]}/{m.REQ[d][i]}")
        Z.append(rz); TXT.append(rt)
    tl = [f"{int(s):02d}:{int((s%1)*60):02d}" if i%4==0 else '' for i,s in enumerate(slots[::step])]
    fig = go.Figure(go.Heatmap(z=Z, x=tl, y=DAYS_SHORT, text=TXT, texttemplate='%{text}',
        textfont=dict(size=8, family='Inter'),
        colorscale=[[0, CRIMSON], [.4, AMBER], [.55, '#FFFDE7'], [.7, '#C8E6C9'], [1, AZURE]],
        zmid=0, showscale=True,
        colorbar=dict(thickness=12,
            title=dict(text='Surplus/Scoperto', side='right', font=dict(size=10)),
            tickfont=dict(size=9))))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', size=11, color=NAVY),
        margin=dict(l=10, r=10, t=10, b=10), height=260,
        xaxis=dict(title='', tickangle=-45, tickfont=dict(size=9)),
        yaxis=dict(title='', autorange='reversed'))
    return fig

def daily_bars(m):
    req = [round(x,1) for x in m.req_d]
    sch = [round(x,1) for x in m.sched]
    ot  = [round(sum(m.OT_DAY[e['id']][d] for e in m.EMP),1) for d in range(7)]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=DAYS_SHORT, y=req, name='Richieste',
                         marker_color=BORDER, marker_line_width=0))
    fig.add_trace(go.Bar(x=DAYS_SHORT, y=[s-o for s,o in zip(sch, ot)],
                         name='Pianificate', marker_color=AZURE, marker_line_width=0))
    fig.add_trace(go.Bar(x=DAYS_SHORT, y=ot, name='Straordinari',
                         marker_color=AMBER, marker_line_width=0))
    fig.update_layout(
        barmode='overlay', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', size=12, color=NAVY),
        margin=dict(l=0, r=0, t=10, b=0), height=260,
        legend=dict(orientation='h', y=1.05, bgcolor='rgba(0,0,0,0)'),
        xaxis=dict(gridcolor=BORDER), yaxis=dict(gridcolor=BORDER, title='ore'))
    return fig

def ot_bar(m):
    data = sorted([(e['name'], e['ot']) for e in m.EMP if e['ot'] > 0],
                  key=lambda x: -x[1])
    if not data:
        return None
    ns, os_ = zip(*data)
    fig = go.Figure(go.Bar(x=list(os_), y=list(ns), orientation='h',
                           marker_color=AMBER, marker_line_width=0,
                           text=[f"{o:.2f}h" for o in os_], textposition='outside'))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', size=11, color=NAVY),
        margin=dict(l=0, r=60, t=10, b=0),
        height=max(180, len(data)*38),
        xaxis=dict(title='ore straordinario', gridcolor=BORDER),
        yaxis=dict(title='', autorange='reversed'))
    return fig


# ══════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ══════════════════════════════════════════════════════════════
def main():
    st.markdown(CSS, unsafe_allow_html=True)

    # ── SIDEBAR ──────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div style="display:flex; align-items:center; gap:12px; margin-bottom: 24px;">
          <div style="font-size:2.2rem;">⏱️</div>
          <div>
            <div style="font-weight:700; font-size:1.2rem; color:white; line-height:1.2;">ThinkCore</div>
            <div style="font-size:0.7rem; color:#94A3B8; letter-spacing:.05em;">TURNI RETAIL</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        gen_btn = st.button(
            "▶  GENERA TURNI",
            width='stretch',
            type="primary",
            disabled=(st.session_state.get('xlsx_uploader') is None)
        )

        st.markdown("---")
        uploaded = st.file_uploader(
            "MODELLO EXCEL",
            type=['xlsx'],
            key='xlsx_uploader',
            help="Carica TOOL_LIDL.xlsx – salvalo prima in Excel!"
        )
        st.markdown("---")
        st.markdown("**OPZIONI DI GENERAZIONE**")
        use_ot  = st.checkbox("Auto-straordinari", value=True)
        use_cmp = st.checkbox("Modalità scenari (5×)", value=True)
        use_co  = st.checkbox("Ottimizza costi OT", value=False)

        st.markdown("---")
        week_in = st.text_input("SETTIMANA ISO (opzionale)",
                                placeholder="es. 2026-W31")

        st.markdown("---")
        _backend = cloud_storage.backend_name()
        _backend_lbl = ('☁️ GitHub (persistente)' if _backend == 'github'
                        else '💾 Locale (non persistente su cloud)')
        st.markdown(f"""
        <div style="font-size:0.7rem; color:{MUTED}; margin-top: 24px;">
          ThinkCore v2.0 · © 2026<br>
          Stato: {_backend_lbl}
        </div>
        """, unsafe_allow_html=True)

    # ── MAIN CONTENT ────────────────────────────────────────
    st.markdown("""
    <div class="top-banner">
      <h1>⏱️ ThinkCore <span style="font-size:1rem; font-weight:400; color:#A0BDDB;">— Gestione Turni Retail</span></h1>
      <p>Pianificazione conforme · Copertura ottimizzata · Straordinari distribuiti equamente</p>
    </div>
    """, unsafe_allow_html=True)

    if 'result' not in st.session_state:
        st.session_state.result = None

    # ── GENERATION ──────────────────────────────────────────
    if gen_btn and uploaded:
        tmp = '/tmp/rotosmart'
        os.makedirs(tmp, exist_ok=True)
        path = os.path.join(tmp, uploaded.name)
        with open(path, 'wb') as f:
            f.write(uploaded.getvalue())

        extra = []
        if use_ot:  extra += ['--auto-ot']
        if use_cmp: extra += ['--compare', '5']
        if use_co:  extra += ['--cost-opt']
        if week_in.strip():
            extra += ['--settimana', week_in.strip()]

        with st.spinner("☁️ Sincronizzazione stato (straordinari, riposi, storico)…"):
            pull_report = cloud_storage.pull(tmp)

        with st.spinner("⚙️ Generazione turni in corso…"):
            m, stdout, stderr = run_engine(path, extra)

        with st.spinner("☁️ Salvataggio stato aggiornato…"):
            push_report = cloud_storage.push(tmp)

        st.session_state.result = dict(
            m=m, stdout=stdout, stderr=stderr,
            xlsx_path=path,
            pull_report=pull_report,
            push_report=push_report
        )
        st.session_state.scenario_idx = getattr(m, 'BEST_SCENARIO_IDX', 0)

    r = st.session_state.result
    if r is None:
        st.markdown(f"""
        <div class="empty-state">
          <div style="font-size:3.2rem; margin-bottom:12px;">📂</div>
          <div style="font-size:1.2rem; font-weight:600; color:#334155;">
            Carica il modello Excel e premi <strong style="color:{AZURE};">GENERA TURNI</strong>
          </div>
          <div style="font-size:.85rem; margin-top:8px;">
            Il motore elabora organico, fabbisogno, riposi e vincoli CCNL in automatico
          </div>
        </div>
        """, unsafe_allow_html=True)
        return

    m = r['m']
    scenari = getattr(m, 'SCENARI', [])
    best_idx = getattr(m, 'BEST_SCENARIO_IDX', 0)

    # ── SCENARIO SELECTOR ──────────────────────────────────
    if len(scenari) > 1:
        st.markdown('<div class="section-title">Scenario attivo</div>',
                    unsafe_allow_html=True)
        cur = st.session_state.get('scenario_idx', best_idx)
        options = list(range(len(scenari)))

        # custom HTML pill selector for a cleaner look (still uses selectbox underneath)
        st.markdown('<div class="scenario-selector">', unsafe_allow_html=True)
        sel = st.selectbox(
            "Confronta gli scenari generati da --compare",
            options=options,
            index=cur if cur in options else best_idx,
            format_func=lambda i: scenario_label(scenari[i], i, i == best_idx),
            label_visibility='collapsed'
        )
        st.markdown('</div>', unsafe_allow_html=True)
        st.session_state.scenario_idx = sel

        # quick scenario badges
        cols = st.columns(min(5, len(scenari)))
        for i, sc in enumerate(scenari[:len(cols)]):
            with cols[i]:
                tag = " ⭐" if i == best_idx else ""
                sel_tag = " ✅" if i == sel else ""
                st.caption(f"S{i+1}{tag}{sel_tag} · viol {sc['viol_n']}")
        active = ScenarioView(m, sel)
    else:
        st.session_state.scenario_idx = 0
        active = ScenarioView(m, 0)

    # ── WRITE OUTPUT XLSX (only when needed) ───────────────
    write_key = f"{r['xlsx_path']}::{active.idx}"
    if st.session_state.get('_write_key') != write_key:
        try:
            with st.spinner("📝 Scrittura diretta nel foglio Turni…"):
                out_xlsx = os.path.join(
                    os.path.dirname(r['xlsx_path']),
                    f"TOOL_LIDL_{getattr(m,'WEEK','') or 'aggiornato'}_S{active.idx+1}.xlsx"
                )
                write_shifts_surgical(
                    r['xlsx_path'], out_xlsx, active.EMP, active.shifts,
                    day_label=active.DAY_LABEL
                )
            r['out_xlsx'] = out_xlsx
            r['write_error'] = None
        except Exception as ex:
            r['out_xlsx'] = None
            r['write_error'] = str(ex)
        st.session_state['_write_key'] = write_key

    m = active  # now all tabs read from the selected scenario

    # ── KEY METRICS ────────────────────────────────────────
    tot_req = sum(m.req_d)
    tot_sch = sum(m.sched)
    tot_ot  = sum(e['ot'] for e in m.EMP)
    marg    = sum(e['mh'] for e in m.EMP) - tot_req
    marg_p  = marg / tot_req * 100 if tot_req else 0
    viol_n  = len(m.viol)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(kpi(f"{tot_req:.0f} h", "Ore richieste"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi(f"{tot_sch:.0f} h", "Ore pianificate"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi(
            f"{marg:+.1f} h", "Margine strutturale",
            delta=f"{marg_p:+.1f}%  (target ≥4%)",
            kind='ok' if marg_p >= 4 else ('warn' if marg_p >= 0 else 'alert')
        ), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi(
            f"{tot_ot:.1f} h", "Straordinari totali",
            kind='ok' if tot_ot == 0 else 'warn'
        ), unsafe_allow_html=True)
    with c5:
        st.markdown(kpi(
            str(viol_n), "Violazioni",
            delta="✅ Nessuna" if viol_n == 0 else f"⚠️ {viol_n} aperte",
            kind='ok' if viol_n == 0 else ('warn' if viol_n <= 4 else 'alert')
        ), unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── TABS ────────────────────────────────────────────────
    t1, t2, t3, t4, t5 = st.tabs([
        "📅 Weekly Rotation",
        "📊 Copertura",
        "⏱ Daily Planner",
        "💶 Straordinari",
        "📋 Console"
    ])

    # TAB 1 ── ROTA ────────────────────────────────────────
    with t1:
        st.markdown(f'<div class="section-title">Weekly Rotation — {getattr(m,"WEEK","—")}</div>',
                    unsafe_allow_html=True)
        assenti_list = getattr(m, 'ASSENTI', [])
        if assenti_list:
            st.warning("⚠️ Assenti: " + ", ".join(f"{n} ({t})" for n, t, _ in assenti_list))

        rows = []
        for e in m.EMP:
            row = {'Dipendente': e['name'], 'Ruolo': e['role'], 'Ore': int(e['mh'])}
            for d, ds in enumerate(DAYS_SHORT):
                s = m.shifts[e['id']][d]
                row[ds] = 'R' if s is None else \
                    f"{hms(s[0])}–{hms(s[1])}{'★' if m.OT_DAY[e['id']][d] > 0 else ''}"
            rows.append(row)

        df_rota = pd.DataFrame(rows)

        def style_rota(val):
            if val == 'R':
                return f'background:{ICE}; color:{MUTED}; font-weight:500; text-align:center'
            if '★' in str(val):
                return f'background:{AMBER}22; color:{NAVY}; font-weight:600; text-align:center; font-size:.8rem'
            return 'text-align:center; font-size:.8rem'

        _sf = getattr(df_rota.style, 'map', None) or getattr(df_rota.style, 'applymap')
        styled = _sf(style_rota, subset=DAYS_SHORT)
        st.dataframe(styled, width='stretch', height=min(800, 88 + len(m.EMP) * 36))

        if m.viol:
            st.markdown('<div class="section-title">Violazioni residue</div>', unsafe_allow_html=True)
            st.markdown(' '.join(f'<span class="viol-pill">⚠ {v}</span>' for v in m.viol),
                        unsafe_allow_html=True)
        else:
            st.success("✅ Nessuna violazione — stacchi, coperture e presidio responsabile a norma.")

        st.markdown('<div class="section-title">Ore pianificate per giorno</div>', unsafe_allow_html=True)
        st.plotly_chart(daily_bars(m), width='stretch')

        if r.get('write_error'):
            st.error(f"⚠️ Scrittura diretta non riuscita: {r['write_error']}\n\n"
                     "Controlla il tab Console per i dettagli.")
        elif r.get('out_xlsx') and os.path.exists(r['out_xlsx']):
            with open(r['out_xlsx'], 'rb') as f:
                st.download_button(
                    "⬇️  Scarica TOOL_LIDL.xlsx aggiornato (turni già scritti)",
                    data=f.read(),
                    file_name=os.path.basename(r['out_xlsx']),
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    width='stretch'
                )
            st.success("✅ I turni sono già scritti nel foglio **Turni** — nessun copia‑incolla "
                       "necessario. Scarica il file e salvalo al posto del tuo TOOL_LIDL.xlsx.")
        else:
            st.warning("File Excel non trovato — controlla il tab Console per gli errori.")

    # TAB 2 ── COPERTURA ────────────────────────────────────
    with t2:
        st.markdown('<div class="section-title">Heatmap copertura</div>', unsafe_allow_html=True)
        st.caption("🟥 Scoperto · 🟨 Pari · 🟦 Surplus · cella = presenti/richiesti")
        st.plotly_chart(heatmap(m), width='stretch')

        comp_data = [(n, round(h, 1)) for n, h in getattr(m, 'comp', [])
                     if h and isinstance(h, (int, float)) and h > 0]
        if comp_data:
            st.markdown('<div class="section-title">Ore per attività</div>', unsafe_allow_html=True)
            df_c = pd.DataFrame(comp_data, columns=['Attività', 'Ore'])
            fig_c = px.bar(df_c, x='Ore', y='Attività', orientation='h', color='Ore',
                           color_continuous_scale=[[0, ICE], [1, AZURE]], text='Ore')
            fig_c.update_traces(texttemplate='%{text:.1f}h', textposition='outside')
            fig_c.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                coloraxis_showscale=False,
                height=max(320, len(comp_data) * 30),
                margin=dict(l=0, r=60, t=10, b=0),
                font=dict(family='Inter', size=11, color=NAVY),
                yaxis=dict(autorange='reversed', title=''),
                xaxis=dict(title='ore/settimana', gridcolor=BORDER)
            )
            st.plotly_chart(fig_c, width='stretch')

    # TAB 3 ── GANTT ────────────────────────────────────────
    with t3:
        st.markdown('<div class="section-title">TimeFlow</div>', unsafe_allow_html=True)
        day_sel = st.radio(
            "Giorno", DAYS_FULL, horizontal=True, index=0,
            label_visibility='collapsed'
        )
        day_idx = DAYS_FULL.index(day_sel)
        st.plotly_chart(gantt(m, day_idx), width='stretch')

        critical = [
            {
                'Orario': hms(t),
                'Presenti': int(m.P[day_idx][i]),
                'Richiesti': int(m.REQ[day_idx][i]),
                'Scoperto': int(m.REQ[day_idx][i] - m.P[day_idx][i])
            }
            for i, t in enumerate(m.SLOTS)
            if i < len(m.P[day_idx]) and i < len(m.REQ[day_idx])
            and m.P[day_idx][i] < m.REQ[day_idx][i]
        ]
        if critical:
            st.markdown('<div class="section-title">Slot scoperti</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(critical), width='stretch', hide_index=True)
        else:
            st.success(f"✅ {day_sel}: copertura completa.")

    # TAB 4 ── STRAORDINARI ─────────────────────────────────
    with t4:
        st.markdown('<div class="section-title">Distribuzione straordinari</div>', unsafe_allow_html=True)
        fig_ot = ot_bar(m)
        if fig_ot:
            st.plotly_chart(fig_ot, width='stretch')
        else:
            st.info("✅ Nessuno straordinario questa settimana.")

        st.markdown('<div class="section-title">Progressivo annuo</div>', unsafe_allow_html=True)
        ytd = getattr(m, 'YTD', {})
        tetto = getattr(getattr(m, 'A', None), 'tetto_annuo', 250) or 250
        ytd_rows = []
        for e in m.EMP:
            prog = ytd.get(e['name'].upper(), 0.0) + e['ot']
            room = max(0.0, tetto - prog)
            stato = '🔴 TETTO' if prog >= tetto else (
                '🟡 ATTENZIONE' if prog >= tetto * 0.8 else '🟢 OK')
            ytd_rows.append({
                'Dipendente': e['name'],
                'Contratto': f"{int(e['mh'])}h",
                'OT questa sett.': f"{e['ot']:.2f}h" if e['ot'] else '—',
                'Prog. anno': f"{prog:.1f}h",
                f'Residuo {int(tetto)}h': f"{room:.1f}h",
                'Stato': stato
            })
        st.dataframe(pd.DataFrame(ytd_rows), width='stretch', hide_index=True)

        sb = getattr(m, 'SEAM_BRIDGE', [])
        if sb:
            st.markdown('<div class="section-title">Micro-estensioni responsabile</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame([
                {'Giorno': DAYS_SHORT[d], 'Dipendente': nm, 'Minuti': mins}
                for d, nm, mins in sb
            ]), width='stretch', hide_index=True)

    # TAB 5 ── CONSOLE ──────────────────────────────────────
    with t5:
        st.markdown('<div class="section-title">Persistenza stato (straordinari/riposi/storico)</div>',
                    unsafe_allow_html=True)
        pr, pu = r.get('pull_report'), r.get('push_report')
        st.markdown(f"**Backend:** `{cloud_storage.backend_name()}`")
        if pr:
            st.caption(
                f"Caricati all'avvio: {', '.join(pr['ok']) or '—'}"
                f"  ·  nuovi (nessuno stato precedente): {', '.join(pr['skip']) or '—'}"
                + (f"  ·  ⚠️ errori: {', '.join(pr['err'])}" if pr['err'] else '')
            )
        if pu:
            st.caption(
                f"Salvati a fine generazione: {', '.join(pu['ok']) or '—'}"
                + (f"  ·  ⚠️ errori: {', '.join(pu['err'])}" if pu['err'] else '')
            )
        if cloud_storage.backend_name() == 'local':
            st.info("Backend locale: `straordinari_log.csv`, `rota_boundary.csv` e "
                    "`rota_history.csv` restano su disco in `/tmp/rotosmart`. Su Streamlit "
                    "Community Cloud questa cartella viene svuotata ai riavvii — configura "
                    "`[github]` in `st.secrets` per la persistenza (vedi cloud_storage.py).")

        st.markdown('<div class="section-title">Output motore</div>', unsafe_allow_html=True)
        st.code(r['stdout'] or '(nessun output)', language='text')
        if r['stderr'].strip():
            st.markdown('<div class="section-title">Avvisi</div>', unsafe_allow_html=True)
            st.code(r['stderr'], language='text')


if __name__ == '__main__':
    main()
