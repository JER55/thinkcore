#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cloud_storage.py — persistenza dei CSV di stato del motore turni.

Il motore (generatore_turni_v6.py) scrive/legge 3 file nella cartella
corrente:
    straordinari_log.csv   (progressivo straordinari per il tetto annuo)
    rota_boundary.csv      (chiusura domenicale, per il riposo 11h a cavallo settimana)
    rota_history.csv       (storico settimanale pianificato vs richiesto)

In ESECUZIONE LOCALE questi file restano semplicemente sul disco (la
cartella /tmp/rotosmart viene riusata da una generazione all'altra) e
tutto funziona senza bisogno di configurare nulla: PERSISTENCE_BACKEND
resta "local" e pull()/push() non fanno nulla.

Su STREAMLIT COMMUNITY CLOUD il filesystem è effimero: ad ogni riavvio
del container quei 3 file spariscono, e con loro la continuità tra
settimane (tetto annuo straordinari, riposo di fine settimana). Per
questo, se in st.secrets è presente una sezione [github] con un token,
questo modulo:
  - PRIMA di generare i turni: scarica gli ultimi CSV da un repo GitHub
    dedicato (Contents API) e li scrive nella working dir del motore
  - DOPO la generazione: carica i CSV aggiornati sullo stesso repo

Configurazione (Streamlit Cloud → Settings → Secrets), file
.streamlit/secrets.toml (MAI da committare, vedi .gitignore):

    [github]
    token = "ghp_xxx..."          # Personal Access Token, scope: repo (o Contents:write se fine-grained)
    repo  = "tuo-utente/thinkcore-state"   # repo PRIVATO dedicato solo ai CSV di stato
    path  = "data"                          # cartella nel repo (opzionale, default "data")

Consiglio: usa un repo separato e privato solo per questi 3 file,
diverso da quello del codice sorgente — così puoi tenere il codice
pubblico su GitHub senza esporre lo storico turni/straordinari.
"""
import base64
import os

STATE_FILES = ['straordinari_log.csv', 'rota_boundary.csv', 'rota_history.csv']

try:
    import streamlit as st
    _SECRETS = st.secrets if hasattr(st, 'secrets') else {}
except Exception:
    _SECRETS = {}


def _github_cfg():
    cfg = _SECRETS.get('github') if hasattr(_SECRETS, 'get') else None
    if not cfg or not cfg.get('token') or not cfg.get('repo'):
        return None
    return dict(token=cfg['token'], repo=cfg['repo'], path=cfg.get('path', 'data').strip('/'))


def backend_name():
    return 'github' if _github_cfg() else 'local'


def _gh_request(method, url, token, **kw):
    import requests
    headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github+json'}
    return requests.request(method, url, headers=headers, timeout=15, **kw)


def pull(dest_dir: str) -> dict:
    """Scarica i CSV di stato dal repo GitHub dentro dest_dir. No-op in locale.
    Ritorna un piccolo report per la UI (Console/log)."""
    cfg = _github_cfg()
    report = {'backend': backend_name(), 'ok': [], 'skip': [], 'err': []}
    if cfg is None:
        report['skip'] = STATE_FILES[:]
        return report
    for fname in STATE_FILES:
        url = f"https://api.github.com/repos/{cfg['repo']}/contents/{cfg['path']}/{fname}"
        try:
            resp = _gh_request('GET', url, cfg['token'])
            if resp.status_code == 200:
                content = base64.b64decode(resp.json()['content'])
                with open(os.path.join(dest_dir, fname), 'wb') as f:
                    f.write(content)
                report['ok'].append(fname)
            elif resp.status_code == 404:
                report['skip'].append(fname)  # non esiste ancora: prima esecuzione
            else:
                report['err'].append(f"{fname}: HTTP {resp.status_code}")
        except Exception as ex:
            report['err'].append(f"{fname}: {ex}")
    return report


def push(src_dir: str) -> dict:
    """Carica i CSV di stato aggiornati sul repo GitHub. No-op in locale."""
    cfg = _github_cfg()
    report = {'backend': backend_name(), 'ok': [], 'skip': [], 'err': []}
    if cfg is None:
        report['skip'] = STATE_FILES[:]
        return report
    for fname in STATE_FILES:
        local_path = os.path.join(src_dir, fname)
        if not os.path.exists(local_path):
            continue
        url = f"https://api.github.com/repos/{cfg['repo']}/contents/{cfg['path']}/{fname}"
        try:
            with open(local_path, 'rb') as f:
                content_b64 = base64.b64encode(f.read()).decode('ascii')
            # serve lo sha corrente se il file esiste già (update vs create)
            sha = None
            resp_get = _gh_request('GET', url, cfg['token'])
            if resp_get.status_code == 200:
                sha = resp_get.json().get('sha')
            payload = {'message': f'ThinkCore: aggiorna {fname}', 'content': content_b64}
            if sha:
                payload['sha'] = sha
            resp_put = _gh_request('PUT', url, cfg['token'], json=payload)
            if resp_put.status_code in (200, 201):
                report['ok'].append(fname)
            else:
                report['err'].append(f"{fname}: HTTP {resp_put.status_code} {resp_put.text[:200]}")
        except Exception as ex:
            report['err'].append(f"{fname}: {ex}")
    return report
