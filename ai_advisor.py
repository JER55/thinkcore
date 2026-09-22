#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai_advisor.py — commento AI (DeepSeek) sulla rota appena generata.

Segue lo stesso pattern di cloud_storage.py: se non è configurata alcuna
chiave, la funzione è un no-op silenzioso (torna None) e il resto del
sistema funziona esattamente come prima. Nessuna dipendenza obbligatoria
oltre a 'requests' (già in requirements.txt).

Configurazione (Streamlit Cloud -> Settings -> Secrets), .streamlit/secrets.toml:

    [deepseek]
    api_key = "sk-xxxxxxxx"
    model   = "deepseek-chat"     # opzionale, default deepseek-chat

In esecuzione locale (CLI, avvia_rotosmart.sh/START.bat) non passi da
st.secrets: imposta invece la variabile d'ambiente DEEPSEEK_API_KEY.
"""
import os
import json

API_URL = "https://api.deepseek.com/chat/completions"

try:
    import streamlit as st
    _SECRETS = st.secrets if hasattr(st, 'secrets') else {}
except Exception:
    _SECRETS = {}


def _cfg():
    """Ritorna (api_key, model) oppure (None, None) se non configurato.
    Ordine di priorità: st.secrets['deepseek'] poi variabile d'ambiente."""
    try:
        sec = _SECRETS.get('deepseek') if hasattr(_SECRETS, 'get') else None
    except Exception:
        sec = None
    if sec and sec.get('api_key'):
        return sec['api_key'], sec.get('model', 'deepseek-chat')
    env_key = os.environ.get('DEEPSEEK_API_KEY')
    if env_key:
        return env_key, os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
    return None, None


def is_configured() -> bool:
    return _cfg()[0] is not None


def _build_context(week: str, req_d, sched, tot_ot, deficit_tot, viol,
                    scoperto_residuo, teste, scenari_valutati=None) -> dict:
    """Riassunto STRUTTURATO (non l'xlsx grezzo) da mandare al modello.
    Tieni questa funzione allineata a cosa produce generatore_turni_v6.py
    a fine esecuzione: req_d, sched, tot_ot, deficit_tot, viol, teste
    sono già tutte variabili disponibili in quello script."""
    return {
        "settimana": week,
        "ore_richieste_tot": round(sum(req_d), 1),
        "ore_pianificate_tot": round(sum(sched), 1),
        "straordinari_tot": round(tot_ot, 1),
        "deficit_strutturale": round(deficit_tot, 1),
        "scoperto_residuo": round(scoperto_residuo, 1),
        "teste_in_organico": teste,
        "n_violazioni": len(viol),
        "violazioni": viol[:15],  # tronca: non serve mandare centinaia di righe
        "scenari_valutati": scenari_valutati,
    }


def analizza_turni(week: str, req_d, sched, tot_ot, deficit_tot, viol,
                    scoperto_residuo, teste, scenari_valutati=None,
                    timeout: int = 25) -> str | None:
    """Chiama DeepSeek e ritorna un commento in italiano sulla rota appena
    generata (2-4 frasi, orientato all'azione). Ritorna None se la chiave
    non è configurata o in caso di errore di rete (mai bloccante:
    il file xlsx viene comunque scritto a prescindere da questa funzione)."""
    api_key, model = _cfg()
    if api_key is None:
        return None

    ctx = _build_context(week, req_d, sched, tot_ot, deficit_tot, viol,
                          scoperto_residuo, teste, scenari_valutati)

    system_prompt = (
        "Sei un analista di workforce planning per un supermercato Lidl. "
        "Ricevi un riepilogo JSON di una rota settimanale appena generata "
        "da un motore di scheduling (vincoli CCNL: stacco 11h, min 2 RESP "
        "in servizio, presidio SCO, ecc.). Scrivi un commento in italiano, "
        "3-5 frasi, concreto e operativo: se ci sono violazioni o scoperto "
        "residuo, indica la causa più probabile e un'azione (es. --auto-ot, "
        "aumentare monte ore, aggiungere organico). Se tutto è a norma, "
        "dillo in una frase e commenta il margine/costo. Niente preamboli, "
        "niente ripetizione dei numeri già visibili nel foglio Excel."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(ctx, ensure_ascii=False)},
        ],
        "temperature": 0.3,
        "max_tokens": 400,
    }

    try:
        import requests
        resp = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
        if resp.status_code != 200:
            return f"[AI advisor non disponibile: HTTP {resp.status_code}]"
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as ex:
        return f"[AI advisor non disponibile: {ex}]"
