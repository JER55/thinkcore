#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GENERATORE TURNI v5 - Store Hours Engine (versione migliorata)
================================================================
Novità v5:
- Messaggi di errore user-friendly
- File di output con timestamp
- Caricamento straordinari da CSV (--ot-csv)
- Ottimizzazione dei costi (--cost-opt)
- Foglio "Executive Summary" con KPI
- Confronto scenari (--compare N)
- Migliore gestione delle righe vuote
- Lettura di "Costo_orario" da Personale (colonna J, opzionale)
- Lettura di "Straordinario_sett" da Personale (colonna K, opzionale)

Uso:
    python generatore_turni_v5.py Modello_Ore_LIDL_v3.xlsx
    python generatore_turni_v5.py Modello_Ore_LIDL_v3.xlsx --auto-ot --cost-opt
    python generatore_turni_v5.py Modello_Ore_LIDL_v3.xlsx --ot-csv straordinari.csv
    python generatore_turni_v5.py Modello_Ore_LIDL_v3.xlsx --compare 5
"""

import sys, math, random, datetime, argparse, csv, os, warnings, re
import copy
from collections import Counter, defaultdict
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

DAYS = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']
Q = 0.25  # granularità minima: 15 minuti
SEED = 0  # offset dei generatori casuali (usato da --compare)

# ---------------------------------------------------------------- Eccezioni personalizzate
class UserError(Exception):
    """Eccezione con messaggio comprensibile per l'utente."""
    pass

# ---------------------------------------------------------------- CLI
ap = argparse.ArgumentParser(description='Generatore turni v5 con miglioramenti')
ap.add_argument('file', nargs='?', default='TOOL_LIDL.xlsx',
                help='percorso del modello Excel')
ap.add_argument('--ot', default='',
                help='straordinari manuali, es: "SIMONE=2, JIN=1.5" (ore/settimana)')
ap.add_argument('--ot-csv', default=None,
                help='file CSV con due colonne: dipendente,ore_straordinario (senza header)')
ap.add_argument('--auto-ot', action='store_true',
                help='pianifica automaticamente straordinari per coprire il deficit')
ap.add_argument('--cost-opt', action='store_true',
                help='ottimizza i costi: preferisce dipendenti con costo orario più basso per gli straordinari')
ap.add_argument('--max-ot-sett', type=float, default=8.0,
                help='tetto straordinari a persona/settimana (default 8h)')
ap.add_argument('--max-ore-giorno', type=float, default=9.0,
                help='ore massime lavorabili in un giorno (default 9)')
ap.add_argument('--tetto-annuo', type=float, default=250.0,
                help='tetto annuo straordinari a persona (default 250h)')
ap.add_argument('--settimana', default=None,
                help='etichetta settimana, es. 2026-W31 (default: ISO corrente)')
ap.add_argument('--no-log', action='store_true',
                help='non scrivere il registro straordinari_log.csv')
ap.add_argument('--compare', type=int, default=0,
                help='genera N scenari e scegli il migliore (minimo costo/violazioni)')
ap.add_argument('--output-dir', default='.',
                help='directory di output (default: corrente)')
ap.add_argument('--preview', action='store_true',
                help='esegue i controlli e stampa la rota SENZA scrivere alcun file')
ap.add_argument('--no-open', action='store_true',
                help='non aprire automaticamente il file generato (Windows)')
A = ap.parse_args()
FILE = A.file

# Data/ora per timestamp
NOW = datetime.datetime.now().strftime('%Y%m%d_%H%M')

_iso = datetime.date.today().isocalendar()
WEEK = A.settimana or f'{_iso[0]}-W{_iso[1]:02d}'
YEAR = WEEK.split('-')[0]
LOGFILE = 'straordinari_log.csv'

# ---------------------------------------------------------------- letture
def hours(v):
    if isinstance(v, datetime.time):
        return v.hour + v.minute / 60 + v.second / 3600
    if isinstance(v, (int, float)):
        return float(v) * 24 if v <= 1 else float(v)
    raise UserError(f"Valore orario non valido: {v!r}. Assicurati che la cella contenga un orario valido.")

def need(v, dove, suggerimento=''):
    if v is None:
        msg = f"Cella vuota o non calcolata: {dove}. "
        msg += suggerimento or "Apri il modello in Excel, salvalo e riprova."
        raise UserError(msg)
    return v

def q4(x):
    return round(x * 4) / 4.0

def hm(x):
    return f'{int(x):02d}:{int(round((x % 1) * 60)):02d}'

def parse_fixed_shift(v, who, giorno_label):
    """Interpreta 'HH:MM-HH:MM' in un cella giorno di Personale come turno fisso."""
    txt = str(v).strip()
    m = re.match(r'^(\d{1,2})[:.](\d{2})\s*-\s*(\d{1,2})[:.](\d{2})$', txt)
    if not m:
        raise UserError(
            f"{who}, {giorno_label}: valore '{txt}' non riconosciuto. "
            f"Usa 'R' (riposo), 'P' (permesso) oppure un orario fisso 'HH:MM-HH:MM' (es. 08:00-16:00).")
    h1, m1, h2, m2 = (int(x) for x in m.groups())
    a, b = h1 + m1/60, h2 + m2/60
    if not (0 <= a < 24 and 0 < b <= 24) or b <= a:
        raise UserError(f"{who}, {giorno_label}: orario fisso '{txt}' non valido (uscita deve essere dopo entrata).")
    return q4(a), q4(b)

print(f'📂 Leggo {FILE} ...')
try:
    wb = openpyxl.load_workbook(FILE, data_only=True)
except Exception as e:
    raise UserError(f"Impossibile aprire il file {FILE}. Verifica che esista e non sia aperto in Excel. Errore: {e}")

for sh in ('Personale', 'Parametri', 'OreRichieste', 'Casse'):
    if sh not in wb.sheetnames:
        raise UserError(f'Foglio "{sh}" non trovato nel modello. Usa il modello originale o aggiungi il foglio mancante.')
p, cas, orich, pers = wb['Parametri'], wb['Casse'], wb['OreRichieste'], wb['Personale']

ENTRY = [hours(need(p.cell(row=68, column=2+d).value,
                   f'Parametri riga 68 colonna {get_column_letter(2+d)}',
                   'Inserisci un orario di ingresso per ogni giorno (riga 68).'))
         for d in range(7)]
CLOSE    = [hours(need(p.cell(row=69, column=2+d).value,
                   f'Parametri riga 69 colonna {get_column_letter(2+d)}',
                   'Inserisci un orario di uscita per ogni giorno (riga 69).'))
            for d in range(7)]
STACCO   = float(need(p['B70'].value, 'Parametri B70', 'Inserisci le ore di stacco minimo (B70).'))
MIN_PRES = int(need(p['B71'].value, 'Parametri B71', 'Inserisci il minimo di persone contemporanee (B71).'))
MIN_AP   = int(need(p['B72'].value, 'Parametri B72', 'Inserisci il minimo di persone all\'apertura (B72).'))
MIN_CH   = int(need(p['B73'].value, 'Parametri B73', 'Inserisci il minimo di persone alla chiusura (B73).'))
PRES_SCO = int(need(p['B17'].value, 'Parametri B17', 'Inserisci il presidio SCO (B17).'))

casse = [[need(cas.cell(row=6+f, column=2+d).value,
               f'Casse riga {6+f} colonna {get_column_letter(2+d)}',
               'Verifica che la tabella casse sia calcolata.') for d in range(7)]
        for f in range(13)]
barr  = [need(cas.cell(row=19, column=2+d).value, f'Casse riga 19 colonna {get_column_letter(2+d)}') for d in range(7)]
sco   = [need(cas.cell(row=25, column=2+d).value, f'Casse riga 25 colonna {get_column_letter(2+d)}') for d in range(7)]
req_d = [need(orich.cell(row=17, column=2+d).value, f'OreRichieste riga 17 colonna {get_column_letter(2+d)}') for d in range(7)]
ops_d = [req_d[d] - barr[d] - sco[d] for d in range(7)]
comp  = [(orich.cell(row=r, column=1).value, orich.cell(row=r, column=9).value)
         for r in range(4, 17)]

# Funzione per rilevare la fine della tabella personale
def _fine_tabella(v):
    return v is not None and str(v).strip().upper().startswith('TOTALE')

