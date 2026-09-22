#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ThinkCore - Gestione Turni Retail
Interfaccia Streamlit per generatore_turni_v6.py

v2.5 - editor turni, restyling
  - TAB "Modifica turni": strip settimanale con ore per giorno (evidenzia il
    giorno attivo), selettore giorno compatto, tabella a 4 colonne con pill
    per R/P e ore, righe più arieggiate.
  - Rimosso codice morto, costanti allineate al design system.
  - Logica di editing (inizio + fine, ±30 min, stato condiviso) invariata.
"""

import streamlit as st
import plotly.graph_objects as go
from write_engine import write_shifts_surgical
import cloud_storage
import plotly.express as px
import pandas as pd
import os, sys, types, io, contextlib, datetime, re, math

# ────────────── CONFIG PAGINA ──────────────
# Logo incorporato nel codice (base64): non serve nessuna cartella "assets" esterna
# da ricordarsi di copiare — il logo viaggia sempre insieme a questo singolo file .py.
_LOGO_B64 = (
    "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"
    "U3QtK3GSuA0Rpp1Jo4vhqeCdGrfcDfFWqw9KzroCY1skL0/nAwjPG5OwobMHbgokYIxbyAq4whSiABzXctcVHjJC9yCNqsknoC/x"
    "CtLlpkoWhPikoa1AJz9W2+OakMWQocEm6OF1LgQ4HtZ1aB+UDOdRwE78YzXWcg0Qq+eN7C5jr7aqw2uULGDBgzGbghTYLrenUgKU"
    "N8JUOQNiRV86A6etdyQmILYyyhToUpwbuasbJB5/T29qo9kfuzTrYtNqZjtL8gw2FrJV/Ecknv2+1alb1jom1qlXCQk3RSfpBymP"
    "/Eo/vn07feu5MSxlNabcdwVSM40i8xa0bzfroNLK1yzWLpiz20xCywuUpByFK1LzjcZNeXfjTKiIvC5EINwSlDrbSWhp0uaSUqB7"
    "ZO2exq1RetJctRVHW6t5Rxsrcjsf132rldT9K2fqeGh2VcTbnzlXhaMgb7gK7A90kH1pbNm2TITZOhW1sz2khYHQYh2Q6ZbOnnyP"
    "yXn95CWJ6H1Wx1cssj8JpsBlZUn8+nJ77jk9+a5z0iSt2SgySt13/wAySkZIB/8AjTjngDA5xjgVtEj4XxytIRdFhspG4kpUQOOA"
    "Rt96OL8KYjFrkPsXVpu5tA/JhLf4YUfznPC8bA8Dn7aMWDcyOox5LP2htDCQTDxpQb4gh30Jod6HelkpW5bWEMSZFzYcwQ3EhvBC"
    "GiN9ClHILpByU9uOdgzFusmc6y3Gk9ROKWrSlPzqPLjkq22GN88VNu/T1wsx8KfFSlC16JAUfK6BuFA9nE+vceu9cqGHW7ePk4yn"
    "FvI1ynFHdSc7Ng9k7ZPdR9qyJXTMOV1g99FqxxYeQZmAEeqS8w5JdCnU3S4xg4N1y0hD2D2zg453++KhzTcmVBx60wGGlrKUpRHa"
    "IT/CDudvf+tSC/HdjqQtTYkqUAnXDCyB+7xx6AV049ujOuKQ4zhenQtEfSgLXv5lAHAA054xzntTPBieNXWepCWHzNOjdOgK6PTX"
    "R92vtsactbDDy3ipLpjspQrRhJKBwc7kHnirj0t0bcLY8+11S+5brawEOtuyFZcStCsgIHKtspA9SO1dz/p9kIiSWQFBceKkuOrX"
    "9Pqo+yQB/wAzVP63vXz10kLbUoNFxRbTn6U52H8q02QxQtzNGq87/wAjipcU+B1Fg7+WoK5/Wt4/a16ky0o8Ntavw0fuIAwkfoAK"
    "qr68k0/Je53qC4omqr3WbV+CIRtDRuCQs00aUs5pBpZVkK2Wdm1WpK/morsud4eWEgjwkKyPqGcq7/0q3WGZdLzLTKvV0MCCl0JW"
    "6vytoz+VLaRueNkj0zTUGLZolscvdxBYjpXpZaWoLfkHHKeArfZR+lI23OKqV56vnSbkJSHQyGwpDDTX0sNnPkTntvWS3ESyiojX"
    "26d/Wvkr5wcMbs0out18ew4D0vqNVtrfU9gQ74Lcq7+IhQWy4XvlUHAwopwDpzjvz370P2l0rdnQ5MfWytHnWZKQpagOcLQMKP3A"
    "rBWupblqKhJcJUMZUrUce2eK68HqGSpkRzpUo6QCWx/U1Pu0tayFcOfCCCIhp5LbZPW9ntpS307FAWhISHHGwFhIz3H0/wB/es+6"
    "j6okXGUp2RJyHFFSEhJ088/3x9qqNxnPupDSXknBIc07439eP61GYShClLdeToH06TkrOeB29zVvDRRw/wAd/wA1Sn8SY2/y5BXW"
    "BeXIrxfiP6tyPICnXg5Ct+P/AFUz/ELs6SGwoZOVKOoIBOMk547bVRXrg2GfAZb0jO61DzEY49gDn7/pTJlLKAjxArScDJ/5tWi2"
    "d1clmOwEeayLK0ZvqR1TKg26vwiolIUQDpA/v/8AlOsdSOGKs+ISMk//AFrOTLVqCEkYTuCSKeauLrcdJCzkKVjvymntxBCqybOj"
    "dvCtXUb0PqGHHjyvK82rUh3ON8/ST+6Qe/FVyz2122XxiHPVoZWlTTqUK1JPfH3GfvURu4LS14exBPcbj9a67lxhyG25brwElKdS"
    "gedQGM/qAK5kjjxTSH76Wtgpn4WPK3/yRXbku3eenujVwUO2+7IJWMYL3hqSr3SUbD9aq79mhx43hNTIbDDv+o4HPFcc76TgbAc4"
    "qFcpSEy3m2nQtvUdJB2I7VBROUjUlR1IUMKH+/396TEYowMrfUn8rSO1JS0t8Nt9L/KtS+pWLdYlWazIcaadH+ZfWr8R4+m2yU+w"
    "57+lVKXILiionNMPu5O3P96jLXnvRJM55srLZC0OLgNSg6vKqYcVRrVTZNKVgBETRDmgeaAqF0F2b3LkKCV3GUlyUkBLcZABQwkc"
    "JwPKkfwjPvXDcUtxwrUcqJyaVpJVp5+wpaGiokNjJAyfYUoRtApooJgc67cbKeiNoC05OpajhIGxJPH2FTZc14pYjOJSy5EUUhbe"
    "xO+dz3IPB7VyuaPvgV2G0uTR3rosurcK2w8lKdJUoqXgHvt6n+9JL2T/AAp4GagpUUmlhdACCdFOEjKd9POc/wC1AO437VCC+1KC"
    "67S6U0vZwaWZB8JIz+Y/2FQAuj1VK5LVMD5HBoi+QcZqHqxzQKqEZVIce1753ppSzjFN6qSVVC6AThVtg02tQ7GklWaSTUKaQJpJ"
    "oUVClCjJoqFCkJaN042Sn8yvX/npQccB8iBpQP5n3NJUSo+gHA9KT7VKhKWNJxkH3FEDiioVCEYNKzikA0dClKzSs0ihvnmhQl5x"
    "R6jTeaGaLQnCTRZpGaGaEJefeiJpNChCGaFETQopCGaFF3oVKEKG9CgKEWjJoqPFCoU0iGaFKxtRUKEVGKAobVKECaFFRihTaGaG"
    "aKhihCOhmioUIR5oZoGi70IQNFyaVRY3oUFDNChQoUIUKFH2oU0v/9k="
)

def _page_icon():
    try:
        import base64, io
        from PIL import Image
        return Image.open(io.BytesIO(base64.b64decode(_LOGO_B64)))
    except Exception:
        return "🧭"

st.set_page_config(page_title="ThinkCore", page_icon=_page_icon(),
                   layout="wide", initial_sidebar_state="expanded")

def _rail_mark_html():
    return '<img src="data:image/jpeg;base64,' + _LOGO_B64 + '" alt="ThinkCore" />'

# ────────────── TOKEN DI DESIGN ──────────────
INK       = "#0B0F16"
SURFACE   = "#131923"
SURFACE_2 = "#1A2230"
SURFACE_3 = "#212B3B"
LINE      = "#262E40"
LINE_SOFT = "#1C2330"
TEXT      = "#E8ECF4"
SUBTLE    = "#8B94A8"
FAINT     = "#586178"
SIGNAL    = "#3FD9C7"
SIGNAL_DK = "#1F6E63"
RESP_BLUE = "#5C8DF6"
AMBER     = "#F2A93B"
CRIMSON   = "#FF5C5C"
ORANGE    = "#F9834C"
WHITE     = "#FFFFFF"

GREEN_DEEP   = "#08261B"
GREEN_MID    = "#12543A"
GREEN_BRIGHT = "#22A876"

NAVY, STEEL, AZURE = INK, SURFACE_2, RESP_BLUE
LIME, WARN, DANGER = SIGNAL, AMBER, CRIMSON
ICE, MUTED = SURFACE, SUBTLE

CSS = f"""<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  html,body,[class*="css"]{{font-family:'Inter',sans-serif;background:{INK};color:{TEXT}}}
  .stApp{{background:
    radial-gradient(ellipse 900px 520px at 12% -12%, {SIGNAL}12, transparent 60%),
    radial-gradient(ellipse 760px 480px at 100% -4%, {RESP_BLUE}0F, transparent 58%),
    {INK}}}
  .block-container{{position:relative}}
  .block-container::before{{content:'';position:fixed;inset:0;pointer-events:none;z-index:-1;
    background-image:radial-gradient({LINE_SOFT} 1px, transparent 1px);
    background-size:30px 30px;opacity:.32;
    mask-image:radial-gradient(ellipse 72% 62% at 50% 0%, #000 0%, transparent 76%)}}
  #MainMenu,footer{{visibility:hidden}}
  header[data-testid="stHeader"]{{background:transparent}}
  .block-container{{padding-top:1.15rem;max-width:1440px}}
  ::selection{{background:{SIGNAL}44}}
  ::-webkit-scrollbar{{width:10px;height:10px}}
  ::-webkit-scrollbar-track{{background:{INK}}}
  ::-webkit-scrollbar-thumb{{background:{LINE};border-radius:6px}}
  ::-webkit-scrollbar-thumb:hover{{background:{FAINT}}}

  .mono, .kpi-value, .ruler-mark span, .chip-mono {{font-family:'Inter',sans-serif;font-variant-numeric:tabular-nums}}

  /* ---------- SIDEBAR ---------- */
  section[data-testid="stSidebar"]{{background:linear-gradient(180deg,{SURFACE_2} 0%,{SURFACE} 140%)!important;
    border-right:1px solid {LINE}}}
  section[data-testid="stSidebar"] *{{color:{TEXT}!important}}
  section[data-testid="stSidebar"] .stSelectbox label,
  section[data-testid="stSidebar"] .stCheckbox label,
  section[data-testid="stSidebar"] .stTextInput label{{
    color:{SUBTLE}!important;font-size:.7rem;letter-spacing:.09em;text-transform:uppercase;font-weight:600}}
  section[data-testid="stSidebar"] hr{{border-color:{LINE}!important;margin:14px 0}}
  .rail-brand{{display:flex;align-items:center;gap:11px;margin-bottom:4px}}
  .rail-mark{{width:38px;height:38px;border-radius:10px;background:{SURFACE};overflow:hidden;
    display:flex;align-items:center;justify-content:center;color:{INK};flex-shrink:0;
    box-shadow:0 4px 14px -3px {SIGNAL}66}}
  .rail-mark img{{width:100%;height:100%;object-fit:cover;display:block}}
  .rail-title{{font-family:'Inter',sans-serif;font-weight:700;font-size:1.18rem;color:{WHITE};line-height:1.1}}
  .rail-sub{{font-size:.68rem;color:{SUBTLE};letter-spacing:.06em;text-transform:uppercase;margin-top:1px}}
  .rail-eyebrow{{font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;color:{FAINT}!important;
    font-weight:700;margin:2px 0 8px;display:flex;align-items:center;gap:6px}}
  .rail-eyebrow::after{{content:'';flex:1;height:1px;background:{LINE}}}
  .rail-status{{font-size:.72rem;color:{FAINT}!important;line-height:1.7;padding-top:2px}}
  .rail-status b{{color:{SUBTLE}!important}}
  .status-dot{{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:6px;flex-shrink:0}}

  button[kind="primary"]{{
    background:linear-gradient(160deg, {GREEN_MID} 0%, {GREEN_DEEP} 100%)!important;
    color:#EAFBF2!important;font-weight:700!important;
    border:1px solid {GREEN_BRIGHT}55!important;border-radius:11px!important;letter-spacing:.04em;
    position:relative;overflow:hidden;
    box-shadow:0 5px 20px -6px {GREEN_DEEP}CC, inset 0 1px 0 rgba(255,255,255,.08)!important;
    transition:transform .15s ease,box-shadow .15s ease,border-color .15s ease!important}}
  button[kind="primary"]::before{{content:'';position:absolute;inset:0;
    background:linear-gradient(115deg, transparent 40%, {GREEN_BRIGHT}26 50%, transparent 60%);pointer-events:none}}
  button[kind="primary"]:hover{{
    background:linear-gradient(160deg, {GREEN_BRIGHT} 0%, {GREEN_MID} 100%)!important;
    border-color:{GREEN_BRIGHT}!important;transform:translateY(-1px);
    box-shadow:0 9px 26px -6px {GREEN_BRIGHT}77, inset 0 1px 0 rgba(255,255,255,.12)!important}}
  button[kind="primary"]:active{{transform:translateY(0)}}
  button[kind="primary"]:disabled{{background:{SURFACE}!important;border-color:{LINE}!important;
    color:{FAINT}!important;box-shadow:none!important;opacity:.6}}
  button[kind="primary"]:disabled::before{{display:none}}

  [data-testid="stFileUploaderDropzone"]{{background:{SURFACE}!important;border:1px dashed {LINE}!important;
    border-radius:11px!important;transition:border-color .15s ease}}
  [data-testid="stFileUploaderDropzone"]:hover{{border-color:{SIGNAL}66!important}}
  [data-testid="stFileUploaderDropzoneInstructions"] *{{color:{SUBTLE}!important}}
  [data-testid="stFileUploaderDropzoneInstructions"] svg{{fill:{FAINT}!important}}
  [data-testid="stBaseButton-secondary"]{{background:{SURFACE_2}!important;color:{TEXT}!important;
    border:1px solid {LINE}!important}}
  [data-testid="stFileUploaderFile"]{{background:{SURFACE}!important;border:1px solid {LINE}!important;
    border-radius:9px!important;padding:8px 10px!important}}
  [data-testid="stFileUploaderFile"] *{{color:{TEXT}!important}}
  [data-testid="stFileUploaderFileIcon"]{{background:transparent!important}}
  [data-testid="stFileUploaderFileIcon"] svg,
  [data-testid="stFileUploaderFileIcon"] path{{fill:{SIGNAL}!important;background:transparent!important}}
  [data-testid="stFileUploaderFileName"]{{font-family:'Inter',sans-serif!important;font-size:.78rem!important}}
  [data-testid="stFileUploaderFileErrorMessage"]{{color:{CRIMSON}!important}}

  .top-banner{{background:linear-gradient(180deg,{SURFACE_2} 0%,{SURFACE} 130%);border:1px solid {LINE};
    border-radius:16px;padding:22px 28px;margin-bottom:16px;overflow:hidden;position:relative;
    box-shadow:0 14px 36px -18px rgba(0,0,0,.6)}}
  .top-banner::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;
    background:linear-gradient(90deg,{SIGNAL} 0%,{RESP_BLUE} 45%,{AMBER} 75%,{CRIMSON} 100%);opacity:.85}}
  .top-banner-row{{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px}}
  .top-banner h1{{font-family:'Inter',sans-serif;margin:0;font-size:1.6rem;font-weight:700;
    letter-spacing:-.01em;color:{WHITE};display:flex;align-items:baseline;gap:2px}}
  .top-banner h1 .dot{{color:{SIGNAL}}}
  .top-banner h1 .sub-inline{{font-weight:400;color:{SUBTLE};font-size:.98rem;
    font-family:'Inter',sans-serif;margin-left:8px}}
  .top-banner p{{color:{SUBTLE};margin:6px 0 0;font-size:.85rem;max-width:64ch}}
  .banner-badge{{display:flex;align-items:center;gap:8px;background:{SURFACE};border:1px solid {LINE};
    border-radius:10px;padding:9px 14px}}
  .banner-badge .bb-k{{font-size:.62rem;letter-spacing:.09em;text-transform:uppercase;color:{FAINT};font-weight:600}}
  .banner-badge .bb-v{{font-family:'Inter',sans-serif;font-size:.95rem;font-weight:600;color:{TEXT}}}

  .hero{{background:{SURFACE};border:1px solid {LINE};border-radius:14px;padding:16px 18px 12px;
    margin:0 0 6px;box-shadow:0 10px 30px -18px rgba(0,0,0,.55);position:relative;overflow:hidden}}
  .hero-head{{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:8px}}
  .hero-title{{font-family:'Inter',sans-serif;font-size:.8rem;font-weight:600;color:{TEXT};
    display:flex;align-items:center;gap:8px}}
  .hero-title::before{{content:'';width:3px;height:14px;background:{SIGNAL};border-radius:2px}}
  .hero-legend{{display:flex;gap:14px;font-size:.72rem;color:{SUBTLE}}}
  .hero-legend .li{{display:flex;align-items:center;gap:6px}}
  .hero-legend .sw{{width:9px;height:9px;border-radius:3px;flex-shrink:0}}
  .hero-svg{{width:100%;line-height:0}}
  .hero-svg svg{{width:100%;height:auto;display:block}}

  .status-bar{{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0 16px}}
  .status-chip{{display:flex;align-items:center;gap:7px;background:{SURFACE};border:1px solid {LINE};
    border-radius:999px;padding:6px 14px;font-size:.76rem;color:{SUBTLE};transition:border-color .15s ease}}
  .status-chip:hover{{border-color:{LINE_SOFT}}}
  .status-chip b{{color:{TEXT};font-family:'Inter',sans-serif;font-weight:600}}

  .kpi-row{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;margin:2px 0 6px;align-items:stretch}}
  .kpi-card{{background:linear-gradient(180deg,{SURFACE} 0%,{SURFACE}00 180%),{SURFACE};
    border:1px solid {LINE};border-radius:13px;padding:15px 17px;position:relative;overflow:hidden;
    animation:kpiRise .42s cubic-bezier(.2,.7,.3,1) both;height:150px;
    display:flex;flex-direction:column;justify-content:space-between;
    transition:border-color .18s ease,transform .18s ease,box-shadow .18s ease;min-width:0;box-sizing:border-box}}
  .kpi-card:hover{{border-color:{LINE_SOFT};transform:translateY(-2px);box-shadow:0 12px 26px -16px rgba(0,0,0,.7)}}
  .kpi-card::before{{content:'';position:absolute;left:0;top:14px;bottom:14px;width:3px;border-radius:2px;background:{RESP_BLUE}}}
  .kpi-card.ok::before{{background:{SIGNAL}}}
  .kpi-card.warn::before{{background:{AMBER}}}
  .kpi-card.alert::before{{background:{CRIMSON}}}
  .kpi-card.hot::before{{background:{ORANGE}}}
  .kpi-top{{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-left:8px;
    height:2.5em;flex-shrink:0}}
  .kpi-label{{font-size:.66rem;letter-spacing:.08em;text-transform:uppercase;color:{FAINT};font-weight:600;
    line-height:1.25;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
  .kpi-tag{{font-family:'Inter',sans-serif;font-size:.6rem;font-weight:600;color:{FAINT};
    border:1px solid {LINE};border-radius:5px;padding:1px 6px;flex-shrink:0;white-space:nowrap}}
  .kpi-value{{font-size:1.68rem;font-weight:600;color:{TEXT};line-height:1;margin:0 0 0 8px;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:flex;align-items:baseline;gap:5px;flex-shrink:0}}
  .kpi-value .unit{{font-size:.86rem;font-weight:500;color:{SUBTLE}}}
  .kpi-delta{{font-size:.71rem;font-weight:500;margin:0 0 0 8px;font-family:'Inter',sans-serif;
    line-height:1.3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;height:1.3em;flex-shrink:0}}
  .kpi-bar{{height:3px;border-radius:2px;background:{LINE};margin:0 8px;overflow:hidden;flex-shrink:0}}
  .kpi-bar-fill{{height:100%;border-radius:2px;transition:width .5s cubic-bezier(.2,.7,.3,1)}}
  @keyframes kpiRise{{from{{opacity:0;transform:translateY(7px)}}to{{opacity:1;transform:translateY(0)}}}}
  @media (prefers-reduced-motion: reduce){{.kpi-card{{animation:none}}.kpi-bar-fill{{transition:none}}}}
  @media (max-width:1100px){{.kpi-row{{grid-template-columns:repeat(2,1fr)}}.kpi-card{{height:auto;min-height:150px}}}}

  .section-title{{font-family:'Inter',sans-serif;font-size:.82rem;font-weight:600;letter-spacing:.01em;
    color:{TEXT};margin:24px 0 12px;padding-bottom:8px;border-bottom:1px solid {LINE};
    display:flex;align-items:center;gap:8px}}
  .section-title::before{{content:'';width:3px;height:14px;background:{SIGNAL};border-radius:2px;display:inline-block}}
  .section-title .st-note{{margin-left:auto;font-family:'Inter',sans-serif;font-weight:400;font-size:.72rem;color:{FAINT}}}

  [data-testid="stSidebarCollapseButton"] button,
  [data-testid="collapsedControl"] button{{background:transparent!important}}
  [data-testid="stSidebarCollapseButton"] svg,
  [data-testid="collapsedControl"] svg{{color:{SUBTLE}!important;fill:{SUBTLE}!important}}

  .scenario-row{{display:flex;gap:8px;flex-wrap:wrap;margin:2px 0 16px}}
  .scenario-chip{{border:1px solid {LINE};background:{SURFACE};border-radius:10px;padding:8px 13px;font-size:.76rem;
    color:{SUBTLE};display:flex;flex-direction:column;gap:1px;min-width:88px;
    transition:border-color .15s ease,transform .15s ease}}
  .scenario-chip:hover{{border-color:{LINE_SOFT};transform:translateY(-1px)}}
  .scenario-chip .sc-id{{font-family:'Inter',sans-serif;font-weight:600;color:{TEXT};font-size:.8rem}}
  .scenario-chip .sc-viol{{font-size:.7rem}}
  .scenario-chip.selected{{border-color:{SIGNAL};background:{SIGNAL}14;box-shadow:0 0 0 1px {SIGNAL}33}}
  .scenario-chip.best .sc-id::after{{content:' ★';color:{AMBER}}}

  .viol-pill{{background:{CRIMSON}14;border:1px solid {CRIMSON}44;color:#FFB0AC;border-radius:8px;
    padding:6px 13px;font-size:.8rem;margin:3px 0;display:block;font-family:'Inter',sans-serif}}

  [role="tablist"]{{display:flex;flex-wrap:wrap;gap:6px;padding:5px;background:{SURFACE};
    border:1px solid {LINE};border-radius:13px;margin:2px 0 18px}}
  button[role="tab"]{{color:{SUBTLE}!important;font-size:.84rem!important;font-weight:500!important;
    padding:9px 17px!important;border-radius:9px!important;background:{INK}66!important;
    border:1px solid transparent!important;
    transition:background .15s ease,color .15s ease,border-color .15s ease!important}}
  button[role="tab"]:hover{{color:{TEXT}!important;background:{LINE_SOFT}!important}}
  button[role="tab"][aria-selected="true"]{{color:{INK}!important;font-weight:700!important;
    background:{SIGNAL}!important;box-shadow:0 2px 10px -2px {SIGNAL}77!important}}
  button[role="tab"][aria-selected="true"]:hover{{background:{SIGNAL}!important}}
  button[role="tab"]:focus{{outline:none!important;box-shadow:none!important}}
  button[role="tab"]:focus-visible{{outline:2px solid {SIGNAL}55!important;outline-offset:1px!important}}
  [data-baseweb="tab-highlight"]{{display:none!important}}

  .legend-row{{display:flex;gap:16px;flex-wrap:wrap;margin:2px 0 14px;font-size:.78rem;color:{SUBTLE}}}
  .legend-item{{display:flex;align-items:center;gap:6px}}
  .legend-dot{{width:9px;height:9px;border-radius:3px;flex-shrink:0}}
  .legend-note{{color:{FAINT};margin-left:2px}}

  .top-banner h1 a, .top-banner h1 svg,
  [data-testid="stHeaderActionElements"]{{display:none!important}}

  .empty-state{{text-align:center;padding:88px 40px;border:1px dashed {LINE};border-radius:16px;
    background:linear-gradient(180deg,{SURFACE} 0%,{SURFACE}00 160%),{SURFACE}}}
  .empty-state .glyph{{color:{SIGNAL};opacity:.55;display:flex;align-items:center;justify-content:center}}
  .empty-state .title{{font-family:'Inter',sans-serif;font-size:1.15rem;font-weight:600;color:{TEXT};margin-top:14px}}
  .empty-state .sub{{font-size:.85rem;color:{SUBTLE};margin-top:8px;max-width:52ch;margin-left:auto;margin-right:auto}}

  [data-testid="stAlertContainer"]{{border-radius:11px!important;border:1px solid transparent!important;backdrop-filter:none!important}}
  [data-testid="stAlertContainer"] p{{font-size:.86rem!important}}
  [data-testid="stAlertContainer"][class*="success"],
  div[data-baseweb="notification"][kind="success"]{{background:{SIGNAL}12!important;border-color:{SIGNAL}3D!important}}
  [data-testid="stAlertContainer"] svg{{flex-shrink:0}}
  .stSuccess{{background:{SIGNAL}12!important;border:1px solid {SIGNAL}3D!important;border-radius:11px!important}}
  .stSuccess p{{color:#B7F3EA!important}}
  .stSuccess svg{{fill:{SIGNAL}!important;color:{SIGNAL}!important}}
  .stWarning{{background:{AMBER}12!important;border:1px solid {AMBER}3D!important;border-radius:11px!important}}
  .stWarning p{{color:#FBE1B4!important}}
  .stWarning svg{{fill:{AMBER}!important;color:{AMBER}!important}}
  .stError{{background:{CRIMSON}12!important;border:1px solid {CRIMSON}3D!important;border-radius:11px!important}}
  .stError p{{color:#FFC7C4!important}}
  .stError svg{{fill:{CRIMSON}!important;color:{CRIMSON}!important}}
  .stInfo{{background:{RESP_BLUE}12!important;border:1px solid {RESP_BLUE}3D!important;border-radius:11px!important}}
  .stInfo p{{color:#C6D7FC!important}}
  .stInfo svg{{fill:{RESP_BLUE}!important;color:{RESP_BLUE}!important}}

  [data-testid="stRadio"] > div[role="radiogroup"]{{display:flex;gap:4px;background:{SURFACE};
    border:1px solid {LINE};border-radius:11px;padding:4px;flex-wrap:wrap}}
  [data-testid="stRadio"] label{{background:transparent;border-radius:8px;padding:6px 14px!important;
    margin:0!important;transition:background .15s ease;cursor:pointer;display:flex!important;align-items:center;gap:0!important}}
  [data-testid="stRadio"] label:hover{{background:{SURFACE_2}}}
  [data-testid="stRadio"] label [data-baseweb="radio"]{{position:absolute;opacity:0;width:0;height:0;overflow:hidden}}
  [data-testid="stRadio"] label div[data-testid="stMarkdownContainer"]{{margin:0!important}}
  [data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] p{{font-size:.82rem!important;
    color:{SUBTLE}!important;margin:0!important;font-weight:500!important}}
  [data-testid="stRadio"] label:has(input:checked){{background:{SIGNAL}1E}}
  [data-testid="stRadio"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p{{color:{TEXT}!important;font-weight:600!important}}

  section[data-testid="stSidebar"] [data-testid="stCheckbox"] label span[data-testid="stMarkdownContainer"]{{
    font-size:.82rem!important;text-transform:none!important;letter-spacing:0!important;color:{TEXT}!important}}

  [data-testid="stDataFrame"]{{border:1px solid {LINE}!important;border-radius:11px!important;overflow:hidden!important}}

  [data-testid="stCodeBlock"] pre{{background:{SURFACE}!important;border:1px solid {LINE}!important;
    border-radius:11px!important;font-size:.78rem!important}}

  [data-testid="stDownloadButton"] button{{background:{SURFACE_2}!important;color:{TEXT}!important;
    border:1px solid {LINE}!important;font-weight:600!important;transition:border-color .15s ease,color .15s ease}}
  [data-testid="stDownloadButton"] button:hover{{border-color:{SIGNAL}!important;color:{SIGNAL}!important}}

  /* ---------- EDITOR TURNI: pulsanti ± compatti ---------- */
  div[data-testid="stButton"] > button:not([kind="primary"]){{
    padding:0 4px !important;
    min-height:28px !important;
    height:28px !important;
    font-size:.9rem !important;
    font-weight:700 !important;
    line-height:1 !important;
    border-radius:6px !important;
    background:{SURFACE_2}!important;
    border:1px solid {LINE}!important;
    color:{TEXT}!important;
    transition:background .12s ease,border-color .12s ease,color .12s ease;
  }}
  div[data-testid="stButton"] > button:not([kind="primary"]):hover{{
    background:{SURFACE_3}!important;
    border-color:{SIGNAL}88!important;
    color:{SIGNAL}!important;
  }}
  div[data-testid="stButton"] > button:not([kind="primary"]):disabled{{
    opacity:.35!important;
  }}

  /* righe editor: spazio verticale contenuto */
  div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"]{{gap:.15rem!important}}
</style>"""

ENGINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'generatore_turni_v6.py')

# ────────────── MOTORE (invariato) ──────────────
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
            try: exec(compile(src, ENGINE_PATH, 'exec'), mod.__dict__)
            except SystemExit: pass
    finally:
        sys.argv = old_argv; os.chdir(old_cwd)
    return mod, out_buf.getvalue(), err_buf.getvalue()

# ────────────── TEMA PLOTLY CENTRALIZZATO ──────────────
_HOVER = dict(bgcolor=SURFACE_3, bordercolor=LINE,
              font=dict(color=TEXT, family='Inter', size=11))

def _theme(fig, height=None, legend=True, top=32):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', size=12, color=TEXT),
        margin=dict(l=8, r=10, t=(top if legend else 8), b=8),
        hoverlabel=_HOVER, colorway=[SIGNAL, RESP_BLUE, AMBER, CRIMSON],
        modebar=dict(remove=['lasso', 'select', 'zoom', 'pan', 'autoscale']),
    )
    if height:
        fig.update_layout(height=height)
    fig.update_xaxes(gridcolor=LINE, zerolinecolor=LINE, linecolor='rgba(0,0,0,0)',
                     tickfont=dict(color=SUBTLE, size=10), title_font=dict(color=SUBTLE, size=11))
    fig.update_yaxes(gridcolor=LINE, zerolinecolor=LINE, linecolor='rgba(0,0,0,0)',
                     tickfont=dict(color=SUBTLE, size=10), title_font=dict(color=SUBTLE, size=11))
    if legend:
        fig.update_layout(legend=dict(orientation='h', y=1.14, x=0, xanchor='left',
                          bgcolor='rgba(0,0,0,0)', font=dict(color=SUBTLE, size=11)))
    return fig

def hms(h):
    hh = int(h); mm = int(round((h - hh) * 60)); return f"{hh:02d}:{mm:02d}"

# ────────────── EDITOR: parsing, delta, ri-validazione ──────────────
def _parse_cell(txt):
    t = str(txt).strip().upper().replace('–', '-').replace('—', '-')
    if t in ('', 'R', 'RIPOSO'): return ('R', None)
    if t in ('P', 'PERMESSO'): return ('P', None)
    mo = re.match(r'^(\d{1,2})[:.](\d{2})\s*-\s*(\d{1,2})[:.](\d{2})$', t)
    if not mo: return ('ERR', txt)
    h1, m1, h2, m2 = (int(x) for x in mo.groups())
    a, b = h1 + m1 / 60, h2 + m2 / 60
    if not (0 <= a < 24 and 0 < b <= 24) or b <= a: return ('ERR', txt)
    q = lambda x: round(x * 4) / 4.0
    return ('S', (q(a), q(b)))

def _shift_to_cell(s, lab=None):
    if s is None: return 'P' if lab == 'P' else 'R'
    return f"{hms(s[0])}-{hms(s[1])}"

def _shift_start_delta(s, direction):
    if s is None: return None
    a, b = s
    if direction > 0:
        a2 = min(b - 0.5, a + 0.5)
    else:
        a2 = max(0.0, a - 0.5)
    return (a2, b) if a2 != a else s

def _shift_end_delta(s, direction):
    if s is None: return None
    a, b = s
    if direction > 0:
        b2 = min(24.0, b + 0.5)
    else:
        b2 = max(a + 0.5, b - 0.5)
    return (a, b2) if b2 != b else s

def revalidate(M, shifts):
    SLOTS = M.SLOTS; EMP = M.EMP; REQ = M.REQ; ENTRY = M.ENTRY; CLOSE = M.CLOSE
    MIN_AP = M.MIN_AP; MIN_CH = M.MIN_CH; STACCO = M.STACCO
    PREV = getattr(M, 'PREV_SUN_CLOSE', {}) or {}
    n = len(SLOTS); isr = {e['id']: e['role'] == 'RESP' for e in EMP}
    P = [[0] * n for _ in range(7)]; PR = [[0] * n for _ in range(7)]
    for e in EMP:
        seq = shifts.get(e['id'], [None] * 7)
        for d in range(7):
            s = seq[d]
            if not s: continue
            a, b = s
            i0 = max(0, int(math.ceil((a - 5.5) * 4 - 1e-9)))
            i1 = min(n, int(math.ceil((b - 5.5) * 4 - 1e-9)))
            for i in range(i0, i1):
                P[d][i] += 1
                if isr[e['id']]: PR[d][i] += 1
    DAYS = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']; v = []
    for e in EMP:
        seq = shifts.get(e['id'], [None] * 7)
        for d in range(7):
            d2 = (d + 1) % 7
            if seq[d] and seq[d2] and seq[d2][0] + 24 - seq[d][1] < STACCO - 1e-9:
                v.append(('stacco', f"{e['name']} {DAYS[d]}→{DAYS[d2]}: "
                          f"{seq[d2][0] + 24 - seq[d][1]:.2f}h < {STACCO:g}h"))
        if seq[0]:
            pc = PREV.get(e['name'].upper())
            if pc is not None and seq[0][0] + 24 - pc < STACCO - 1e-9:
                v.append(('stacco', f"{e['name']} Dom(sett.prec.)→Lun: {seq[0][0] + 24 - pc:.2f}h"))
    for d in range(7):
        workers = [e['id'] for e in EMP if shifts.get(e['id'], [None] * 7)[d]]
        op = sum(1 for i in workers if abs(shifts[i][d][0] - ENTRY[d]) < 1e-9)
        cl = sum(1 for i in workers if abs(shifts[i][d][1] - CLOSE[d]) < 1e-9)
        if op < MIN_AP: v.append(('apertura', f"{DAYS[d]}: {op} in apertura (minimo {MIN_AP})"))
        if cl < MIN_CH: v.append(('chiusura', f"{DAYS[d]}: {cl} in chiusura (minimo {MIN_CH})"))
        for i, t in enumerate(SLOTS):
            if P[d][i] < REQ[d][i]:
                v.append(('copertura', f"{DAYS[d]} {hms(t)}: {P[d][i]}<{REQ[d][i]}"))
            if P[d][i] > 0 and PR[d][i] < 1:
                v.append(('responsabile', f"{DAYS[d]} {hms(t)}: nessun responsabile"))
    return P, PR, v

def _grouped_viol(viol):
    from collections import OrderedDict
    g = OrderedDict()
    for cat, txt in viol: g.setdefault(cat, []).append(txt)
    return g

# ────────────── HERO ──────────────
def coverage_spectrum_svg(m, W=1000, H=140):
    slots = m.SLOTS
    n = len(slots)
    present = [sum(m.P[d][i] for d in range(7)) for i in range(n)]
    req     = [sum(m.REQ[d][i] for d in range(7)) for i in range(n)]
    maxv = max(1.0, max(req), max(present))
    padx, top, base = 10, 16, H - 26
    uh = base - top
    bw = (W - 2 * padx) / n
    def Y(v): return base - (v / maxv) * uh

    parts = [f'''<defs>
      <linearGradient id="tc_cov" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="{SIGNAL}" stop-opacity="0.96"/>
        <stop offset="1" stop-color="{SIGNAL}" stop-opacity="0.40"/></linearGradient>
      <linearGradient id="tc_sur" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="{SIGNAL}" stop-opacity="0.34"/>
        <stop offset="1" stop-color="{SIGNAL}" stop-opacity="0.08"/></linearGradient>
      <filter id="tc_gl" x="-60%" y="-60%" width="220%" height="220%">
        <feGaussianBlur stdDeviation="1.3" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    </defs>''']
    curve = []
    for i in range(n):
        x = padx + i * bw
        r = req[i]; p = present[i]
        cov = min(p, r); short = max(0, r - p); over = max(0, p - r)
        gap = bw * 0.22
        xr = f'{x + gap:.2f}'; wr = f'{bw - 2 * gap:.2f}'
        if cov > 0:
            parts.append(f'<rect x="{xr}" y="{Y(cov):.2f}" width="{wr}" height="{base - Y(cov):.2f}" fill="url(#tc_cov)" rx="1"/>')
        if over > 0:
            parts.append(f'<rect x="{xr}" y="{Y(r + over):.2f}" width="{wr}" height="{Y(r) - Y(r + over):.2f}" fill="url(#tc_sur)" rx="1"/>')
        if short > 0:
            parts.append(f'<rect x="{xr}" y="{Y(cov + short):.2f}" width="{wr}" height="{Y(cov) - Y(cov + short):.2f}" fill="{CRIMSON}" rx="1" filter="url(#tc_gl)"/>')
        if r > 0 or p > 0:
            curve.append(f'{x + bw / 2:.1f},{Y(p):.2f}')
    if curve:
        parts.append(f'<polyline points="{" ".join(curve)}" fill="none" stroke="{TEXT}" '
                     f'stroke-width="1" stroke-opacity="0.5" stroke-linejoin="round"/>')
    parts.append(f'<line x1="{padx}" y1="{base:.1f}" x2="{W - padx}" y2="{base:.1f}" stroke="{LINE}" stroke-width="1"/>')
    for h in range(6, 22, 3):
        i = int(round((h - 5.5) * 4))
        if 0 <= i < n:
            x = padx + (i + 0.5) * bw
            parts.append(f'<line x1="{x:.1f}" y1="{base + 2}" x2="{x:.1f}" y2="{base + 6}" stroke="{FAINT}" stroke-width="1"/>')
            parts.append(f'<text x="{x:.1f}" y="{base + 18}" fill="{SUBTLE}" font-size="10.5" '
                         f'font-family="Inter,sans-serif" text-anchor="middle">{h:02d}:00</text>')
    return (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
            f'preserveAspectRatio="none" role="img">' + ''.join(parts) + '</svg>')

def hero_html(m):
    peak_slot = max(range(len(m.SLOTS)),
                    key=lambda i: sum(m.REQ[d][i] for d in range(7)))
    peak_t = hms(m.SLOTS[peak_slot])
    return f"""<div class="hero">
      <div class="hero-head">
        <div class="hero-title">Presidio sull'arco operativo · settimana aggregata</div>
        <div class="hero-legend">
          <span class="li"><span class="sw" style="background:{SIGNAL}"></span>Coperto</span>
          <span class="li"><span class="sw" style="background:{CRIMSON}"></span>Scoperto</span>
          <span class="li"><span class="sw" style="background:{SIGNAL}44"></span>Surplus</span>
          <span class="li" style="color:{FAINT}">picco {peak_t}</span>
        </div>
      </div>
      <div class="hero-svg">{coverage_spectrum_svg(m)}</div>
    </div>"""

# ────────────── KPI ──────────────
def kpi(value, label, unit='', delta=None, kind='default', tag='', bar_pct=None, bar_color=None, delta_color=None):
    dc = delta_color or (SIGNAL if (delta and ('▲' in str(delta) or '+' in str(delta) or 'ok' in str(delta).lower()
                               or 'nessun' in str(delta).lower())) else CRIMSON)
    dh = (f'<div class="kpi-delta" style="color:{dc}">{delta}</div>'
          if delta else '<div class="kpi-delta">&nbsp;</div>')
    unit_html = f'<span class="unit">{unit}</span>' if unit else ''
    tag_html = f'<span class="kpi-tag">{tag}</span>' if tag else ''
    pct = max(0, min(100, bar_pct)) if bar_pct is not None else 0
    bc = bar_color or SIGNAL
    bar_html = (f'<div class="kpi-bar"><div class="kpi-bar-fill" '
                f'style="width:{pct:.0f}%;background:{bc}"></div></div>')
    return (f'<div class="kpi-card {kind}">'
            f'<div class="kpi-top"><span class="kpi-label">{label}</span>{tag_html}</div>'
            f'<div class="kpi-value">{value}{unit_html}</div>{dh}{bar_html}</div>')

def legend_html(items, note=None):
    chips = ''.join(
        f'<span class="legend-item"><span class="legend-dot" style="background:{color}"></span>{label}</span>'
        for label, color in items)
    note_html = f'<span class="legend-note">{note}</span>' if note else ''
    return f'<div class="legend-row">{chips}{note_html}</div>'

def status_bar(m, backend):
    viol_n = len(m.viol)
    dot_color = SIGNAL if viol_n == 0 else (AMBER if viol_n <= 4 else CRIMSON)
    backend_dot = SIGNAL if backend == 'github' else FAINT
    backend_lbl = 'GitHub · persistente' if backend == 'github' else 'Locale · non persistente su cloud'
    chips = [
        f'<div class="status-chip">Settimana <b>{getattr(m,"WEEK","—")}</b></div>',
        f'<div class="status-chip"><span class="status-dot" style="background:{backend_dot}"></span>{backend_lbl}</div>',
        f'<div class="status-chip"><span class="status-dot" style="background:{dot_color}"></span>'
        f'{viol_n} violazion{"e" if viol_n==1 else "i"}</div>',
    ]
    return f'<div class="status-bar">{"".join(chips)}</div>'

class ScenarioView:
    def __init__(self, m, idx):
        sc = m.SCENARI[idx]
        self.idx = idx
        self.seed = sc['seed']
        self.cost = sc['cost']
        for attr in ('req_d', 'SLOTS', 'REQ', 'ENTRY', 'CLOSE', 'WEEK',
                     'ASSENTI', 'comp', 'YTD', 'A'):
            setattr(self, attr, getattr(m, attr, None))
        emp_ot, emp_mh = sc['emp_ot'], sc['emp_mh_eff']
        self.EMP = [dict(e, ot=emp_ot.get(e['id'], e['ot']),
                         mh_eff=emp_mh.get(e['id'], e.get('mh_eff', e['mh'])))
                    for e in m.EMP]
        self.shifts = sc['shifts']
        self.P = sc['P']
        self.PR = sc['PR']
        self.OT_DAY = sc['OT_DAY']
        self.DUR = sc['DUR']
        self.SEAM_BRIDGE = sc['SEAM_BRIDGE']
        self.sched = sc['sched']
        self.DAY_LABEL = sc['day_label']
        self.viol = sc['viol']

def scenario_label(sc, idx, is_best):
    base = f"Scenario {idx+1} (seed {sc['seed']})"
    tag = "  ★ scelto dal motore" if is_best else ""
    return f"{base} — violazioni: {sc['viol_n']}{tag}"

DAYS_FULL  = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
DAYS_SHORT = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']

# ────────────── GRAFICI ──────────────
def gantt(m, d):
    rows = []
    for e in m.EMP:
        s = m.shifts[e['id']][d]
        if s is None: continue
        rows.append(dict(
            Dipendente=e['name'],
            Inizio=datetime.datetime(2000, 1, 1) + datetime.timedelta(hours=s[0]),
            Fine=datetime.datetime(2000, 1, 1) + datetime.timedelta(hours=s[1]),
            Ore=round(s[1] - s[0], 2), Ruolo=e['role'],
            OT='★ Straordinario' if m.OT_DAY[e['id']][d] > 0 else 'Ordinario'))
    if not rows:
        fig = go.Figure()
        _theme(fig, height=300, legend=False)
        fig.update_layout(annotations=[dict(text='Nessun turno in questa giornata',
                          showarrow=False, font=dict(color=SUBTLE, size=13))])
        return fig
    df = pd.DataFrame(rows).sort_values('Inizio')
    fig = px.timeline(df, x_start='Inizio', x_end='Fine', y='Dipendente', color='Ruolo',
                      color_discrete_map={'RESP': RESP_BLUE, 'ADDETTO': SIGNAL},
                      hover_data={'Ore': ':.2f', 'OT': True, 'Inizio': False, 'Fine': False},
                      labels={'Dipendente': '', 'Ruolo': 'Ruolo'})
    fig.update_traces(marker_line_color=INK, marker_line_width=1, opacity=0.95)
    _theme(fig, height=max(300, len(rows) * 32) + 24)
    fig.update_layout(
        xaxis=dict(tickformat='%H:%M', gridcolor=LINE, title='', zerolinecolor=LINE),
        yaxis=dict(autorange='reversed', title='', gridcolor=LINE),
        bargap=0.3)
    entry = m.ENTRY[d]; close = m.CLOSE[d] if isinstance(m.CLOSE, list) else m.CLOSE
    for hv, lb, col, pos in [(entry, 'Apertura', RESP_BLUE, 'top right'),
                             (close, 'Chiusura', AMBER, 'top left')]:
        t = datetime.datetime(2000, 1, 1) + datetime.timedelta(hours=hv)
        fig.add_vline(x=t, line_width=1.4, line_dash='dot', line_color=col,
                      annotation_text=lb, annotation_position=pos,
                      annotation_font_color=col, annotation_font_size=10)
    return fig

def heatmap(m):
    slots = m.SLOTS; step = 2; Z = []; TXT = []
    for d in range(7):
        rz = []; rt = []
        for i in range(0, min(len(slots), len(m.P[d]), len(m.REQ[d])), step):
            delta = m.P[d][i] - m.REQ[d][i]
            rz.append(delta)
            sign = '+' if delta > 0 else ''
            rt.append(f"{hms(slots[i])}<br>{m.P[d][i]}/{m.REQ[d][i]}<br>{sign}{delta}")
        Z.append(rz); TXT.append(rt)
    tl = [f"{int(s):02d}" if i % 2 == 0 else '' for i, s in enumerate(slots[::step])]
    x_uid = [f"{i}" for i in range(len(tl))]
    fig = go.Figure(go.Heatmap(
        z=Z, x=x_uid, y=DAYS_SHORT, customdata=TXT,
        hovertemplate='%{customdata}<extra>%{y}</extra>',
        xgap=2, ygap=3,
        colorscale=[[0, CRIMSON], [.40, AMBER], [.5, LINE], [.62, SIGNAL_DK], [1, SIGNAL]],
        zmid=0, showscale=True,
        colorbar=dict(thickness=12, outlinewidth=0, len=0.9,
                      title=dict(text='surplus / scoperto', side='right',
                                 font=dict(size=10, color=SUBTLE)),
                      tickfont=dict(size=9, color=SUBTLE))))
    _theme(fig, height=270, legend=False)
    fig.update_layout(
        xaxis=dict(title='', tickmode='array', tickvals=x_uid, ticktext=tl,
                   tickfont=dict(size=10, color=SUBTLE), showgrid=False),
        yaxis=dict(title='', autorange='reversed',
                   tickfont=dict(color=SUBTLE), showgrid=False))
    return fig

def daily_bars(m):
    req = [round(x, 1) for x in m.req_d]; sch = [round(x, 1) for x in m.sched]
    ot = [round(sum(m.OT_DAY[e['id']][d] for e in m.EMP), 1) for d in range(7)]
    ordinary = [round(s - o, 1) for s, o in zip(sch, ot)]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=DAYS_SHORT, y=req, name='Richiesto',
                         marker_color='rgba(0,0,0,0)', marker_line=dict(color=FAINT, width=1.2),
                         hovertemplate='Richiesto %{y:.1f} h<extra></extra>'))
    fig.add_trace(go.Bar(x=DAYS_SHORT, y=ordinary, name='Ordinario',
                         marker_color=SIGNAL, marker_line_width=0,
                         hovertemplate='Ordinario %{y:.1f} h<extra></extra>'))
    fig.add_trace(go.Bar(x=DAYS_SHORT, y=ot, name='Straordinario',
                         marker_color=AMBER, marker_line_width=0,
                         hovertemplate='Straordinario %{y:.1f} h<extra></extra>'))
    _theme(fig, height=270)
    fig.update_layout(barmode='overlay',
                      yaxis=dict(gridcolor=LINE, title='ore'),
                      xaxis=dict(gridcolor='rgba(0,0,0,0)'),
                      bargap=0.35)
    fig.data[2].base = ordinary
    return fig

def ot_bar(m):
    data = sorted([(e['name'], e['ot']) for e in m.EMP if e['ot'] > 0], key=lambda x: -x[1])
    if not data: return None
    ns, os_ = zip(*data)
    fig = go.Figure(go.Bar(x=list(os_), y=list(ns), orientation='h', marker_color=AMBER,
                           marker_line_width=0, text=[f"{o:.2f}h" for o in os_],
                           textposition='outside', textfont=dict(color=TEXT, family='Inter'),
                           hovertemplate='%{y}: %{x:.2f} h<extra></extra>'))
    _theme(fig, height=max(180, len(data) * 38), legend=False)
    fig.update_layout(margin=dict(l=8, r=60, t=10, b=8),
                      xaxis=dict(title='ore straordinario', gridcolor=LINE),
                      yaxis=dict(title='', autorange='reversed', gridcolor='rgba(0,0,0,0)'))
    return fig

# ────────────── SOSTENIBILITÀ ──────────────
_FIXED_KEYS = ('barriera', 'presidio', 'fisse', 'settimanal')

def _read_volumi(xlsx_path):
    key = '_vol_' + str(xlsx_path)
    if key in st.session_state:
        return st.session_state[key]
    pezzi, fatt = 136000, 226000
    try:
        import openpyxl
        wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
        P = wb['Parametri']
        if isinstance(P['B6'].value, (int, float)): pezzi = P['B6'].value
        if isinstance(P['B5'].value, (int, float)): fatt = P['B5'].value
        wb.close()
    except Exception:
        pass
    st.session_state[key] = (pezzi, fatt)
    return pezzi, fatt

def _read_benchmark(xlsx_path):
    """Legge il benchmark produttività da Parametri cercando le etichette (non celle fisse:
    la riga si è già spostata più volte in questo file), e la nota 'range tipici' se presente,
    per un controllo di coerenza automatico sulla pagina Sostenibilità."""
    key = '_bench_' + str(xlsx_path)
    if key in st.session_state:
        return st.session_state[key]
    out = {'min': None, 'max': None, 'note_min': None, 'note_max': None}
    try:
        import openpyxl, re as _re
        wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
        P = wb['Parametri']
        for row in P.iter_rows(min_col=1, max_col=2):
            lab = row[0].value
            if not isinstance(lab, str):
                continue
            low = lab.lower()
            if 'produttivit' in low and 'minima' in low and 'pezz' in low and isinstance(row[1].value, (int, float)):
                out['min'] = row[1].value
            elif 'produttivit' in low and 'massima' in low and 'pezz' in low and isinstance(row[1].value, (int, float)):
                out['max'] = row[1].value
            elif 'tipici' in low or 'tipico' in low:
                m = _re.search(r'(\d+)\s*-\s*(\d+)\s*pz', lab, _re.I)
                if m:
                    out['note_min'], out['note_max'] = int(m.group(1)), int(m.group(2))
        wb.close()
    except Exception:
        pass
    st.session_state[key] = out
    return out

def _build_sost_report(rowspec, comp, R, target, ore_target, gap, t_sost, ore_ly, rid_var):
    import io as _io, openpyxl
    from openpyxl.styles import Font
    from openpyxl.chart import BarChart, Reference
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Sintesi'
    ws['A1'] = 'ANALISI SOSTENIBILITÀ TARGET — sintesi per la direzione'
    ws['A1'].font = Font(bold=True, size=14, color='0B3D2E')
    ws['A3'] = 'Voce'; ws['B3'] = 'Valore'; ws['A3'].font = ws['B3'].font = Font(bold=True)
    for i, (k, v) in enumerate(rowspec):
        ws.cell(row=4 + i, column=1, value=k); ws.cell(row=4 + i, column=2, value=v)
    ws.column_dimensions['A'].width = 50; ws.column_dimensions['B'].width = 16
    verdetto = "NON SOSTENIBILE" if gap > 0 else "SOSTENIBILE"
    concl = (f"VERDETTO: target {verdetto}. Il target di {target:.0f} pz/h implica un budget di "
             f"{ore_target:.0f} h, contro {R:.0f} h di lavoro misurato: {gap:.0f} h/sett "
             f"{'scoperte' if gap > 0 else 'di margine'}, a parità di volume e senza miglioramenti di "
             f"processo. Target sostenibile calibrato sul modello: {t_sost:.0f} pz/h. "
             + (f"Il taglio cade sul rifornimento (-{rid_var:.0f}% di capacità), non sulle attività "
                f"non comprimibili (casse/SCO/pulizie)." if gap > 0 else ""))
    rr = 5 + len(rowspec)
    ws.cell(row=rr, column=1, value='Conclusione:').font = Font(bold=True)
    ws.cell(row=rr + 1, column=1, value=concl)
    wa = wb.create_sheet('Attività')
    for j, t in enumerate(['Attività', 'Ore', '% su fabbisogno', 'Tipo']):
        wa.cell(row=1, column=1 + j, value=t).font = Font(bold=True)
    for i, (n, h) in enumerate(sorted(comp, key=lambda x: -x[1])):
        tipo = 'Non comprimibile' if any(k in str(n).lower() for k in _FIXED_KEYS) else 'Comprimibile'
        wa.cell(row=2 + i, column=1, value=n); wa.cell(row=2 + i, column=2, value=round(h, 1))
        wa.cell(row=2 + i, column=3, value=round(h / R * 100, 1) if R else 0)
        wa.cell(row=2 + i, column=4, value=tipo)
    wa.column_dimensions['A'].width = 42
    wc = wb.create_sheet('Ore a confronto')
    wc['A1'] = 'Voce'; wc['B1'] = 'Ore'
    conf = [('Fabbisogno misurato', round(R, 1)), ('Budget dal target', round(ore_target, 1)),
            ('Anno scorso (pari volume)', round(ore_ly, 1))]
    for i, (k, v) in enumerate(conf):
        wc.cell(row=2 + i, column=1, value=k); wc.cell(row=2 + i, column=2, value=v)
    ch = BarChart(); ch.title = 'Ore: fabbisogno vs budget target vs anno scorso'
    ch.add_data(Reference(wc, min_col=2, min_row=1, max_row=1 + len(conf)), titles_from_data=True)
    ch.set_categories(Reference(wc, min_col=1, min_row=2, max_row=1 + len(conf)))
    wc.add_chart(ch, 'D2'); wc.column_dimensions['A'].width = 26
    buf = _io.BytesIO(); wb.save(buf); return buf.getvalue()

def analisi_sostenibilita(m, xlsx_path):
    st.markdown('<div class="section-title">Sostenibilità del target'
                '<span class="st-note">target assegnato vs fabbisogno misurato</span></div>',
                unsafe_allow_html=True)
    st.caption("Il fabbisogno è calcolato dal modello riga per riga (minuti/PLT · attività fisse e "
               "settimanali · casse e SCO), letto dal foglio OreRichieste. La produttività, a volume "
               "costante, sale solo se il lavoro diventa più veloce: senza migliorie di processo, un "
               "target più alto equivale a cancellare ore di lavoro reale.")

    pezzi0, fatt0 = _read_volumi(xlsx_path)
    c1, c2, c3 = st.columns(3)
    pezzi = c1.number_input("Pezzi / settimana", min_value=1, value=int(pezzi0), step=1000)
    target = c2.number_input("Target assegnato (pz/h)", min_value=1.0, value=262.0, step=1.0)
    prod_ly = c3.number_input("Produttività anno scorso (pz/h)", min_value=1.0, value=248.0, step=1.0,
                              help="Quanto facevi l'anno scorso, a pari volume — è il termine di "
                                   "paragone storico, non un'ipotesi.")
    ore_ly = pezzi / prod_ly if prod_ly else 0

    # --- fabbisogno dal modello vivo (stesso motore che genera i turni) ---
    R = sum(m.req_d)
    comp = [(n, h) for n, h in getattr(m, 'comp', []) if h and isinstance(h, (int, float)) and h > 0]
    fixed = sum(h for n, h in comp if any(k in str(n).lower() for k in _FIXED_KEYS))
    var = max(0.0, R - fixed)
    fixed_pct = (fixed / R * 100) if R else 0
    monte_contratto = sum(e.get('mh_contratto', e['mh']) for e in m.EMP) + sum(a[2] for a in getattr(m, 'ASSENTI', []))
    monte_presenti = sum(e['mh'] for e in m.EMP)
    n_assenti = len(getattr(m, 'ASSENTI', []) or [])

    ore_target = pezzi / target if target else 0
    gap = R - ore_target
    t_sost = pezzi / R if R else 0
    taglio = max(0.0, gap)
    var_res = max(0.0, var - taglio)
    rid_var = (taglio / var * 100) if var else 0
    non_sostenibile = target > t_sost

    # --- verdetto: netto, senza ambiguità ---
    if non_sostenibile:
        st.error(f"**TARGET NON SOSTENIBILE.** A {target:.0f} pz/h il budget è **{ore_target:.0f} h**, "
                 f"ma il lavoro misurato ne richiede **{R:.0f} h** → **{gap:.0f} h/settimana scoperte**, "
                 f"a parità di volume e senza alcuna miglioria di processo. Il target che il modello "
                 f"regge oggi è **{t_sost:.0f} pz/h**.")
    else:
        st.success(f"**TARGET SOSTENIBILE.** A {target:.0f} pz/h il budget è **{ore_target:.0f} h**, "
                   f"entro le **{R:.0f} h** misurate dal modello — margine di **{-gap:.0f} h**.")

    # delta_color esplicito qui (non l'auto-detect di kpi()): un segno '+' nello scoperto
    # è una notizia negativa per noi — l'opposto di quello che l'euristica di kpi() assumerebbe.
    cards = [
        kpi(f"{R:.0f}", "Fabbisogno misurato", unit="h", tag="modello"),
        kpi(f"{ore_target:.0f}", "Budget dal target", unit="h", tag=f"{target:.0f} pz/h",
            kind='alert' if gap > 0 else 'ok'),
        kpi(f"{gap:+.0f}", "Scoperto vs fabbisogno", unit="h",
            kind='alert' if gap > 0 else 'ok',
            delta=("richiede taglio sul comprimibile" if gap > 0 else "entro il fabbisogno misurato"),
            delta_color=(CRIMSON if gap > 0 else SIGNAL),
            bar_pct=min(100, abs(gap) / R * 100) if R else 0, bar_color=CRIMSON if gap > 0 else SIGNAL),
        kpi(f"{t_sost:.0f}", "Target sostenibile", unit="pz/h", tag=f"assegnato {target:.0f}",
            kind='ok' if not non_sostenibile else 'alert'),
    ]
    st.markdown(f'<div class="kpi-row" style="grid-template-columns:repeat(4,1fr)">{"".join(cards)}</div>',
                unsafe_allow_html=True)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    cresciuto = R > ore_ly
    st.caption(f"Per confronto: l'anno scorso, a {prod_ly:.0f} pz/h, servivano **{ore_ly:.0f} h**. Il "
               f"fabbisogno misurato oggi ({R:.0f} h) è {'più alto' if cresciuto else 'più basso'} — "
               + (f"controlla nella verifica dati qui sotto cosa è cambiato (nuove attività, input "
                  f"aggiornati) prima di portare il numero in direzione." if cresciuto else
                  f"il confronto storico gioca a tuo favore."))

    # --- fisso vs comprimibile ---
    st.markdown('<div class="section-title">Fabbisogno: cosa è comprimibile</div>', unsafe_allow_html=True)
    st.markdown(legend_html([(f'Non comprimibile · casse, SCO, fisse ({fixed_pct:.0f}%)', SUBTLE),
                             (f'Comprimibile · rifornimento ({100 - fixed_pct:.0f}%)', SIGNAL)],
                            note="il taglio del target cade tutto sul comprimibile"), unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(y=['Fabbisogno'], x=[fixed], name='Non comprimibile', orientation='h', marker_color=SUBTLE))
    fig.add_trace(go.Bar(y=['Fabbisogno'], x=[var], name='Comprimibile', orientation='h', marker_color=SIGNAL))
    fig.add_vline(x=ore_target, line_width=2, line_dash='dash', line_color=CRIMSON,
                  annotation_text=f'Budget target {ore_target:.0f}h', annotation_position='top')
    fig.add_vline(x=ore_ly, line_width=1.5, line_dash='dot', line_color=AMBER,
                  annotation_text=f'Anno scorso {ore_ly:.0f}h', annotation_position='bottom')
    fig.update_layout(barmode='stack')
    _theme(fig, height=200, legend=True)
    st.plotly_chart(fig, width='stretch', config={'displayModeBar': False})
    if gap > 0:
        st.warning(f"Le **{fixed:.0f} h non comprimibili** ({fixed_pct:.0f}% del fabbisogno) restano "
                   f"intatte. Le **{gap:.0f} h** tagliate cadono sul rifornimento: **-{rid_var:.0f}%** "
                   f"di capacità ({var:.0f} h → {var_res:.0f} h) = scaffali non riforniti, rotture di "
                   f"stock, vendite perse — sullo stesso fatturato su cui è calcolato il target.")

    # --- confronto ore, con il contesto organico della settimana ---
    st.markdown('<div class="section-title">Ore: fabbisogno vs budget vs storico'
                f'<span class="st-note">{monte_presenti:.0f} h presenti questa settimana '
                f'({n_assenti} assenti) · {monte_contratto:.0f} h a contratto (tutti)</span></div>',
                unsafe_allow_html=True)
    cb = go.Figure(go.Bar(
        x=['Fabbisogno<br>misurato', 'Budget<br>dal target', f'Anno scorso<br>({prod_ly:.0f} pz/h)', 'Presenti<br>oggi'],
        y=[R, ore_target, ore_ly, monte_presenti],
        marker_color=[SUBTLE, CRIMSON if gap > 0 else SIGNAL, AMBER, RESP_BLUE],
        text=[f'{v:.0f} h' for v in [R, ore_target, ore_ly, monte_presenti]], textposition='outside',
        textfont=dict(color=TEXT)))
    cb.add_hline(y=R, line_dash='dash', line_color=SUBTLE, annotation_text='fabbisogno', annotation_position='right')
    _theme(cb, height=290, legend=False)
    st.plotly_chart(cb, width='stretch', config={'displayModeBar': False})
    if monte_presenti < R:
        st.caption(f"Nota a parte, indipendente dal target: questa settimana hai {n_assenti} assenti, quindi "
                   f"solo {monte_presenti:.0f} h presenti contro {R:.0f} h di fabbisogno — il buco è coperto "
                   f"da straordinario, non dal target.")

    with st.expander("Dettaglio ore per attività (verifica riga per riga)"):
        rows = [{'Attività': n, 'Ore': round(h, 1), '%': f"{h / R * 100:.0f}%" if R else '—',
                 'Tipo': 'Non comprimibile' if any(k in str(n).lower() for k in _FIXED_KEYS) else 'Comprimibile'}
                for n, h in sorted(comp, key=lambda x: -x[1])]
        st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
        st.caption("Controlla che nessuna attività compaia due volte tra le righe fisse/settimanali e "
                   "quelle di rifornimento (stesso compito contato in due punti diversi).")

    # --- verifica coerenza dati: controlli automatici + promemoria manuale ---
    bench = _read_benchmark(xlsx_path)
    issues = []
    if bench.get('min') is not None and bench.get('max') is not None:
        bmin, bmax = bench['min'], bench['max']
        if bmax - bmin < 5:
            issues.append(f"Il benchmark produttività in Parametri è **{bmin:.0f}–{bmax:.0f} pz/h**: un "
                           f"intervallo di soli {bmax - bmin:.0f} punti è molto stretto per un benchmark — "
                           f"verifica non sia un singolo valore digitato per errore in due celle.")
        if bench.get('note_max') is not None and bmax > bench['note_max']:
            issues.append(f"Il benchmark impostato (**{bmin:.0f}–{bmax:.0f} pz/h**) è sopra il range "
                           f"tipico dichiarato nella nota di Parametri (**{bench['note_min']}–"
                           f"{bench['note_max']} pz/h**). Controlla quale dei due è corretto prima di "
                           f"usarlo con la direzione.")
    st.markdown('<div class="section-title">Verifica dati</div>', unsafe_allow_html=True)
    if issues:
        for msg in issues:
            st.warning(msg)
    else:
        st.success("Nessuna incoerenza rilevata automaticamente sul benchmark di Parametri.")
    st.caption("Controlli automatici limitati: verifica comunque a mano che i minuti/PLT e la quota SCO "
               "vengano da dati di cassa/cronometro reali (non stime), non da un valore digitato per far "
               "tornare il conto.")

    # --- report ---
    st.markdown('<div class="section-title">Report per la direzione</div>', unsafe_allow_html=True)
    try:
        rowspec = [
            ('Volume settimanale (pezzi)', int(pezzi)),
            ('Target assegnato (pz/h)', round(target, 1)),
            ('Budget-ore implicito dal target', round(ore_target, 1)),
            ('Fabbisogno misurato dal modello (h)', round(R, 1)),
            ('Scoperto vs fabbisogno (h/sett)', round(gap, 1)),
            ('Target sostenibile dal modello (pz/h)', round(t_sost, 1)),
            ('Produttività anno scorso (pz/h)', round(prod_ly, 1)),
            ('Ore anno scorso (pari volume)', round(ore_ly, 1)),
            ('Ore non comprimibili — casse/SCO/fisse (h)', round(fixed, 1)),
            ('Quota non comprimibile sul fabbisogno', f"{fixed_pct:.0f}%"),
            ('Ore comprimibili — rifornimento (h)', round(var, 1)),
            ('Riduzione capacità rifornimento imposta dal target', f"-{rid_var:.0f}%"),
            ("Monte ore a contratto — tutto l'organico (h)", round(monte_contratto, 1)),
            ('Monte ore presenti questa settimana (h)', round(monte_presenti, 1)),
            ('Assenti questa settimana', n_assenti),
        ]
        data = _build_sost_report(rowspec, comp, R, target, ore_target, gap, t_sost, ore_ly, rid_var)
        st.download_button("Scarica report sostenibilità (Excel)", data=data,
                           file_name="Analisi_Sostenibilita.xlsx",
                           mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                           width='stretch')
    except Exception as ex:
        st.error(f"Report non generato: {ex}")

# ────────────── MAIN ──────────────
def main():
    st.markdown(CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(f"""<div class="rail-brand">
          <div class="rail-mark">{_rail_mark_html()}</div>
          <div><div class="rail-title">ThinkCore</div>
          <div class="rail-sub">Analisi dati, controllo costi e pianificazione turni retail</div></div>
        </div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
        gen_btn = st.button("▶  GENERA TURNI", width='stretch', type="primary",
                            disabled=(st.session_state.get('xlsx_uploader') is None))
        st.markdown("---")
        st.markdown('<div class="rail-eyebrow">Modello dati</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader("MODELLO EXCEL", type=['xlsx'],
                                    key='xlsx_uploader', label_visibility='collapsed',
                                    help="Carica TOOL_LIDL.xlsx — salvalo prima in Excel!")
        st.markdown("---")
        st.markdown('<div class="rail-eyebrow">Opzioni generazione</div>', unsafe_allow_html=True)
        use_ot = st.checkbox("Auto-straordinari", value=True)
        use_cmp = st.checkbox("Modalità scenari 5×", value=True)
        use_co = st.checkbox("Ottimizza costi OT", value=False)
        st.markdown("---")
        week_in = st.text_input("SETTIMANA ISO (opz.)", placeholder="es. 2026-W31")
        st.markdown("---")
        _backend = cloud_storage.backend_name()
        _dot = SIGNAL if _backend == 'github' else FAINT
        _backend_lbl = 'GitHub · persistente' if _backend == 'github' else 'Locale · non persistente su cloud'
        st.markdown(f'''<div class="rail-status">
            <b>ThinkCore</b> v2.6 · build 2026-09-10<br>
            <span class="status-dot" style="background:{_dot}"></span>{_backend_lbl}
        </div>''', unsafe_allow_html=True)

    st.markdown(f"""<div class="top-banner">
      <div class="top-banner-row">
        <div>
          <h1>THINKCORE<span class="dot">.</span><span class="sub-inline">Analisi dati, controllo costi e pianificazione turni retail</span></h1>
        </div>
        <div class="banner-badge">
          <span class="bb-k">Arco operativo</span>
          <span class="bb-v">05:30 – 21:15</span>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    if 'result' not in st.session_state: st.session_state.result = None

    if gen_btn and uploaded:
        tmp = '/tmp/rotosmart'; os.makedirs(tmp, exist_ok=True)
        path = os.path.join(tmp, uploaded.name)
        with open(path, 'wb') as f: f.write(uploaded.getvalue())
        extra = []
        if use_ot:  extra += ['--auto-ot']
        if use_cmp: extra += ['--compare', '5']
        if use_co:  extra += ['--cost-opt']
        if week_in.strip(): extra += ['--settimana', week_in.strip()]

        with st.spinner("Sincronizzazione stato (straordinari, riposi, storico)…"):
            pull_report = cloud_storage.pull(tmp)
        with st.spinner("Generazione turni in corso…"):
            m, stdout, stderr = run_engine(path, extra)
        with st.spinner("Salvataggio stato aggiornato…"):
            push_report = cloud_storage.push(tmp)

        st.session_state.result = dict(m=m, stdout=stdout, stderr=stderr, xlsx_path=path,
                                       pull_report=pull_report, push_report=push_report)
        st.session_state.scenario_idx = getattr(m, 'BEST_SCENARIO_IDX', 0)
        for k in list(st.session_state.keys()):
            if k.startswith('edit_state_') or k == '_grid_v':
                st.session_state.pop(k, None)

    r = st.session_state.result
    if r is None:
        st.markdown(f"""<div class="empty-state">
          <div class="glyph">
            <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 7.5a2 2 0 0 1 2-2h4.2l1.8 2H19a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7Z"/>
              <path d="M12 11v6M9.2 13.8 12 11l2.8 2.8"/>
            </svg>
          </div>
          <div class="title">Carica il modello e genera i turni</div>
          <div class="sub">Carica <b>TOOL_LIDL.xlsx</b> dal pannello a sinistra e premi
            <b>Genera turni</b>. Il motore legge organico, fabbisogno, riposi e vincoli CCNL
            e restituisce la rotazione della settimana.</div>
        </div>""", unsafe_allow_html=True)
        return

    m = r['m']
    scenari = getattr(m, 'SCENARI', [])
    best_idx = getattr(m, 'BEST_SCENARIO_IDX', 0)

    st.markdown(status_bar(m, cloud_storage.backend_name()), unsafe_allow_html=True)

    if len(scenari) > 1:
        cur = st.session_state.get('scenario_idx', best_idx)
        if cur not in range(len(scenari)): cur = best_idx
        st.markdown(f'<div class="section-title">Scenario'
                    f'<span class="st-note">{scenario_label(scenari[cur], cur, cur == best_idx)}</span></div>',
                    unsafe_allow_html=True)
        cols = st.columns(len(scenari))
        for i, sc in enumerate(scenari):
            with cols[i]:
                label = f"{'★ ' if i == best_idx else ''}S{i + 1}"
                if st.button(label, key=f"scenario_btn_{i}", width='stretch',
                             type="primary" if i == cur else "secondary"):
                    cur = i
                st.caption(f"viol {sc['viol_n']}")
        st.session_state.scenario_idx = cur
        sel = cur
        active = ScenarioView(m, sel)
    else:
        st.session_state.scenario_idx = 0
        active = ScenarioView(m, 0)

    write_key = f"{r['xlsx_path']}::{active.idx}"
    if st.session_state.get('_write_key') != write_key:
        try:
            with st.spinner("Scrittura diretta nel foglio Turni…"):
                out_xlsx = os.path.join(os.path.dirname(r['xlsx_path']),
                    f"TOOL_LIDL_{getattr(m,'WEEK','') or 'aggiornato'}_S{active.idx+1}.xlsx")
                write_shifts_surgical(r['xlsx_path'], out_xlsx, active.EMP, active.shifts,
                                      day_label=active.DAY_LABEL)
            r['out_xlsx'] = out_xlsx
            r['write_error'] = None
        except Exception as ex:
            r['out_xlsx'] = None
            r['write_error'] = str(ex)
        st.session_state['_write_key'] = write_key

    m = active

    st.markdown(hero_html(m), unsafe_allow_html=True)

    tot_req = sum(m.req_d); tot_sch = sum(m.sched)
    tot_ot = sum(e['ot'] for e in m.EMP)
    marg = sum(e['mh'] for e in m.EMP) - tot_req
    marg_p = marg / tot_req * 100 if tot_req else 0
    viol_n = len(m.viol)

    cov_pct = (tot_sch / tot_req * 100) if tot_req else 0
    marg_bar = max(0, min(100, (marg_p + 5) / 20 * 100))
    ot_bar_pct = min(100, tot_ot / (0.06 * tot_req) * 100) if tot_req and tot_ot else 0
    ot_pct = (tot_ot / tot_req * 100) if tot_req else 0
    ot_kind = 'ok' if tot_ot == 0 else ('alert' if ot_pct > 6 else 'warn')
    viol_bar_pct = min(100, viol_n / 10 * 100) if viol_n else 0

    kpi_cards = [
        kpi(f"{tot_req:.0f}", "Ore richieste", unit="h", tag="fabbisogno",
            bar_pct=100, bar_color=LINE_SOFT),
        kpi(f"{tot_sch:.0f}", "Ore pianificate", unit="h",
            tag=f"{cov_pct:.0f}%",
            delta=("▲ copre il fabbisogno" if cov_pct >= 100 else f"{tot_req-tot_sch:.0f} h sotto il fabbisogno"),
            kind='ok' if cov_pct >= 100 else 'warn',
            bar_pct=cov_pct, bar_color=SIGNAL if cov_pct >= 100 else AMBER),
        kpi(f"{marg:+.1f}", "Margine strutturale", unit="h",
            delta=f"{marg_p:+.1f}%  ·  target ≥ 4%",
            kind='ok' if marg_p >= 4 else ('warn' if marg_p >= 0 else 'alert'),
            bar_pct=marg_bar, bar_color=SIGNAL if marg_p >= 4 else (AMBER if marg_p >= 0 else CRIMSON)),
        kpi(f"{tot_ot:.1f}", "Straordinari", unit="h",
            tag="vs 6% soglia",
            delta=("nessuno" if tot_ot == 0 else f"{ot_pct:.1f}% del fabbisogno"),
            kind=ot_kind,
            bar_pct=ot_bar_pct, bar_color=(CRIMSON if ot_kind == 'alert' else AMBER)),
        kpi(str(viol_n), "Violazioni residue",
            delta="nessuna — piano a norma" if viol_n == 0 else f"{viol_n} da risolvere",
            kind='ok' if viol_n == 0 else ('warn' if viol_n <= 4 else 'alert'),
            bar_pct=viol_bar_pct, bar_color=CRIMSON),
    ]
    st.markdown(f'<div class="kpi-row">{"".join(kpi_cards)}</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # --- scenario assenze: stesso semaforo a 4 stati e barra di capacità del Centro Comando Excel ---
    # NB: la base è mh_contratto (monte ore lordo), non mh (ore effettive/flessibili post permessi
    # e turni fissi) — solo così il deficit combacia con Excel invece di un numero diverso e fuorviante.
    assenti_now = getattr(m, 'ASSENTI', []) or []
    n_assenti_now = len(assenti_now)
    ore_perse_now = sum(a[2] for a in assenti_now)
    monte_presenti_now = sum(e.get('mh_contratto', e['mh']) for e in m.EMP)
    deficit_now = max(0, tot_req - monte_presenti_now)
    if deficit_now == 0:
        dfc_kind, dfc_color, dfc_badge = 'ok', SIGNAL, '🟢 OK'
        dfc_msg = 'copertura garantita, nessun intervento'
    elif deficit_now <= 50:
        dfc_kind, dfc_color, dfc_badge = 'warn', AMBER, '🟡 JOLLY'
        dfc_msg = f'{math.ceil(deficit_now / 25)} jolly (su 2) coprono il buco'
    elif deficit_now <= 90:
        dfc_kind, dfc_color, dfc_badge = 'hot', ORANGE, '🟠 JOLLY+OT'
        dfc_msg = f'2 jolly + {deficit_now - 50:.0f}h di straordinario'
    else:
        dfc_kind, dfc_color, dfc_badge = 'alert', CRIMSON, '🔴 CRITICO'
        dfc_msg = f'deficit {deficit_now:.0f}h: oltre 2 jolly + straordinari legali'
    st.markdown('<div class="section-title">Scenario assenze'
                '<span class="st-note">stessa lettura del Centro Comando Excel · '
                'segna le assenze nel foglio Personale</span></div>', unsafe_allow_html=True)
    sc_cards = [
        kpi(f"{n_assenti_now}", "Assenze", tag="questa settimana"),
        kpi(f"{ore_perse_now:.0f}", "Ore perse", unit="h"),
        kpi(f"{deficit_now:.0f}", "Deficit", unit="h", tag=dfc_badge,
            kind=dfc_kind, delta=dfc_msg, delta_color=dfc_color,
            bar_pct=min(100, deficit_now / 200 * 100), bar_color=dfc_color),
    ]
    st.markdown(f'<div class="kpi-row" style="grid-template-columns:repeat(3,1fr)">{"".join(sc_cards)}</div>',
                unsafe_allow_html=True)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    t1, t_edit, t2, t3, t4, t5, t6 = st.tabs(["Rotazione settimanale", "Modifica turni", "Copertura",
                                              "Giornata", "Straordinari", "Console", "Sostenibilità"])

    # TAB 1 ── ROTA
    with t1:
        st.markdown(f'<div class="section-title">Rotazione settimanale'
                    f'<span class="st-note">{getattr(m,"WEEK","—")}</span></div>', unsafe_allow_html=True)
        assenti_list = getattr(m, 'ASSENTI', [])
        if assenti_list:
            st.warning("Assenti questa settimana: " + ", ".join(f"{n} ({t})" for n, t, _ in assenti_list))
        rows = []
        for e in m.EMP:
            row = {'Dipendente': e['name'], 'Ruolo': e['role'], 'Ore': int(e['mh'])}
            for d, ds in enumerate(DAYS_SHORT):
                s = m.shifts[e['id']][d]
                row[ds] = 'R' if s is None else f"{hms(s[0])}–{hms(s[1])}{'★' if m.OT_DAY[e['id']][d]>0 else ''}"
            rows.append(row)
        df_rota = pd.DataFrame(rows)
        def style_rota(val):
            if val == 'R': return f'background:{SURFACE_2};color:{FAINT};font-weight:500;text-align:center'
            if '★' in str(val): return f'background:{AMBER}26;color:{TEXT};font-weight:600;text-align:center;font-size:.8rem'
            return f'color:{TEXT};text-align:center;font-size:.8rem'
        _sf = getattr(df_rota.style, 'map', None) or getattr(df_rota.style, 'applymap')
        styled = _sf(style_rota, subset=DAYS_SHORT)
        st.dataframe(styled, width='stretch', height=min(800, 88 + len(m.EMP) * 36))
        if m.viol:
            st.markdown('<div class="section-title">Violazioni residue</div>', unsafe_allow_html=True)
            st.markdown(''.join(f'<span class="viol-pill">{v}</span>' for v in m.viol), unsafe_allow_html=True)
        else:
            st.success("Nessuna violazione — stacchi, coperture e presidio responsabile a norma.")
        st.markdown('<div class="section-title">Ore per giorno<span class="st-note">'
                    'ordinario + straordinario vs richiesto</span></div>', unsafe_allow_html=True)
        st.plotly_chart(daily_bars(m), width='stretch', config={'displayModeBar': False})
        if r.get('write_error'):
            st.error(f"Scrittura diretta non riuscita: {r['write_error']} — controlla il tab Console.")
        elif r.get('out_xlsx') and os.path.exists(r['out_xlsx']):
            with open(r['out_xlsx'], 'rb') as f:
                st.download_button("Scarica TOOL_LIDL.xlsx aggiornato (turni già scritti)",
                                   data=f.read(), file_name=os.path.basename(r['out_xlsx']),
                                   mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                   width='stretch')
            st.success("Turni scritti nel foglio Turni — nessun copia-incolla. "
                       "Scarica il file e salvalo al posto del tuo TOOL_LIDL.xlsx.")
        else:
            st.warning("File Excel non trovato — controlla il tab Console per gli errori.")

    # ─────────────────────────────────────────────────────────
    # TAB EDIT ── MODIFICA TURNI (restyling v2.5)
    # ─────────────────────────────────────────────────────────
    with t_edit:
        st.markdown('<div class="section-title">Modifica turni'
                    '<span class="st-note">inizio e fine separati · step 30 min</span></div>',
                    unsafe_allow_html=True)

        rawm = r['m']
        ver = st.session_state.get('_edit_ver', 0)
        grid_v = st.session_state.get('_grid_v', 0)
        labs_all = getattr(active, 'DAY_LABEL', {}) or {}

        # ── stato condiviso tra le due modalità ──
        state_key = f"edit_state_{active.idx}_{ver}"
        if state_key not in st.session_state:
            st.session_state[state_key] = {
                e['id']: [active.shifts[e['id']][d] for d in range(7)]
                for e in active.EMP
            }
        state = st.session_state[state_key]

        # ── toolbar: modalità ──
        edit_mode = st.radio("Modalità", ["± 30 min", "Testo"], horizontal=True,
                             label_visibility='collapsed',
                             key=f"edit_mode_{active.idx}")

        if edit_mode == "± 30 min":
            st.caption("Seleziona il giorno dalla **strip** qui sotto. Per ogni dipendente "
                       "regoli **inizio** (blu) e **fine** (ambra) con i pulsanti **−** / **+**. "
                       "Le celle **R** / **P** non hanno pulsanti.")

            # ── ore settimanali per la strip (calcolate dallo stato corrente) ──
            wk_hours = [0.0] * 7
            for e in active.EMP:
                for d in range(7):
                    ss = state[e['id']][d]
                    if ss:
                        wk_hours[d] += (ss[1] - ss[0])

            # ── selettore giorno: leggo prima il valore dallo stato, disegno la strip,
            #    poi il radio sotto la conferma/aggiorna ──
            radio_key = f"edit_day_{active.idx}_{ver}"
            if radio_key not in st.session_state:
                st.session_state[radio_key] = DAYS_FULL[0]
            cur_day_lbl = st.session_state[radio_key]
            if cur_day_lbl not in DAYS_FULL:
                cur_day_lbl = DAYS_FULL[0]
            day_idx = DAYS_FULL.index(cur_day_lbl)

            # strip settimanale: evidenzia il giorno attivo
            # strip settimanale: evidenzia il giorno attivo
            parts = []
            for i in range(7):
                is_active = (i == day_idx)
                bg     = f"{SIGNAL}1E" if is_active else "transparent"
                bd     = f"{SIGNAL}"   if is_active else LINE
                nm_col = SIGNAL        if is_active else SUBTLE
                hr_col = TEXT          if is_active else FAINT
                parts.append(
                    f"<div style='flex:1;text-align:center;padding:10px 4px;"
                    f"background:{bg};border:1px solid {bd};border-radius:10px;"
                    f"transition:border-color .15s ease,background .15s ease'>"
                    f"<div style='font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;"
                    f"color:{nm_col};font-weight:700'>{DAYS_SHORT[i]}</div>"
                    f"<div style='font-family:Inter,sans-serif;font-size:.8rem;"
                    f"color:{hr_col};margin-top:3px;font-weight:500'>{wk_hours[i]:.1f}h</div>"
                    f"</div>"
                )
            st.markdown(f"<div style='display:flex;gap:6px;margin:14px 0 8px'>"
                        f"{''.join(parts)}</div>", unsafe_allow_html=True)

            # radio sotto la strip (stile segmented control via CSS)
            day_sel = st.radio("Giorno", DAYS_FULL, horizontal=True,
                               label_visibility='collapsed',
                               key=radio_key)
            day_idx = DAYS_FULL.index(day_sel)

            # ── intestazione tabella ──
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            H = ("font-size:.64rem;letter-spacing:.09em;text-transform:uppercase;"
                 f"color:{FAINT};font-weight:700;padding:4px 0")
            hc = st.columns([2.6, 3.4, 3.4, 1.0])
            hc[0].markdown(f"<div style='{H}'>Dipendente</div>", unsafe_allow_html=True)
            hc[1].markdown(f"<div style='{H}text-align:center'>"
                           f"<span style='color:{RESP_BLUE}'>●</span> Inizio</div>",
                           unsafe_allow_html=True)
            hc[2].markdown(f"<div style='{H}text-align:center'>"
                           f"<span style='color:{AMBER}'>●</span> Fine</div>",
                           unsafe_allow_html=True)
            hc[3].markdown(f"<div style='{H}text-align:right'>Ore</div>",
                           unsafe_allow_html=True)
            st.markdown(f"<div style='height:1px;background:{LINE};margin:2px 0 6px'></div>",
                        unsafe_allow_html=True)

            # ── righe dipendenti ──
            for e in active.EMP:
                s = state[e['id']][day_idx]
                labs = labs_all.get(e['id'], [None] * 7)
                c0, c1, c2, c3 = st.columns([2.6, 3.4, 3.4, 1.0])

                # nome + barretta ruolo
                role_col = RESP_BLUE if e['role'] == 'RESP' else SIGNAL
                c0.markdown(
                    f"<div style='padding-top:8px;font-size:.86rem;color:{TEXT};"
                    f"display:flex;align-items:center;gap:8px'>"
                    f"<span style='width:3px;height:14px;border-radius:2px;"
                    f"background:{role_col}'></span>{e['name']}</div>",
                    unsafe_allow_html=True)

                if s is None:
                    lab = 'P' if labs[day_idx] == 'P' else 'R'
                    pill_bg = f"{SIGNAL}1E" if lab == 'P' else f"{SUBTLE}1A"
                    pill_fg = SIGNAL if lab == 'P' else SUBTLE
                    pill_bd = f"{SIGNAL}55" if lab == 'P' else LINE
                    c1.markdown(
                        f"<div style='display:flex;justify-content:center;padding-top:5px'>"
                        f"<span style='display:inline-block;padding:4px 14px;border-radius:6px;"
                        f"background:{pill_bg};color:{pill_fg};border:1px solid {pill_bd};"
                        f"font-family:Inter,sans-serif;font-size:.72rem;"
                        f"font-weight:700;letter-spacing:.1em'>{lab}</span></div>",
                        unsafe_allow_html=True)
                    c2.markdown(
                        f"<div style='text-align:center;padding-top:8px;"
                        f"font-family:Inter,sans-serif;font-size:.8rem;"
                        f"color:{FAINT}'>—</div>",
                        unsafe_allow_html=True)
                    c3.markdown(
                        f"<div style='text-align:right;padding-top:8px;"
                        f"font-family:Inter,sans-serif;font-size:.8rem;"
                        f"color:{FAINT}'>0.0h</div>",
                        unsafe_allow_html=True)
                else:
                    a, b = s
                    # inizio
                    with c1:
                        bc1, bc2, bc3 = st.columns([1, 2, 1], gap="small")
                        if bc1.button("−", key=f"ms_{e['id']}_{day_idx}_{ver}",
                                      help="inizio −30 min"):
                            state[e['id']][day_idx] = _shift_start_delta(s, -1)
                            st.rerun()
                        bc2.markdown(
                            f"<div style='text-align:center;"
                            f"font-family:Inter,sans-serif;font-size:.9rem;"
                            f"padding-top:5px;color:{RESP_BLUE};font-weight:600;"
                            f"letter-spacing:.02em'>{hms(a)}</div>",
                            unsafe_allow_html=True)
                        if bc3.button("+", key=f"ps_{e['id']}_{day_idx}_{ver}",
                                      help="inizio +30 min"):
                            state[e['id']][day_idx] = _shift_start_delta(s, +1)
                            st.rerun()
                    # fine
                    with c2:
                        bc1, bc2, bc3 = st.columns([1, 2, 1], gap="small")
                        if bc1.button("−", key=f"me_{e['id']}_{day_idx}_{ver}",
                                      help="fine −30 min"):
                            state[e['id']][day_idx] = _shift_end_delta(s, -1)
                            st.rerun()
                        bc2.markdown(
                            f"<div style='text-align:center;"
                            f"font-family:Inter,sans-serif;font-size:.9rem;"
                            f"padding-top:5px;color:{AMBER};font-weight:600;"
                            f"letter-spacing:.02em'>{hms(b)}</div>",
                            unsafe_allow_html=True)
                        if bc3.button("+", key=f"pe_{e['id']}_{day_idx}_{ver}",
                                      help="fine +30 min"):
                            state[e['id']][day_idx] = _shift_end_delta(s, +1)
                            st.rerun()
                    # ore (pill)
                    dur = b - a
                    c3.markdown(
                        f"<div style='text-align:right;padding-top:5px'>"
                        f"<span style='display:inline-block;padding:3px 10px;border-radius:6px;"
                        f"background:{SURFACE_2};border:1px solid {LINE};"
                        f"font-family:Inter,sans-serif;font-size:.78rem;"
                        f"color:{TEXT}'>{dur:.1f}h</span></div>",
                        unsafe_allow_html=True)

                st.markdown(f"<div style='height:1px;background:{LINE_SOFT};margin:3px 0'></div>",
                            unsafe_allow_html=True)

            new_shifts = {eid: list(seq) for eid, seq in state.items()}
            new_label = {e['id']: labs_all.get(e['id'], [None] * 7) for e in active.EMP}
            errs = []

        else:
            # ── modalità Testo: data_editor settimanale ──
            st.caption("Scrivi l'orario come **08:00-16:00**, oppure **R** (riposo) / "
                       "**P** (permesso). Le modifiche si riflettono anche in modalità "
                       "± 30 min.")
            base_rows, names = [], []
            for e in active.EMP:
                names.append(e['name'])
                labs = labs_all.get(e['id'], [None] * 7)
                base_rows.append({ds: _shift_to_cell(state[e['id']][d], labs[d])
                                  for d, ds in enumerate(DAYS_SHORT)})
            base_df = pd.DataFrame(base_rows, index=names)
            edited = st.data_editor(
                base_df, key=f"ed_{active.idx}_{ver}_{grid_v}", width='stretch',
                height=min(760, 96 + len(active.EMP) * 35),
                column_config={ds: st.column_config.TextColumn(ds, help="HH:MM-HH:MM · R · P")
                               for ds in DAYS_SHORT})
            name2id = {e['name']: e['id'] for e in active.EMP}
            new_shifts, new_label, errs = {}, {}, []
            for nm in edited.index:
                eid = name2id[nm]; ss = [None] * 7; ll = [None] * 7
                labs = labs_all.get(eid, [None] * 7)
                for d, ds in enumerate(DAYS_SHORT):
                    kind, val = _parse_cell(edited.at[nm, ds])
                    if kind == 'S':
                        ss[d] = val
                    elif kind == 'P':
                        ll[d] = 'P'
                    elif kind == 'R':
                        ll[d] = 'R'
                    else:
                        errs.append(f"{nm} · {ds}: «{val}»")
                        ss[d] = state[eid][d]; ll[d] = labs[d]
                new_shifts[eid] = ss; new_label[eid] = ll
            for eid in new_shifts:
                state[eid] = list(new_shifts[eid])
            if errs:
                st.error("Valori non riconosciuti (uso HH:MM-HH:MM, R o P) — "
                         "mantengo il turno generato per: "
                         + " · ".join(errs[:8]) + (" …" if len(errs) > 8 else ""))

        # ── ri-validazione al volo ──
        P_e, PR_e, viol_e = revalidate(rawm, new_shifts)
        gen_n = len(getattr(active, 'viol', []) or []); now_n = len(viol_e)
        tot_h = sum((s[1] - s[0]) for e in active.EMP for s in new_shifts[e['id']] if s)
        scop = sum(1 for d in range(7) for i in range(len(rawm.SLOTS)) if P_e[d][i] < rawm.REQ[d][i])
        delta = now_n - gen_n
        delta_txt = ("+" if delta > 0 else "") + str(delta) + " vs generato"
        cards = [
            kpi(str(now_n), "Violazioni ora", delta=delta_txt, tag="V",
                kind='ok' if now_n == 0 else ('warn' if now_n <= 4 else 'alert')),
            kpi(f"{tot_h:.1f}", "Ore pianificate", unit="h", tag="H"),
            kpi(str(scop), "Slot scoperti", tag="S",
                kind='ok' if scop == 0 else ('warn' if scop <= 4 else 'alert')),
        ]
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-row" style="grid-template-columns:repeat(3,1fr)">'
                    f'{"".join(cards)}</div>', unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        if viol_e:
            LBL = {'stacco': 'Stacco < 11h', 'apertura': 'Apertura sotto minimo',
                   'chiusura': 'Chiusura sotto minimo', 'copertura': 'Slot scoperti',
                   'responsabile': 'Slot senza responsabile'}
            for cat, items in _grouped_viol(viol_e).items():
                with st.expander(f"{LBL.get(cat, cat)} — {len(items)}"):
                    st.markdown(''.join(f'<span class="viol-pill">{t}</span>' for t in items[:80]),
                                unsafe_allow_html=True)
                    if len(items) > 80:
                        st.caption(f"… e altri {len(items) - 80}")
        else:
            st.success("Nessuna violazione — stacchi, coperture, presidio responsabile, "
                       "aperture e chiusure a norma.")

        with st.expander("Ore per persona · pianificate vs contratto"):
            hr = []
            for e in active.EMP:
                planned = sum((s[1] - s[0]) for s in new_shifts[e['id']] if s)
                hr.append({'Dipendente': e['name'], 'Ruolo': e['role'],
                           'Contratto (h)': int(e['mh']),
                           'Pianificate (h)': round(planned, 2),
                           'Δ (h)': round(planned - e['mh'], 2)})
            st.dataframe(pd.DataFrame(hr), width='stretch', hide_index=True)

        col_a, col_b = st.columns(2)
        if col_a.button("↩  Ripristina turni generati", width='stretch'):
            st.session_state['_edit_ver'] = ver + 1
            st.session_state.pop(f"edit_state_{active.idx}_{ver}", None)
            st.session_state['_grid_v'] = grid_v + 1
            st.rerun()
        try:
            out_edit = os.path.join(os.path.dirname(r['xlsx_path']),
                                    f"TOOL_LIDL_{getattr(active, 'WEEK', '') or 'mod'}_MODIFICATO.xlsx")
            write_shifts_surgical(r['xlsx_path'], out_edit, active.EMP, new_shifts, day_label=new_label)
            with open(out_edit, 'rb') as f:
                col_b.download_button("⬇  Scarica Excel con le modifiche", data=f.read(),
                                      file_name=os.path.basename(out_edit),
                                      mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                      width='stretch')
        except Exception as ex:
            col_b.error(f"Scrittura non riuscita: {ex}")

    # TAB 2 ── COPERTURA
    with t2:
        st.markdown('<div class="section-title">Heatmap copertura'
                    '<span class="st-note">presenti − richiesti, per slot da 30 min</span></div>',
                    unsafe_allow_html=True)
        st.markdown(legend_html([('Scoperto', CRIMSON), ('In pari', LINE_SOFT), ('Surplus', SIGNAL)],
                                note='passa il mouse per presenti/richiesti e scarto'), unsafe_allow_html=True)
        st.plotly_chart(heatmap(m), width='stretch', config={'displayModeBar': False})
        comp_data = [(n, round(h, 1)) for n, h in getattr(m, 'comp', [])
                     if h and isinstance(h, (int, float)) and h > 0]
        if comp_data:
            st.markdown('<div class="section-title">Ore per attività<span class="st-note">'
                        'composizione del fabbisogno settimanale</span></div>', unsafe_allow_html=True)
            df_c = pd.DataFrame(comp_data, columns=['Attività', 'Ore']).sort_values('Ore')
            fig_c = go.Figure(go.Bar(x=df_c['Ore'], y=df_c['Attività'], orientation='h',
                                     marker=dict(color=df_c['Ore'], colorscale=[[0, SIGNAL_DK], [1, SIGNAL]]),
                                     text=[f"{v:.1f}h" for v in df_c['Ore']], textposition='outside',
                                     textfont=dict(color=TEXT, family='Inter'),
                                     hovertemplate='%{y}: %{x:.1f} h<extra></extra>'))
            _theme(fig_c, height=max(320, len(comp_data) * 30), legend=False)
            fig_c.update_layout(margin=dict(l=8, r=60, t=10, b=8),
                                yaxis=dict(title='', gridcolor='rgba(0,0,0,0)'),
                                xaxis=dict(title='ore / settimana', gridcolor=LINE))
            st.plotly_chart(fig_c, width='stretch', config={'displayModeBar': False})

    # TAB 3 ── GIORNATA (gantt)
    with t3:
        st.markdown('<div class="section-title">Timeline giornaliera</div>', unsafe_allow_html=True)
        day_sel = st.radio("Giorno", DAYS_FULL, horizontal=True, index=0, label_visibility='collapsed')
        day_idx = DAYS_FULL.index(day_sel)
        st.plotly_chart(gantt(m, day_idx), width='stretch', config={'displayModeBar': False})
        critical = [{'Orario': hms(t), 'Presenti': int(m.P[day_idx][i]),
                     'Richiesti': int(m.REQ[day_idx][i]),
                     'Scoperto': int(m.REQ[day_idx][i] - m.P[day_idx][i])}
                    for i, t in enumerate(m.SLOTS)
                    if i < len(m.P[day_idx]) and i < len(m.REQ[day_idx])
                    and m.P[day_idx][i] < m.REQ[day_idx][i]]
        if critical:
            st.markdown('<div class="section-title">Slot scoperti<span class="st-note">'
                        f'{len(critical)} intervalli sotto il fabbisogno</span></div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(critical), width='stretch', hide_index=True)
        else:
            st.success(f"{day_sel}: copertura completa su tutti gli slot.")

    # TAB 4 ── STRAORDINARI
    with t4:
        st.markdown('<div class="section-title">Distribuzione straordinari</div>', unsafe_allow_html=True)
        fig_ot = ot_bar(m)
        if fig_ot: st.plotly_chart(fig_ot, width='stretch', config={'displayModeBar': False})
        else: st.info("Nessuno straordinario pianificato questa settimana.")
        st.markdown('<div class="section-title">Progressivo annuo'
                    '<span class="st-note">tetto e residuo per dipendente</span></div>', unsafe_allow_html=True)
        ytd = getattr(m, 'YTD', {}); tetto = getattr(getattr(m, 'A', None), 'tetto_annuo', 250) or 250
        ytd_rows = []
        for e in m.EMP:
            prog = ytd.get(e['name'].upper(), 0.0) + e['ot']
            room = max(0.0, tetto - prog)
            stato = '🔴 TETTO' if prog >= tetto else ('🟡 ATTENZIONE' if prog >= tetto * .8 else '🟢 OK')
            ytd_rows.append({'Dipendente': e['name'], 'Contratto': f"{int(e['mh'])}h",
                             'OT questa sett': f"{e['ot']:.2f}h" if e['ot'] else '—',
                             'Prog. anno': f"{prog:.1f}h", f'Residuo {int(tetto)}h': f"{room:.1f}h",
                             'Stato': stato})
        st.dataframe(pd.DataFrame(ytd_rows), width='stretch', hide_index=True)
        sb = getattr(m, 'SEAM_BRIDGE', [])
        if sb:
            st.markdown('<div class="section-title">Micro-estensioni responsabile'
                        '<span class="st-note">ponti di presidio sulle giunture di turno</span></div>',
                        unsafe_allow_html=True)
            st.dataframe(pd.DataFrame([{'Giorno': DAYS_SHORT[d], 'Dipendente': nm, 'Minuti': mins}
                                       for d, nm, mins in sb]), width='stretch', hide_index=True)

    # TAB 5 ── CONSOLE
    with t5:
        st.markdown('<div class="section-title">Persistenza stato'
                    '<span class="st-note">straordinari · riposi · storico</span></div>',
                    unsafe_allow_html=True)
        pr, pu = r.get('pull_report'), r.get('push_report')
        st.markdown(f"**Backend:** `{cloud_storage.backend_name()}`")
        if pr:
            st.caption(f"Caricati all'avvio: {', '.join(pr['ok']) or '—'}"
                       f"  ·  nuovi (nessuno stato precedente): {', '.join(pr['skip']) or '—'}"
                       + (f"  ·  errori: {', '.join(pr['err'])}" if pr['err'] else ''))
        if pu:
            st.caption(f"Salvati a fine generazione: {', '.join(pu['ok']) or '—'}"
                       + (f"  ·  errori: {', '.join(pu['err'])}" if pu['err'] else ''))
        if cloud_storage.backend_name() == 'local':
            st.info("Backend locale: i CSV di stato restano in `/tmp/rotosmart`. Su Streamlit "
                    "Community Cloud questa cartella si svuota ai riavvii — configura `[github]` "
                    "in `st.secrets` per la persistenza (vedi cloud_storage.py).")
        st.markdown('<div class="section-title">Output motore</div>', unsafe_allow_html=True)
        st.code(r['stdout'] or '(nessun output)', language='text')
        if r['stderr'].strip():
            st.markdown('<div class="section-title">Avvisi</div>', unsafe_allow_html=True)
            st.code(r['stderr'], language='text')

    # TAB 6 ── SOSTENIBILITÀ
    with t6:
        analisi_sostenibilita(m, r['xlsx_path'])


if __name__ == '__main__':
    main()