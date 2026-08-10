#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scrive i turni generati direttamente nel foglio Turni di TOOL_LIDL.xlsx,
modificando SOLO l'XML del foglio Turni dentro lo zip .xlsx, lasciando
ogni altro file (grafici, data bar, formattazione condizionale, altri
fogli) byte-per-byte identico all'originale.

Perché non openpyxl.load_workbook + save(): verificato che questo causa
perdita reale di regole di formattazione condizionale avanzate (data bar)
su Dashboard e OreRichieste (da 6 a 3 regole) — vedi test in questa sessione.
"""
import re
import shutil
import zipfile
from openpyxl.utils import get_column_letter

R_SHARED_INDEX = 144  # indice di "R" in sharedStrings.xml (verificato)
# 'P' (permesso) non esiste in sharedStrings.xml: si scrive come inlineStr,
# senza toccare sharedStrings.xml (stessa garanzia di preservazione byte-per-byte).

DAY_PAIRS = [(6,7),(9,10),(12,13),(15,16),(18,19),(21,22),(24,25)]  # F,G | I,J | ...


def _cell_style(xml: str, ref: str) -> str:
    """Estrae l'attributo s= (stile) della cella esistente, per preservarlo."""
    m = re.search(rf'<c r="{ref}"[^>]*s="(\d+)"', xml)
    return m.group(1) if m else '110'  # fallback plausibile, non dovrebbe servire


def write_shifts_surgical(tool_lidl_path: str, out_path: str,
                          EMP: list, shifts: dict, day_label: dict = None,
                          max_slots: int = 22, first_row: int = 5) -> dict:
    """
    EMP: lista dipendenti presenti (stesso ordine di Personale, come li
         costruisce generatore_turni_v6.py) — EMP[i]['id'] indicizza shifts.
    shifts: dict {emp_id: [ (start,end)|None per 7 giorni ]}
    day_label: opzionale, dict {emp_id: ['R'|'P'|None per 7 giorni]} (attributo
               DAY_LABEL del motore) — distingue Riposo da Permesso nei
               giorni senza turno. Se assente, tutti i giorni None -> 'R'.
    Scrive SOLO nelle colonne F,G,I,J,L,M,O,P,R,S,U,V,X,Y (In/Out per giorno),
    righe first_row..first_row+max_slots-1. Non tocca A:E (nomi/ruolo,
    self-updating) né le colonne Ore/Tot/Delta (formule).
    """
    with zipfile.ZipFile(tool_lidl_path, 'r') as zin:
        names = zin.namelist()
        sheet_xml = zin.read('xl/worksheets/sheet5.xml').decode('utf-8')  # Turni

    n_written = 0
    for i in range(max_slots):
        row = first_row + i
        if i < len(EMP):
            e = EMP[i]
            day_shifts = shifts[e['id']]
            labels = day_label.get(e['id'], [None]*7) if day_label else [None]*7
        else:
            day_shifts = [None] * 7  # slot inutilizzato -> pulisci con 'R'
            labels = [None] * 7

        for d, (ci, co) in enumerate(DAY_PAIRS):
            s = day_shifts[d]
            for col, is_start in ((ci, True), (co, False)):
                ref = f"{get_column_letter(col)}{row}"
                style = _cell_style(sheet_xml, ref)
                if s is None:
                    if labels[d] == 'P':
                        new_cell = f'<c r="{ref}" s="{style}" t="inlineStr"><is><t>P</t></is></c>'
                    else:
                        new_cell = f'<c r="{ref}" s="{style}" t="s"><v>{R_SHARED_INDEX}</v></c>'
                else:
                    val = (s[0] if is_start else s[1]) / 24.0
                    new_cell = f'<c r="{ref}" s="{style}" t="n"><v>{val!r}</v></c>'

                pattern = rf'<c r="{ref}"[^>]*>.*?</c>|<c r="{ref}"[^/]*/>'
                new_xml, n = re.subn(pattern, new_cell, sheet_xml, count=1)
                if n != 1:
                    raise RuntimeError(f"Cella {ref} non trovata/non sostituita nell'XML di Turni.")
                sheet_xml = new_xml
                n_written += 1

    # Riscrive lo zip: tutti i file identici tranne sheet5.xml (Turni)
    with zipfile.ZipFile(tool_lidl_path, 'r') as zin, \
         zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == 'xl/worksheets/sheet5.xml':
                data = sheet_xml.encode('utf-8')
            zout.writestr(item, data)

    return {'celle_scritte': n_written}