EMP, r = [], 5
ASSENTI = []
# Leggiamo ora:
# - Colonna H (8) = Assenza
# - Colonna J (10) = Costo_orario (nuova)
# - Colonna K (11) = Straordinario_sett (nuova)
while r <= 200:
    raw = pers.cell(row=r, column=1).value
    if raw is None or not str(raw).strip() or _fine_tabella(raw):
        break
    name = str(raw).strip()
    role = str(pers.cell(row=r, column=2).value or 'ADDETTO').strip().upper()
    role = 'RESP' if role.startswith('RESP') else 'ADDETTO'
    mh   = float(need(pers.cell(row=r, column=3).value, f'Personale C{r}', 'Inserisci il monte ore settimanale (colonna C).'))
    days = int(need(pers.cell(row=r, column=4).value, f'Personale D{r}', 'Inserisci il numero di giorni lavorativi (colonna D).'))
    if abs(mh * 4 - round(mh * 4)) > 1e-6:
        raise UserError(f"{name}: monte ore {mh} non multiplo di 15 minuti. Usa multipli di 0.25.")
    if days < 1 or days > 7:
        raise UserError(f"{name}: giorni lavorativi {days} non validi (1-7).")
    # Colonna H: Assenza
    ass = pers.cell(row=r, column=8).value
    ass = str(ass).strip().upper() if ass else ''
    if ass in ('F', 'M', 'FERIE', 'MALATTIA'):
        ASSENTI.append((name, 'ferie' if ass.startswith('F') else 'malattia', mh))
        r += 1
        continue
    # Colonna J (opzionale): costo orario
    costo = pers.cell(row=r, column=10).value
    costo = float(costo) if isinstance(costo, (int, float)) and costo > 0 else None
    # Colonna K (opzionale): straordinario settimanale
    otg = pers.cell(row=r, column=11).value
    otg = float(otg) if isinstance(otg, (int, float)) and otg > 0 else 0.0

    # Colonne L..R (12..18): vincoli giornalieri Lun..Dom
    #   vuoto            -> nessun vincolo, il motore sceglie liberamente
    #   'R'               -> riposo obbligato quel giorno
    #   'P'               -> permesso quel giorno (usa le ore di colonna S)
    #   'HH:MM-HH:MM'     -> turno fisso quel giorno (orario esatto, non calcolato)
    # Colonna S (19): ore di permesso/giorno da contratto (usata solo con 'P')
    forced_r = set()
    forced_p = set()
    fixed_shift = {}
    ore_p_giorno = pers.cell(row=r, column=19).value
    ore_p_giorno = float(ore_p_giorno) if isinstance(ore_p_giorno, (int, float)) and ore_p_giorno > 0 else 0.0
    for d in range(7):
        v = pers.cell(row=r, column=12 + d).value
        if v is None or (isinstance(v, str) and not v.strip()):
            continue
        vs = str(v).strip().upper()
        if vs == 'R':
            forced_r.add(d)
        elif vs == 'P':
            if ore_p_giorno <= 0:
                raise UserError(f"{name}: '{DAYS[d]}'=P ma la colonna S (ore permesso/giorno) "
                                f"e' vuota o zero. Indica le ore di permesso contrattuali in colonna S.")
            forced_p.add(d)
        else:
            fixed_shift[d] = parse_fixed_shift(v, name, DAYS[d])

    n_r, n_p, n_fix = len(forced_r), len(forced_p), len(fixed_shift)
    if n_r + n_p + n_fix > 7:
        raise UserError(f"{name}: troppi vincoli giornalieri ({n_r} riposo + {n_p} permesso + "
                        f"{n_fix} orario fisso = {n_r+n_p+n_fix} giorni su 7 disponibili).")
    if n_r > 7 - days:
        raise UserError(f"{name}: {n_r} giorni marcati 'R' superano i riposi previsti dal contratto "
                        f"(colonna D={days} giorni lavorativi -> {7-days} riposi attesi). "
                        f"Aumenta i giorni di riposo standard o riduci le 'R' fisse.")
    ore_fix = sum(b - a for a, b in fixed_shift.values())
    days_eff = days - n_p
    mh_eff_in = mh - n_p * ore_p_giorno - ore_fix
    if days_eff < n_fix:
        raise UserError(f"{name}: i giorni lavorativi effettivi ({days_eff}, dopo {n_p} permessi) "
                        f"sono inferiori ai {n_fix} giorni con orario fisso assegnati.")
    if mh_eff_in < -1e-6:
        raise UserError(f"{name}: le ore di permesso ({n_p*ore_p_giorno:g}h) e turni fissi ({ore_fix:g}h) "
                        f"superano il monte ore contrattuale ({mh:g}h).")
    mh_eff_in = max(0.0, mh_eff_in)

    EMP.append(dict(id=len(EMP), name=name, role=role,
                    mh=mh_eff_in, days=days_eff, ot=otg, costo=costo,
                    mh_contratto=mh, days_contratto=days,
                    forced_r=forced_r, forced_p=forced_p,
                    fixed_shift=fixed_shift, ore_fix=ore_fix,
                    ore_p_giorno=ore_p_giorno))
    r += 1

# Controllo righe vuote intermedie
gap = r
while gap <= 200:
    v = pers.cell(row=gap, column=1).value
    if _fine_tabella(v):
        break
    if v is not None and str(v).strip():
        raise UserError(f'Personale: la riga {r} è vuota ma la riga {gap} contiene "{str(v).strip()}". '
                        f'Non lasciare righe vuote in mezzo: compatta l\'elenco verso l\'alto.')
    gap += 1

if not EMP:
    raise UserError('Nessun dipendente trovato in Personale (righe 5-26). Verifica che i nomi siano presenti.')
if len(EMP) > 22:
    raise UserError(f'Trovati {len(EMP)} dipendenti, ma il blocco turni del modello (B3:V24) accetta 22 slot. '
                    f'Riduci l\'organico a 22 oppure amplia il blocco B3:V24 nel foglio Turni.')
dups = [n for n, c in Counter(e['name'].upper() for e in EMP).items() if c > 1]
if dups:
    raise UserError(f'Nomi duplicati in Personale: {", ".join(dups)}. Rendi i nomi univoci (es. ROSSI M. / ROSSI L.).')

# ---------------------------------------------------------------- Caricamento OT da CSV
if A.ot_csv:
    try:
        with open(A.ot_csv, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 2:
                    continue
                nome, ore = row[0].strip().upper(), float(row[1])
                for e in EMP:
                    if e['name'].upper() == nome:
                        e['ot'] = ore
                        break
    except Exception as e:
        raise UserError(f"Errore nella lettura del file CSV {A.ot_csv}: {e}")

# ---------------------------------------------------------------- check organico
resp_n  = sum(1 for e in EMP if e['role'] == 'RESP')
resp_gg = sum(e['days'] for e in EMP if e['role'] == 'RESP')
mh_tot  = sum(e['mh'] for e in EMP)
marg    = mh_tot - sum(req_d)

print('\n=== CHECK ORGANICO ===')
if ASSENTI:
    tot_ass = sum(a[2] for a in ASSENTI)
    print(f'  ASSENTI questa settimana ({len(ASSENTI)}): ' + ', '.join(f'{n} ({t})' for n, t, _ in ASSENTI))
    print(f'  Ore escluse per assenze: {tot_ass:g} h. Turni generati SOLO sui {len(EMP)} presenti.')

print(f'  Teste: {len(EMP)} (max 22)   Responsabili: {resp_n} (min 2)   RESP-giorni/sett: {resp_gg} (min 14, consigliato >=16)')
print(f'  Monte ore: {mh_tot:g} h   Richieste: {sum(req_d):.1f} h   Margine: {marg:+.1f} h ({marg/sum(req_d)*100:+.1f}%)')

vincoli_fissi = [e for e in EMP if e['forced_r'] or e['forced_p'] or e['fixed_shift']]
if vincoli_fissi:
    print(f'  Vincoli giornalieri fissi attivi su {len(vincoli_fissi)} dipendenti:')
    for e in vincoli_fissi:
        parti = []
        if e['forced_r']: parti.append('R:' + ','.join(DAYS[d] for d in sorted(e['forced_r'])))
        if e['forced_p']: parti.append('P:' + ','.join(DAYS[d] for d in sorted(e['forced_p'])))
        if e['fixed_shift']:
            parti.append('Fisso:' + ','.join(f"{DAYS[d]} {hm(a)}-{hm(b)}"
                        for d, (a, b) in sorted(e['fixed_shift'].items())))
        print(f"    {e['name']}: " + '  '.join(parti))

if resp_gg < 14:
    raise UserError(f'RESP-giorni insufficienti: {resp_gg} su un minimo di 14 (2 responsabili in servizio ogni giorno). '
                    f'Aggiungi un responsabile, aumenta i giorni dei responsabili o promuovi un addetto a RESP.')
if resp_gg < 16:
    print('  AVVISO: con meno di 16 RESP-giorni la rotazione aperture/chiusure è rigida.')
if marg < 0:
    print(f'  AVVISO: organico insufficiente di {-marg:.1f} h. Tampona con --auto-ot; se il deficit è ricorrente, assumi.')
elif marg < 0.04 * sum(req_d):
    print('  AVVISO: margine sotto il cuscinetto consigliato del 4-8%.')
elif marg > 0.15 * sum(req_d):
    print('  NOTA: margine oltre il 15%: organico abbondante.')

# ---------------------------------------------------------------- straordinari: input e limiti
def cap_ot(e):
    """Tetto settimanale OT a persona: min(--max-ot-sett, 25% del monte, 48h totali)."""
    return max(0.0, min(A.max_ot_sett, q4(0.25 * e['mh']), 48.0 - e['mh']))

# Gestione manuale --ot
if A.ot.strip():
    byname = {e['name'].upper(): e for e in EMP}
    for tok in A.ot.split(','):
        tok = tok.strip()
        if not tok:
            continue
        if '=' not in tok:
            raise UserError(f'--ot: formato non valido "{tok}" (usa NOME=ore).')
        nm, hh = tok.split('=', 1)
        nm = nm.strip().upper()
        hit = byname.get(nm) or next((e for k, e in byname.items() if k.startswith(nm)), None)
        if hit is None:
            raise UserError(f'--ot: dipendente "{nm}" non trovato in Personale.')
        hit['ot'] = float(hh)

OT_WARN = []
for e in EMP:
    if e['ot'] <= 0:
        e['ot'] = 0.0
        continue
    if abs(e['ot'] * 4 - round(e['ot'] * 4)) > 1e-6:
        OT_WARN.append(f"{e['name']}: straordinario {e['ot']:g}h arrotondato ai 15 minuti.")
        e['ot'] = q4(e['ot'])
    c = cap_ot(e)
    if e['ot'] > c + 1e-9:
        OT_WARN.append(f"{e['name']}: straordinario richiesto {e['ot']:g}h oltre il limite {c:g}h -> ridotto a {c:g}h.")
        e['ot'] = c

# registro cumulato (tetto annuo)
def read_log():
    ytd = Counter()
    rows = []
    if os.path.exists(LOGFILE):
        with open(LOGFILE, newline='', encoding='utf-8') as f:
            for row in csv.reader(f, delimiter=';'):
                if len(row) < 3 or row[0] == 'settimana':
                    continue
                rows.append(row)
                if row[0].startswith(YEAR) and row[0] != WEEK:
                    try:
                        ytd[row[1].upper()] += float(row[2])
                    except ValueError:
                        pass
    return ytd, rows

YTD, LOGROWS = read_log()
# --- riposo tra settimane consecutive: chiusure domenicali della settimana precedente ---
BOUNDARY_FILE = 'rota_boundary.csv'
PREV_SUN_CLOSE = {}
if os.path.exists(BOUNDARY_FILE):
    try:
        with open(BOUNDARY_FILE, newline='', encoding='utf-8') as _f:
            for _row in csv.reader(_f, delimiter=';'):
                if len(_row) < 2 or _row[0].strip().lower() == 'dipendente':
                    continue
                try:
                    PREV_SUN_CLOSE[_row[0].strip().upper()] = float(_row[1])
                except ValueError:
                    pass
    except Exception:
        PREV_SUN_CLOSE = {}
if PREV_SUN_CLOSE:
    print(f'  Riposo inter-settimana attivo: {len(PREV_SUN_CLOSE)} chiusure domenicali precedenti considerate per il lunedì.')
for e in EMP:
    room_y = A.tetto_annuo - YTD[e['name'].upper()]
    if e['ot'] > room_y + 1e-9:
        capped = max(0.0, q4(room_y))
        OT_WARN.append(f"{e['name']}: tetto annuo {A.tetto_annuo:g}h quasi raggiunto (progressivo {YTD[e['name'].upper()]:g}h) -> straordinario ridotto a {capped:g}h.")
        e['ot'] = capped

for e in EMP:
    e['mh_eff'] = e['mh'] + e['ot']
    e['h'] = e['mh_eff'] / e['days'] if e['days'] > 0 else 0

resp_all = [e for e in EMP if e['role'] == 'RESP']
if len(resp_all) < 2:
    raise UserError('Servono almeno 2 responsabili in organico per ruotare aperture e chiusure.')

# ---------------------------------------------------------------- fabbisogno per slot
SLOTS = [5.5 + 0.25 * i for i in range(63)]  # 05:30 .. 21:00
def wgt(t):
    if t < 8:  return 2.2
    if t < 10: return 1.7
    if t < 12: return 1.05
    if t < 15: return 0.95
    if t < 18: return 1.05
    if t < 20: return 0.95
    if t < 21: return 0.7
    return 1.4

REQ = []
for d in range(7):
    W = sum(wgt(t) for t in SLOTS if t >= ENTRY[d])
    row = []
    for t in SLOTS:
        if t < ENTRY[d]:
            row.append(0); continue
        fe  = (casse[int(t) - 8][d] + PRES_SCO) if 8 <= t < 21 else 0
        ops = math.floor(ops_d[d] * wgt(t) / W / 0.25)
        row.append(max(MIN_PRES, fe + ops))
    REQ.append(row)

# ---------------------------------------------------------------- riposi
cap     = sum(e['h'] for e in EMP)
surplus = [cap - req_d[d] for d in range(7)]
peak    = max(range(7), key=lambda d: req_d[d])
rest    = {e['id']: set() for e in EMP}
# Semina i riposi/permessi FISSI (colonne L..R di Personale) prima del
# bilanciamento automatico: questi giorni sono bloccati e non negoziabili.
for e in EMP:
    rest[e['id']] |= e['forced_r'] | e['forced_p']
avail_r = [len(resp_all)] * 7
removed = [0.0] * 7
# I riposi/permessi FISSI dei RESP vanno scalati SUBITO dalla capacità
# disponibile, prima che l'auto-pick scelga altri giorni di riposo,
# altrimenti rischia di scendere sotto la soglia minima senza saperlo.
for e in resp_all:
    for d in (e['forced_r'] | e['forced_p']):
        avail_r[d] -= 1; removed[d] += e['h']
if any(a < 2 for a in avail_r):
    giorni_critici = [DAYS[d] for d, a in enumerate(avail_r) if a < 2]
    raise UserError('Riposi/permessi fissi dei responsabili scendono sotto la soglia minima di 2 '
                    f'presenti in servizio nei giorni: {", ".join(giorni_critici)}. '
                    'Rivedi i vincoli fissi (colonne L..R) o aggiungi un responsabile.')
for e in resp_all:                                    # RESP: mai sotto 2 in servizio
    need_more = (7 - e['days']) - len(rest[e['id']])
    for _ in range(max(0, need_more)):
        cands = [d for d in range(7) if d not in rest[e['id']]
                and d not in e['fixed_shift'] and avail_r[d] - 1 >= 2]
        cands = [d for d in cands if d != peak] or cands
        if not cands:
            raise UserError('Riposi responsabili impossibili: servono più giorni RESP (aggiungi un responsabile o aumenta i suoi giorni).')
        d = max(cands, key=lambda x: surplus[x] - removed[x])
        rest[e['id']].add(d); avail_r[d] -= 1; removed[d] += e['h']
for e in sorted((x for x in EMP if x['role'] != 'RESP'), key=lambda x: -x['h']):
    need_more = (7 - e['days']) - len(rest[e['id']])
    for _ in range(max(0, need_more)):
        best = None
        for d in range(7):
            if d in rest[e['id']] or d in e['fixed_shift']: continue
            room  = surplus[d] - removed[d] - e['h']
            score = (surplus[d] - removed[d]) + (0 if room >= 2.5 else -50) + (-3 if d == peak else 0)
            if best is None or score > best[0]: best = (score, d)
        rest[e['id']].add(best[1]); removed[best[1]] += e['h']
working = [[e['id'] for e in EMP if d not in rest[e['id']]] for d in range(7)]
IS_RESP = {e['id']: e['role'] == 'RESP' for e in EMP}

# ---------------------------------------------------------------- durate giornaliere
def split_hours(tot, nd, who):
    for g in (1.0, 0.5, 0.25):
        u = tot / g
        if abs(u - round(u)) < 1e-6:
            u = int(round(u))
            return (u // nd) * g, u - (u // nd) * nd, g
    raise UserError(f'{who}: monte ore {tot:g} non multiplo di 15 minuti. Usa multipli di 0.25.')

DUR    = {e['id']: [0.0] * 7 for e in EMP}
OT_DAY = {e['id']: [0.0] * 7 for e in EMP}
plan   = [0.0] * 7

extras = []
for e in EMP:
    # I giorni con orario fisso hanno ore già decise: le mettiamo subito in
    # DUR e le escludiamo dalla ripartizione automatica del monte ore.
    for d, (a, b) in e['fixed_shift'].items():
        DUR[e['id']][d] = b - a
        plan[d] += (b - a)
    nd_free = e['days'] - len(e['fixed_shift'])
    if nd_free > 0:
        base, k, g = split_hours(e['mh'], nd_free, e['name'])
        if base <= 0:
            raise UserError(f"{e['name']}: monte ore residuo {e['mh']:g} troppo basso per "
                            f"{nd_free} giorni lavorativi liberi (esclusi gli orari fissi).")
        for d in range(7):
            if d not in rest[e['id']] and d not in e['fixed_shift']:
                DUR[e['id']][d] = base
                plan[d] += base
        if k:
            extras.append((e['id'], g, k))
    elif e['mh'] > 1e-6:
        raise UserError(f"{e['name']}: restano {e['mh']:g}h da distribuire ma nessun giorno libero "
                        f"(tutti i giorni lavorativi hanno un orario fisso). Verifica i vincoli in Personale.")

def place_chunk(eid, g, is_ot, exclude=()):
    cands = [d for d in range(7)
             if d not in rest[eid] and d not in exclude
             and d not in EMP[eid]['fixed_shift']
             and DUR[eid][d] + g <= A.max_ore_giorno + 1e-9]
    if not cands:
        return None
    # Se cost-opt, preferiamo non usare ancora OT se non necessario?
    # Qui scegliamo il giorno con maggior deficit
    d = max(cands, key=lambda x: (req_d[x] - plan[x], req_d[x]))
    DUR[eid][d] += g
    plan[d] += g
    if is_ot:
        OT_DAY[eid][d] += g
    return d

for eid, g, k in sorted(extras, key=lambda x: (-x[1], -x[2])):
    used = set()
    for _ in range(k):
        d = place_chunk(eid, g, False, exclude=used)
        if d is None:
            raise UserError(f"{EMP[eid]['name']}: impossibile collocare il monte ore con max {A.max_ore_giorno:g} h/giorno. Aumenta --max-ore-giorno o i giorni lavorativi.")
        used.add(d)

# straordinari manuali
for e in EMP:
    if e['ot'] <= 0:
        continue
    _, _, g = split_hours(e['ot'], 1, e['name'])
    n = int(round(e['ot'] / g))
    placed = 0.0
    for _ in range(n):
        if place_chunk(e['id'], g, True) is None:
            break
        placed += g
    if placed + 1e-9 < e['ot']:
        OT_WARN.append(f"{e['name']}: collocate solo {placed:g}h di straordinario su {e['ot']:g}h (limite {A.max_ore_giorno:g} h/giorno).")
        e['ot'] = placed
        e['mh_eff'] = e['mh'] + e['ot']

# straordinari automatici a copertura del deficit
AUTO_OT_ADDED = 0.0
if A.auto_ot:
    STEP = 0.5
    guard = 0
    while guard < 4000:
        guard += 1
        deficit = [(req_d[d] - plan[d], d) for d in range(7)]
        deficit.sort(reverse=True)
        moved = False
        for gap, d in deficit:
            if gap < STEP:
                break
            elig = [e for e in EMP
                    if d not in rest[e['id']]
                    and DUR[e['id']][d] + STEP <= A.max_ore_giorno + 1e-9
                    and e['ot'] + STEP <= cap_ot(e) + 1e-9
                    and YTD[e['name'].upper()] + e['ot'] + STEP <= A.tetto_annuo + 1e-9]
            if not elig:
                continue
            # Chi caricare di straordinario:
            #  - default: bilancia sul meno carico (OT settimana, poi progressivo annuo)
            #  - --cost-opt: preferisci il costo orario più basso, SE disponibile
            def _ot_key(x):
                c = x.get('costo')
                if A.cost_opt and c is not None:
                    return (c, x['ot'], YTD[x['name'].upper()], x['id'])
                return (x['ot'], YTD[x['name'].upper()], x['mh'], x['id'])
            pick = min(elig, key=_ot_key)
            DUR[pick['id']][d] += STEP
            OT_DAY[pick['id']][d] += STEP
            plan[d] += STEP
            pick['ot'] += STEP
            pick['mh_eff'] += STEP
            AUTO_OT_ADDED += STEP
            moved = True
            break
        if not moved:
            break
    for e in EMP:
        e['h'] = e['mh_eff'] / e['days']

# ---------------------------------------------------------------- ancore responsabili
def pick_anchors():
    def _ok_open(i, d):
        fx = EMP[i]['fixed_shift'].get(d)
        return fx is None or abs(fx[0] - ENTRY[d]) < 1e-9
    def _ok_close(i, d):
        fx = EMP[i]['fixed_shift'].get(d)
        return fx is None or abs(fx[1] - CLOSE[d]) < 1e-9
    wr_open  = [[i for i in working[d] if IS_RESP[i] and _ok_open(i, d)]  for d in range(7)]
    wr_close = [[i for i in working[d] if IS_RESP[i] and _ok_close(i, d)] for d in range(7)]
    rnd = random.Random(7 + SEED)
    pairs = []
    for d in range(7):
        pr = [(a, b) for a in wr_open[d] for b in wr_close[d] if a != b]
        if d == 0 and PREV_SUN_CLOSE:
            def _mon_ok(a):
                pc = PREV_SUN_CLOSE.get(EMP[a]['name'].upper())
                return pc is None or ENTRY[0] + 24 - pc >= STACCO - 1e-9
            pr = [(a, b) for (a, b) in pr if _mon_ok(a)]
        rnd.shuffle(pr)
        pairs.append(pr)
    sol = [None] * 7
    def bt(d):
        if d == 7:
            return sol[6][1] != sol[0][0]
        for pr in pairs[d]:
            if d > 0 and sol[d - 1][1] == pr[0]:
                continue
            sol[d] = pr
            if bt(d + 1):
                return True
        sol[d] = None
        return False
    if not bt(0):
        raise UserError('Impossibile ruotare aperture/chiusure dei responsabili: servono almeno 2 responsabili in servizio ogni giorno.')
    return sol

ANCH = pick_anchors()

# ---------------------------------------------------------------- assegnazione turni
def templates(eid, d):
    h, e = DUR[eid][d], ENTRY[d]
    out = [('OPEN', e, e + h)]
    for k in range(16, 33):
        s = k / 2.0
        if s + h <= 21.0: out.append((f'MID{s}', s, s + h))
    out.append(('CLOSE', CLOSE[d] - h, CLOSE[d]))
    nxt = (d + 1) % 7
    if ANCH[nxt][0] == eid:
        lim = ENTRY[nxt] + (24 - STACCO)
        out = [t for t in out if t[2] <= lim + 1e-9]
    prv = (d - 1) % 7
    if ANCH[prv][1] == eid:
        lim2 = CLOSE[prv] - 24 + STACCO
        out = [t for t in out if t[1] >= lim2 - 1e-9]
    return out

RW   = 8.0
W_AC = 12.0

def build():
    shifts = {e['id']: [None] * 7 for e in EMP}
    P  = [[0] * 63 for _ in range(7)]
    PR = [[0] * 63 for _ in range(7)]
    OPc = [0] * 7
    CLc = [0] * 7
    def cover(d, a, b, k, eid):
        rp = IS_RESP[eid]
        if abs(a - ENTRY[d]) < 1e-9: OPc[d] += k
        if abs(b - CLOSE[d]) < 1e-9:    CLc[d] += k
        i0 = max(0, int(math.ceil((a - 5.5) * 4 - 1e-9)))
        i1 = min(63, int(math.ceil((b - 5.5) * 4 - 1e-9)))
        Pd = P[d]
        if rp:
            PRd = PR[d]
            for i in range(i0, i1):
                Pd[i] += k; PRd[i] += k
        else:
            for i in range(i0, i1):
                Pd[i] += k
    def ok_rest(eid, d, start, end=None):
        end = end if end is not None else start + DUR[eid][d]
        pv, nx = shifts[eid][(d - 1) % 7], shifts[eid][(d + 1) % 7]
        if pv and start + 24 - pv[1] < STACCO - 1e-9: return False
        if nx and nx[0] + 24 - end < STACCO - 1e-9:   return False
        if d == 0:
            pc = PREV_SUN_CLOSE.get(EMP[eid]['name'].upper())
            if pc is not None and start + 24 - pc < STACCO - 1e-9:
                return False
        return True
    def gain(d, a, b, eid):
        rp = IS_RESP[eid]
        v = 0.0
        if abs(a - ENTRY[d]) < 1e-9 and OPc[d] < MIN_AP: v += W_AC
        if abs(b - CLOSE[d]) < 1e-9 and CLc[d] < MIN_CH:    v += W_AC
        for i, t in enumerate(SLOTS):
            if a <= t < b:
                v += 1.0 if P[d][i] < REQ[d][i] else -0.15
                if rp and REQ[d][i] > 0 and PR[d][i] < 1:
                    v += RW
        return v
    def du(d):
        s = W_AC * (max(0, MIN_AP - OPc[d]) + max(0, MIN_CH - CLc[d]))
        for i in range(63):
            s += max(0, REQ[d][i] - P[d][i])
            if REQ[d][i] > 0 and PR[d][i] < 1:
                s += RW
        return s

    locked = set()
    for d in range(7):
        pool = list(working[d])
        op, cl = ANCH[d]
        shifts[op][d] = (ENTRY[d], ENTRY[d] + DUR[op][d])
        cover(d, *shifts[op][d], 1, op); pool.remove(op); locked.add((op, d))
        shifts[cl][d] = (CLOSE[d] - DUR[cl][d], CLOSE[d])
        cover(d, *shifts[cl][d], 1, cl); pool.remove(cl); locked.add((cl, d))
        # Turni fissi (colonne L..R di Personale): applicati esattamente come
        # richiesto, non ricalcolati. Chi è già ancora apertura/chiusura è
        # stato gestito sopra (e pick_anchors garantisce l'allineamento).
        for eid in list(pool):
            fx = EMP[eid]['fixed_shift'].get(d)
            if fx is None:
                continue
            shifts[eid][d] = fx
            cover(d, *fx, 1, eid)
            pool.remove(eid)
            locked.add((eid, d))
        for eid in sorted(pool, key=lambda i: (not IS_RESP[i], -DUR[i][d])):
            best, bv = None, -1e18
            for name, a, b in templates(eid, d):
                if not ok_rest(eid, d, a, b): continue
                v = gain(d, a, b, eid)
                if v > bv: bv, best = v, (a, b)
            shifts[eid][d] = best; cover(d, *best, 1, eid)

    def optimize_day(d, free):
        rnd = random.Random(42 + d + 1009 * SEED)
        def improve():
            changed = True
            while changed:
                changed = False
                for eid in free:
                    a0, b0 = shifts[eid][d]
                    best = (du(d), a0, b0)
                    for name, a, b in templates(eid, d):
                        if (a, b) == (a0, b0) or not ok_rest(eid, d, a, b): continue
                        cover(d, a0, b0, -1, eid); cover(d, a, b, 1, eid)
                        u = du(d)
                        cover(d, a, b, -1, eid); cover(d, a0, b0, 1, eid)
                        if u < best[0]: best = (u, a, b)
                    if (best[1], best[2]) != (a0, b0):
                        cover(d, a0, b0, -1, eid); cover(d, best[1], best[2], 1, eid)
                        shifts[eid][d] = (best[1], best[2]); changed = True
        improve()
        best_u = du(d); best_state = {e: shifts[e][d] for e in free}
        for _ in range(120):
            if best_u == 0: break
            for eid in rnd.sample(free, min(4, len(free))):
                a0, b0 = shifts[eid][d]
                cands = [(a, b) for _, a, b in templates(eid, d) if ok_rest(eid, d, a, b)]
                if not cands: continue
                a, b = rnd.choice(cands)
                cover(d, a0, b0, -1, eid); cover(d, a, b, 1, eid); shifts[eid][d] = (a, b)
            improve()
            u = du(d)
            if u < best_u:
                best_u, best_state = u, {e: shifts[e][d] for e in free}
            else:
                for e, (a, b) in best_state.items():
                    a0, b0 = shifts[e][d]
                    if (a0, b0) != (a, b):
                        cover(d, a0, b0, -1, e); cover(d, a, b, 1, e); shifts[e][d] = (a, b)
    for d in range(7):
        optimize_day(d, [i for i in working[d] if (i, d) not in locked])

    # riparazione seam RESP
    resp_ids = [e['id'] for e in EMP if IS_RESP[e['id']]]
    SEAM_BRIDGE = []
    for d in range(7):
        for _ in range(6):
            holes = [i for i in range(63) if P[d][i] > 0 and PR[d][i] == 0]
            if not holes:
                break
            hi = holes[0]; th = SLOTS[hi]; fixed = False
            order = sorted((e for e in resp_ids if e in working[d] and d not in EMP[e]['fixed_shift']),
                           key=lambda e: min(abs(shifts[e][d][1] - th), abs(shifts[e][d][0] - th)))
            for eid in order:
                a0, b0 = shifts[eid][d]
                if b0 <= th and ANCH[d][1] != eid:
                    new_b = th + 0.25
                    if new_b - b0 <= 0.5 + 1e-9 and new_b <= CLOSE[d] + 1e-9 and ok_rest(eid, d, a0, new_b):
                        cover(d, a0, b0, -1, eid); cover(d, a0, new_b, 1, eid)
                        shifts[eid][d] = (a0, new_b); DUR[eid][d] += (new_b - b0)
                        EMP[eid]['ot'] = EMP[eid].get('ot', 0.0) + (new_b - b0)
                        EMP[eid]['mh_eff'] = EMP[eid].get('mh_eff', EMP[eid]['mh']) + (new_b - b0)
                        SEAM_BRIDGE.append((d, EMP[eid]['name'], round((new_b - b0) * 60)))
                        fixed = True; break
                if a0 > th and ANCH[d][0] != eid:
                    new_a = th
                    if a0 - new_a <= 0.5 + 1e-9 and new_a >= ENTRY[d] - 1e-9 and ok_rest(eid, d, new_a, b0):
                        cover(d, a0, b0, -1, eid); cover(d, new_a, b0, 1, eid)
                        shifts[eid][d] = (new_a, b0); DUR[eid][d] += (a0 - new_a)
                        EMP[eid]['ot'] = EMP[eid].get('ot', 0.0) + (a0 - new_a)
                        EMP[eid]['mh_eff'] = EMP[eid].get('mh_eff', EMP[eid]['mh']) + (a0 - new_a)
                        SEAM_BRIDGE.append((d, EMP[eid]['name'], round((a0 - new_a) * 60)))
                        fixed = True; break
            if not fixed:
                break
    return shifts, P, PR, SEAM_BRIDGE

# Esegui la generazione (se --compare > 1, genera più scenari e scegli il migliore)
def evaluate_scenario(shifts, P, PR, SEAM_BRIDGE):
    # Calcola costo totale (ore normali + straordinari pesati)
    costo_tot = 0.0
    violazioni = 0
    for e in EMP:
        tot = sum(DUR[e['id']][d] for d in range(7) if shifts[e['id']][d])
        # Costo: ore normali * costo_orario (se disponibile) + straordinario * 1.5 * costo_orario
        costo = e.get('costo')
        if costo is None:
            costo = 1.0  # nessun dato di costo: confronto solo relativo
        straord = e['ot']
        costo_tot += (tot - straord) * costo + straord * 1.5 * costo
        # Violazioni: stacchi, coperture, ecc. (semplificato)
        # per ora contiamo le violazioni dal console report
    # Contiamo violazioni dalle strutture P/PR
    for d in range(7):
        for i in range(63):
            if P[d][i] < REQ[d][i]:
                violazioni += 1
            if P[d][i] > 0 and PR[d][i] == 0:
                violazioni += 1
    # Aperture/chiusure
    for d in range(7):
        op = sum(1 for i in working[d] if abs(shifts[i][d][0] - ENTRY[d]) < 1e-9)
        cl = sum(1 for i in working[d] if abs(shifts[i][d][1] - CLOSE[d]) < 1e-9)
        if op < MIN_AP: violazioni += 1
        if cl < MIN_CH: violazioni += 1
    return costo_tot, violazioni

def _snapshot_state():
    return (copy.deepcopy(DUR), copy.deepcopy(OT_DAY), list(plan),
            {e['id']: (e['ot'], e.get('mh_eff', e['mh']), e.get('h', 0.0)) for e in EMP})

def _restore_state(snap):
    d0, o0, p0, emp0 = snap
    for k in DUR:    DUR[k][:]    = d0[k]
    for k in OT_DAY: OT_DAY[k][:] = o0[k]
    plan[:] = p0
    for e in EMP:
        e['ot'], e['mh_eff'], e['h'] = emp0[e['id']]

def _full_validate(shifts_loc, P_loc, PR_loc):
    """Ricalcola l'elenco violazioni testuali per uno scenario specifico.
    IMPORTANTE: va chiamata subito dopo build(), quando DUR/OT_DAY/EMP
    riflettono ancora lo stato di QUEL preciso scenario (prima di
    _restore_state per lo scenario successivo)."""
    v = []
    for e in EMP:
        tot = sum(DUR[e['id']][d] for d in range(7) if shifts_loc[e['id']][d])
        if abs(tot - e['mh_eff']) > 0.01:
            v.append(f"ore {e['name']}: {tot:g} vs monte+straord {e['mh_eff']:g}")
        seq = shifts_loc[e['id']]
        for d in range(7):
            d2 = (d + 1) % 7
            if seq[d] and seq[d2] and seq[d2][0] + 24 - seq[d][1] < STACCO - 1e-9:
                v.append(f"stacco {e['name']} {DAYS[d]}->{DAYS[d2]}: {seq[d2][0]+24-seq[d][1]:.2f}h")
        if seq[0]:
            pc = PREV_SUN_CLOSE.get(e['name'].upper())
            if pc is not None and seq[0][0] + 24 - pc < STACCO - 1e-9:
                v.append(f"stacco {e['name']} Dom(sett.prec.)->Lun: {seq[0][0]+24-pc:.2f}h")
        for d, (fa, fb) in e['fixed_shift'].items():
            s = seq[d]
            if s is None or abs(s[0] - fa) > 1e-6 or abs(s[1] - fb) > 1e-6:
                v.append(f"orario fisso non rispettato: {e['name']} {DAYS[d]} atteso "
                        f"{hm(fa)}-{hm(fb)}, ottenuto {(hm(s[0])+'-'+hm(s[1])) if s else 'riposo'}")
    for d in range(7):
        op = sum(1 for i in working[d] if abs(shifts_loc[i][d][0] - ENTRY[d]) < 1e-9)
        cl = sum(1 for i in working[d] if abs(shifts_loc[i][d][1] - CLOSE[d]) < 1e-9)
        if op < MIN_AP: v.append(f'apertura {DAYS[d]}: {op} persone')
        if cl < MIN_CH: v.append(f'chiusura {DAYS[d]}: {cl} persone')
        for i, t in enumerate(SLOTS):
            if P_loc[d][i] < REQ[d][i]:
                v.append(f'copertura {DAYS[d]} {int(t)}:{int((t%1)*60):02d}: {P_loc[d][i]}<{REQ[d][i]}')
            if P_loc[d][i] > 0 and PR_loc[d][i] == 0:
                v.append(f'nessun responsabile {DAYS[d]} {int(t)}:{int((t%1)*60):02d}')
    return v

def _scenario_extra(sh, P_, PR_, SB_):
    """Cattura tutti i dati necessari a ricostruire uno scenario nella UI
    (Streamlit), senza dover rigenerare i turni da capo."""
    sched_s = [sum(DUR[i][d] for i in working[d]) for d in range(7)]
    dlabel_s = {e['id']: ['P' if d in e['forced_p'] else ('R' if sh[e['id']][d] is None else None)
                          for d in range(7)] for e in EMP}
    return dict(
        shifts=sh, P=P_, PR=PR_, SEAM_BRIDGE=SB_,
        DUR=copy.deepcopy(DUR), OT_DAY=copy.deepcopy(OT_DAY),
        sched=sched_s, day_label=dlabel_s,
        tot_ot=sum(e['ot'] for e in EMP),
        emp_ot={e['id']: e['ot'] for e in EMP},
        emp_mh_eff={e['id']: e['mh_eff'] for e in EMP},
        viol=_full_validate(sh, P_, PR_),
    )

# SCENARI: elenco di TUTTI gli scenari valutati (non solo il migliore),
# usato da app_lidl.py per permettere all'utente di navigare tra le
# alternative generate da --compare invece di vedere solo quella scelta
# automaticamente dal motore.
SCENARI = []
BEST_SCENARIO_IDX = 0

if A.compare > 1:
    base_snap = _snapshot_state()
    best = None
    for _seed in range(A.compare):
        _restore_state(base_snap)
        SEED = _seed
        random.seed(_seed)
        sh, P_, PR_, SB_ = build()
        cost_s, viol_s = evaluate_scenario(sh, P_, PR_, SB_)
        extra = _scenario_extra(sh, P_, PR_, SB_)   # legge DUR/OT_DAY/EMP prima del restore
        won = _snapshot_state()
        SCENARI.append(dict(seed=_seed, cost=cost_s, viol_n=viol_s, snapshot=won, **extra))
        key = (viol_s, cost_s)
        if best is None or key < best[0]:
            best = (key, _seed, sh, P_, PR_, SB_, won)
    _restore_state(best[6])
    SEED = best[1]
    shifts, P, PR, SEAM_BRIDGE = best[2], best[3], best[4], best[5]
    BEST_SCENARIO_IDX = best[1]
    print(f'\n[--compare] Valutati {A.compare} scenari -> scelto seed={best[1]} '
          f'(violazioni={best[0][0]}, costo_relativo={best[0][1]:.1f}). '
          f'NB: i riposi sono fissati prima di build(), quindi la variazione è nei soli turni. '
          f'Tutti i {A.compare} scenari restano disponibili in SCENARI per il confronto.')
else:
    shifts, P, PR, SEAM_BRIDGE = build()
    extra = _scenario_extra(shifts, P, PR, SEAM_BRIDGE)
    SCENARI.append(dict(seed=0, cost=None, viol_n=len(extra['viol']),
                        snapshot=_snapshot_state(), **extra))
    BEST_SCENARIO_IDX = 0

# Etichetta per giorno (usata da write_engine.py per distinguere
# Riposo da Permesso nel foglio Turni, invece di scrivere sempre 'R')
DAY_LABEL = {}
for e in EMP:
    DAY_LABEL[e['id']] = ['P' if d in e['forced_p'] else ('R' if shifts[e['id']][d] is None else None)
                          for d in range(7)]

# Riallinea mh_eff
for e in EMP:
    tot_dur = sum(DUR[e['id']][d] for d in range(7) if shifts[e['id']][d])
    e['mh_eff'] = tot_dur

# ---------------------------------------------------------------- validazione
viol = []
for e in EMP:
    tot = sum(DUR[e['id']][d] for d in range(7) if shifts[e['id']][d])
    if abs(tot - e['mh_eff']) > 0.01:
        viol.append(f"ore {e['name']}: {tot:g} vs monte+straord {e['mh_eff']:g}")
    seq = shifts[e['id']]
    for d in range(7):
        d2 = (d + 1) % 7
        if seq[d] and seq[d2] and seq[d2][0] + 24 - seq[d][1] < STACCO - 1e-9:
            viol.append(f"stacco {e['name']} {DAYS[d]}->{DAYS[d2]}: {seq[d2][0]+24-seq[d][1]:.2f}h")
    # Riposo tra la chiusura di domenica scorsa e l'apertura di lunedì:
    # copre anche i turni fissi, che il controllo sopra (solo entro la
    # settimana corrente) non intercetta per il giorno 0.
    if seq[0]:
        pc = PREV_SUN_CLOSE.get(e['name'].upper())
        if pc is not None and seq[0][0] + 24 - pc < STACCO - 1e-9:
            viol.append(f"stacco {e['name']} Dom(sett.prec.)->Lun: {seq[0][0]+24-pc:.2f}h")
    # Autocontrollo: ogni turno fisso richiesto deve comparire esattamente
    # com'è stato specificato in Personale (nessuna riscrittura silenziosa).
    for d, (fa, fb) in e['fixed_shift'].items():
        s = seq[d]
        if s is None or abs(s[0] - fa) > 1e-6 or abs(s[1] - fb) > 1e-6:
            viol.append(f"orario fisso non rispettato: {e['name']} {DAYS[d]} atteso "
                        f"{hm(fa)}-{hm(fb)}, ottenuto {(hm(s[0])+'-'+hm(s[1])) if s else 'riposo'}")
for d in range(7):
    op = sum(1 for i in working[d] if abs(shifts[i][d][0] - ENTRY[d]) < 1e-9)
    cl = sum(1 for i in working[d] if abs(shifts[i][d][1] - CLOSE[d]) < 1e-9)
    if op < MIN_AP: viol.append(f'apertura {DAYS[d]}: {op} persone')
    if cl < MIN_CH: viol.append(f'chiusura {DAYS[d]}: {cl} persone')
    for i, t in enumerate(SLOTS):
        if P[d][i] < REQ[d][i]:
            viol.append(f'copertura {DAYS[d]} {int(t)}:{int((t%1)*60):02d}: {P[d][i]}<{REQ[d][i]}')
        if P[d][i] > 0 and PR[d][i] == 0:
            viol.append(f'nessun responsabile {DAYS[d]} {int(t)}:{int((t%1)*60):02d}')

# ---------------------------------------------------------------- report a video
tot_ot = sum(e['ot'] for e in EMP)

if SEAM_BRIDGE:
    print('\n=== PONTI RESPONSABILE (micro-estensioni) ===')
    for d, nm, mins in SEAM_BRIDGE:
        print(f'  {DAYS[d]}: {nm} esteso di {mins} min per garantire un responsabile continuo.')
    print(f'  Totale: {sum(m for _,_,m in SEAM_BRIDGE)} min di presidio responsabile aggiunti.')

print('\n=== COMPOSIZIONE ORE RICHIESTE ===')
for nome, ore in comp:
    if ore: print(f'  {nome:<42s} {ore:6.1f} h')
print(f'  {"TOTALE":<42s} {sum(req_d):6.1f} h')

print('\n=== RIEPILOGO GIORNALIERO ===')
sched = [sum(DUR[i][d] for i in working[d]) for d in range(7)]
ot_g  = [sum(OT_DAY[e["id"]][d] for e in EMP) for d in range(7)]
print('  giorno   richieste  pianificate  di cui straord  teste  saturazione')
for d in range(7):
    print(f'  {DAYS[d]}      {req_d[d]:8.1f}   {sched[d]:9.1f}   {ot_g[d]:12.1f}   {len(working[d]):4d}   {req_d[d]/sched[d]*100:6.1f}%' if sched[d] else '')
print(f'  TOT      {sum(req_d):8.1f}   {sum(sched):9.1f}   {tot_ot:12.1f}')

deficit_tot = sum(req_d) - sum(e['mh'] for e in EMP)
print('\n=== BILANCIO CAPACITA ===')
print(f'  Ore richieste dal modello : {sum(req_d):7.1f} h')
print(f'  Monte ore contrattuale    : {sum(e["mh"] for e in EMP):7.1f} h')
print(f'  Deficit strutturale       : {deficit_tot:7.1f} h')
print(f'  Straordinari pianificati  : {tot_ot:7.1f} h' + (f'  (di cui {AUTO_OT_ADDED:g}h da --auto-ot)' if AUTO_OT_ADDED else ''))
print(f'  Scoperto residuo          : {max(0.0, deficit_tot - tot_ot):7.1f} h')

if tot_ot > 0 or YTD:
    print('\n=== STRAORDINARI (settimana ' + WEEK + ') ===')
    print('  dipendente        contratto  straord  tetto sett  prog. anno  residuo 250h  stato')
    for e in EMP:
        prog = YTD[e['name'].upper()] + e['ot']
        if prog >= A.tetto_annuo - 1e-9 and e['ot'] > 0:
            st = 'TETTO'
        elif prog >= 0.8 * A.tetto_annuo:
            st = 'ATTENZIONE'
        else:
            st = 'ok'
        if e['ot'] > 0 or YTD[e['name'].upper()] > 0:
            print(f"  {e['name']:<16s}  {e['mh']:8.1f}  {e['ot']:7.2f}  {cap_ot(e):10.2f}  {prog:10.1f}  {max(0.0, A.tetto_annuo-prog):12.1f}  {st}")
for w in OT_WARN:
    print('  AVVISO:', w)

print('\n=== ROTA ===  (* = giornata con straordinario)')
print('  ' + 'Dipendente'.ljust(26) + ''.join(x.center(13) for x in DAYS))
for e in EMP:
    row = ''
    for d in range(7):
        s = shifts[e['id']][d]
        star = '*' if OT_DAY[e['id']][d] > 0 else ''
        row += ('R' if s is None else f'{hm(s[0])}-{hm(s[1])}{star}').center(13)
    print('  ' + e['name'][:25].ljust(26) + row)
print(f'\nVIOLAZIONI: {len(viol)}')
for v in viol[:20]: print('  -', v)

# ---------------------------------------------------------------- file di output
if A.preview:
    print('\n[PREVIEW] Controlli eseguiti, nessun file scritto. Togli --preview per generare i turni.')
    sys.exit(0)

out = openpyxl.Workbook()
BLU, DARK, ICE, ORA, RED = '0050AA', '062B61', 'F3F7FD', 'FFE9C9', 'FFD3D3'
ws = out.active; ws.title = 'IncollaQui'
ws.sheet_view.showGridLines = False
ws['A1'] = ('Copia SEMPRE il blocco fisso B3:V24 (22 slot) e incollalo nel modello in '
            'Turni!F5 con Incolla speciale > "Valori e formati dei numeri" + "Salta celle '
            'vuote". Gli slot non usati contengono R: cosi ripuliscono eventuali orari '
            'residui di personale rimosso. Non riordinare Personale.')
ws['A1'].font = Font(name='Inter', size=9, italic=True, color='667085')
ws.column_dimensions['A'].width = 24
for j in range(21): ws.column_dimensions[get_column_letter(2 + j)].width = 7
for d in range(7):
    c = ws.cell(row=2, column=2 + 3 * d, value=DAYS[d] + '  In/Out')
    c.font = Font(name='Inter', size=9, bold=True, color='FFFFFF')
    c.fill = PatternFill('solid', fgColor=BLU)
for i, e in enumerate(EMP):
    rr = 3 + i
    ws.cell(row=rr, column=1, value=e['name']).font = Font(name='Inter', size=9)
    for d in range(7):
        s = shifts[e['id']][d]
        ci, co = 2 + 3 * d, 3 + 3 * d
        if s is None:
            ws.cell(row=rr, column=ci, value='R')
            ws.cell(row=rr, column=co, value='R')
        else:
            ws.cell(row=rr, column=ci, value=s[0] / 24)
            ws.cell(row=rr, column=co, value=s[1] / 24)
        for cc in (ci, co):
            cell = ws.cell(row=rr, column=cc)
            cell.number_format = 'h:mm'
            cell.font = Font(name='Inter', size=9, color=BLU)
            cell.alignment = Alignment(horizontal='center')
for slot in range(len(EMP), 22):
    rr = 3 + slot
    for d in range(7):
        for cc in (2 + 3 * d, 3 + 3 * d):
            cell = ws.cell(row=rr, column=cc, value='R')
            cell.number_format = 'h:mm'
            cell.font = Font(name='Inter', size=9, color=BLU)
            cell.alignment = Alignment(horizontal='center')

# Foglio Rota
ws = out.create_sheet('Rota')
ws.sheet_view.showGridLines = False
ws['A1'] = 'WEEKLY ROTATION  ·  ' + WEEK
ws['A1'].font = Font(name='Inter', size=14, bold=True, color=DARK)
ws['A2'] = '* = giornata con ore di straordinario (dettaglio nel foglio Straordinari)'
ws['A2'].font = Font(name='Inter', size=8, italic=True, color='667085')
hdr = ['Dipendente', 'Ruolo', 'Monte', 'Straord'] + DAYS
for j, t in enumerate(hdr):
    c = ws.cell(row=3, column=1 + j, value=t)
    c.font = Font(name='Inter', size=9, bold=True, color='FFFFFF')
    c.fill = PatternFill('solid', fgColor=DARK)
    c.alignment = Alignment(horizontal='center')
ws.column_dimensions['A'].width = 24; ws.column_dimensions['B'].width = 9
ws.column_dimensions['C'].width = 7;  ws.column_dimensions['D'].width = 8
for j in range(7): ws.column_dimensions[get_column_letter(5 + j)].width = 12.5
for i, e in enumerate(EMP):
    rr = 4 + i
    fill = PatternFill('solid', fgColor=ICE) if i % 2 else None
    cells = [e['name'], e['role'], e['mh'], (e['ot'] if e['ot'] else '')]
    for d in range(7):
        s = shifts[e['id']][d]
        star = '*' if OT_DAY[e['id']][d] > 0 else ''
        cells.append('R' if s is None else f'{hm(s[0])}-{hm(s[1])}{star}')
    for j, v in enumerate(cells):
        c = ws.cell(row=rr, column=1 + j, value=v)
        c.font = Font(name='Inter', size=9)
        if fill: c.fill = fill
        if j >= 2: c.alignment = Alignment(horizontal='center')
rr = 4 + len(EMP)
ws.cell(row=rr, column=1, value='Ore pianificate').font = Font(name='Inter', size=9, bold=True)
for d in range(7):
    c = ws.cell(row=rr, column=5 + d, value=round(sched[d], 2))
    c.font = Font(name='Inter', size=9, bold=True)
    c.alignment = Alignment(horizontal='center')

# Foglio Straordinari
ws = out.create_sheet('Straordinari')
ws.sheet_view.showGridLines = False
ws['A1'] = 'STRAORDINARI  ·  settimana ' + WEEK
ws['A1'].font = Font(name='Inter', size=14, bold=True, color=DARK)
ws['A2'] = (f'Limiti applicati: max {A.max_ot_sett:g} h/sett a persona (e comunque 25% del monte ore e 48h totali), '
            f'max {A.max_ore_giorno:g} h/giorno, tetto annuo {A.tetto_annuo:g} h. Progressivo anno da {LOGFILE}.')
ws['A2'].font = Font(name='Inter', size=8, italic=True, color='667085')
hdr = ['Dipendente', 'Contratto (h)'] + DAYS + ['Straord. sett.', 'Prog. anno', 'Residuo annuo', 'Stato']
for j, t in enumerate(hdr):
    c = ws.cell(row=4, column=1 + j, value=t)
    c.font = Font(name='Inter', size=9, bold=True, color='FFFFFF')
    c.fill = PatternFill('solid', fgColor=DARK)
    c.alignment = Alignment(horizontal='center')
ws.column_dimensions['A'].width = 24
for j in range(1, len(hdr)): ws.column_dimensions[get_column_letter(1 + j)].width = 11
for i, e in enumerate(EMP):
    rr = 5 + i
    prog = YTD[e['name'].upper()] + e['ot']
    resid = max(0.0, A.tetto_annuo - prog)
    stato = ('TETTO RAGGIUNTO' if prog >= A.tetto_annuo - 1e-9 and prog > 0 else
             'ATTENZIONE' if prog >= 0.8 * A.tetto_annuo else 'OK')
    vals = ([e['name'], e['mh']] + [(OT_DAY[e['id']][d] or '') for d in range(7)]
            + [e['ot'] or 0, round(prog, 2), round(resid, 2), stato])
    rowfill = (PatternFill('solid', fgColor=RED) if stato == 'TETTO RAGGIUNTO' else
               PatternFill('solid', fgColor=ORA) if stato == 'ATTENZIONE' else
               (PatternFill('solid', fgColor=ICE) if i % 2 else None))
    for j, v in enumerate(vals):
        c = ws.cell(row=rr, column=1 + j, value=v)
        c.font = Font(name='Inter', size=9)
        if rowfill: c.fill = rowfill
        if j >= 1: c.alignment = Alignment(horizontal='center')
rr = 5 + len(EMP)
ws.cell(row=rr, column=1, value='TOTALE').font = Font(name='Inter', size=9, bold=True)
for d in range(7):
    c = ws.cell(row=rr, column=3 + d, value=round(ot_g[d], 2) or '')
    c.font = Font(name='Inter', size=9, bold=True); c.alignment = Alignment(horizontal='center')
c = ws.cell(row=rr, column=10, value=round(tot_ot, 2))
c.font = Font(name='Inter', size=9, bold=True); c.alignment = Alignment(horizontal='center')
rr += 2
ws.cell(row=rr, column=1, value='Bilancio capacita settimana').font = Font(name='Inter', size=10, bold=True, color=DARK)
for k, (lbl, val) in enumerate([('Ore richieste dal modello', round(sum(req_d), 1)),
                                ('Monte ore contrattuale', sum(e['mh'] for e in EMP)),
                                ('Straordinari pianificati', round(tot_ot, 2)),
                                ('Scoperto residuo', round(max(0.0, sum(req_d) - sum(e['mh'] for e in EMP) - tot_ot), 1))]):
    ws.cell(row=rr + 1 + k, column=1, value=lbl).font = Font(name='Inter', size=9)
    c = ws.cell(row=rr + 1 + k, column=2, value=val)
    c.font = Font(name='Inter', size=9, bold=True); c.alignment = Alignment(horizontal='center')

# --- Foglio Executive Summary (nuovo)
ws = out.create_sheet('Executive Summary')
ws.sheet_view.showGridLines = False
ws['A1'] = 'EXECUTIVE SUMMARY  ·  ' + WEEK
ws['A1'].font = Font(name='Inter', size=14, bold=True, color=DARK)

# KPI
row = 3
kpi = [
    ('Ore richieste', sum(req_d)),
    ('Ore pianificate', sum(sched)),
    ('Straordinari totali', tot_ot),
    ('Costo stimato del lavoro (€)',
     round(sum(e['costo'] * (sum(DUR[e['id']]) - e['ot']) + e['costo'] * 1.5 * e['ot'] for e in EMP), 2)
     if all(e.get('costo') for e in EMP) else 'N/D (compila la colonna Costo_orario per tutti)'),
    ('Produttività (€/ora)', f"{sum(req_d)/sum(sched)*100:.1f}%" if sum(sched) else 'N/D'),
    ('Violazioni', len(viol))
]
for label, val in kpi:
    ws.cell(row=row, column=1, value=label).font = Font(name='Inter', size=10, bold=True)
    ws.cell(row=row, column=2, value=val).font = Font(name='Inter', size=10)
    row += 1

# Grafico delle coperture giornaliere (semplice)
if not viol:
    chart = BarChart()
    data = Reference(ws, min_col=2, min_row=3, max_row=3+len(kpi)-1, max_col=2)
    cats = Reference(ws, min_col=1, min_row=3, max_row=3+len(kpi)-1)
    chart.add_data(data, titles_from_data=False)
    chart.set_categories(cats)
    chart.title = "KPIs"
    chart.x_axis.title = "Indicatore"
    chart.y_axis.title = "Valore"
    ws.add_chart(chart, "D3")

# Registro straordinari log
if not A.no_log and tot_ot > 0:
    keep = [row for row in LOGROWS if row[0] != WEEK]
    for e in EMP:
        if e['ot'] > 0:
            keep.append([WEEK, e['name'], f"{e['ot']:g}"])
    with open(LOGFILE, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['settimana', 'dipendente', 'ore_straordinario'])
        w.writerows(sorted(keep))
    print(f'Registro straordinari aggiornato: {LOGFILE} (settimana {WEEK}).')

# Salva con timestamp
out_filename = f'Turni_generati_{WEEK}_{NOW}.xlsx'
out_path = os.path.join(A.output_dir, out_filename)
out.save(out_path)
# --- scrivi la giuntura di fine settimana (chiusure domenicali) per il controllo riposo tra settimane
if not A.no_log:
    try:
        with open(BOUNDARY_FILE, 'w', newline='', encoding='utf-8') as _f:
            _w = csv.writer(_f, delimiter=';')
            _w.writerow(['dipendente', 'chiusura_domenica', 'settimana'])
            for e in EMP:
                s = shifts[e['id']][6]
                if s is not None:
                    _w.writerow([e['name'], f'{s[1]:.4f}', WEEK])
        print(f'\U0001F517 Giuntura salvata: {BOUNDARY_FILE} (riposo lun. prossima settimana).')
    except Exception:
        pass

# --- storico settimanale: base dati per calibrare i minuti/PLT (ciclo chiuso)
if not A.no_log:
    HIST = 'rota_history.csv'
    _act = [(n, h) for n, h in comp if n]
    _header = ['settimana','timestamp','ore_richieste','ore_pianificate','straordinari',
               'auto_ot','violazioni','scoperto_residuo','teste'] + [n for n, _ in _act]
    _scoperto = round(max(0.0, sum(req_d) - sum(e['mh'] for e in EMP) - tot_ot), 2)
    _row = [WEEK, NOW, round(sum(req_d), 2), round(sum(sched), 2), round(tot_ot, 2),
            round(AUTO_OT_ADDED, 2), len(viol), _scoperto, len(EMP)] + \
           [round(h, 2) if isinstance(h, (int, float)) else '' for _, h in _act]
    try:
        _new = not os.path.exists(HIST)
        with open(HIST, 'a', newline='', encoding='utf-8') as _f:
            _w = csv.writer(_f, delimiter=';')
            if _new: _w.writerow(_header)
            _w.writerow(_row)
        print(f'\U0001F4C8 Storico aggiornato: {HIST} (pianificato vs richiesto per settimana).')
    except Exception:
        pass

# --- copia stabile 'ultimo' + apertura automatica su Windows
try:
    import shutil
    _latest = os.path.join(A.output_dir, 'Turni_ultimo.xlsx')
    shutil.copyfile(out_path, _latest)
    print(f'\U0001F4CC Copia stabile: {_latest} (sempre l\'ultima generata).')
except Exception:
    pass
if sys.platform.startswith('win') and not A.no_open and not A.preview:
    try:
        os.startfile(out_path)  # type: ignore
    except Exception:
        pass

print(f'\n📁 File scritto: {out_path}  (fogli: IncollaQui, Rota, Straordinari, Executive Summary)')
print('INCOLLA COSI: copia il blocco fisso B3:V24 -> Turni!F5 -> Incolla speciale > "Valori e formati dei numeri" + "Salta celle vuote".')
if viol:
    print('⚠️ ATTENZIONE: turni generati CON violazioni residue. Aumenta il monte ore, pianifica straordinari (--auto-ot) o riduci il fabbisogno.')
else:
    print('✅ Nessuna violazione: stacchi, coperture, presidio responsabile, aperture e chiusure tutti a norma.')