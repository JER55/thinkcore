# 🏪 ThinkCore — Gestione Turni Retail

Generatore automatico di turni settimanali per punti vendita retail —
applicabile a supermercati e
discount: bastano i parametri del proprio punto vendita nel
foglio `Parametri`, senza toccare il motore.

Vincoli CCNL gestiti nativamente: riposo minimo 11h, presidio
responsabile continuo, aperture/chiusure coperte, straordinari
distribuiti e limitati (settimanali + tetto annuo).

Interfaccia web in Streamlit, motore di ottimizzazione in Python puro,
con un livello di riparazione automatica delle violazioni residue e un
livello opzionale di analisi AI (DeepSeek) per interpretarle.

## Struttura del repo

```
app_lidl.py               interfaccia Streamlit (6 tab: Weekly Rotation,
                           Copertura, TimeFlow, Straordinari, Console,
                           Sostenibilità)
generatore_turni_v6.py     motore di generazione turni (anche da CLI) —
                           include il repair pass automatico (v. sotto)
ai_advisor.py              analisi AI (DeepSeek) della rota generata —
                           opzionale, no-op se non configurato
write_engine.py            scrittura chirurgica dei turni nel foglio
                           Turni di TOOL_LIDL.xlsx (XML-level, non tocca
                           formattazione condizionale/grafici)
cloud_storage.py           persistenza dei CSV di stato (locale o GitHub)
requirements.txt
.streamlit/secrets.toml.example   modello di configurazione persistenza
                           cloud e chiave DeepSeek
TOOL_LIDL_template.xlsx    modello Excel con dipendenti FITTIZI, per demo
                           pubbliche/test — la tua copia reale con i nomi
                           veri NON va mai versionata (vedi .gitignore)
```

Il file `TOOL_LIDL.xlsx` reale (con i nomi e le ore dei tuoi dipendenti)
**non è nel repo**: si carica a runtime dall'interfaccia con l'uploader,
proprio per non dover mai committare dati personali/retributivi.

## Riparazione automatica delle violazioni

Il motore non si limita a segnalare le violazioni: dopo aver generato i
turni, un secondo passaggio deterministico tenta di chiuderne una parte
riorganizzando i turni già assegnati — mai inventando ore che non
esistono, mai violando un vincolo per sistemarne un altro. Nello
specifico, per ogni giorno:

- **apertura/chiusura sotto soglia** → anticipa l'inizio o posticipa la
  fine del turno più vicino
- **buco di copertura generico** (oltre al presidio responsabile, già
  gestito da un meccanismo analogo preesistente) → estende il turno più
  vicino al buco

Ogni estensione è micro (≤30 minuti), passa sempre dal controllo dello
stacco minimo di 11h e dal tetto ore/giorno configurato, e non tocca mai
un dipendente con orario fisso quel giorno. Il dettaglio di cosa è stato
riparato compare in console (`=== RIPARAZIONI AUTOMATICHE ===`) e nel
tab **Straordinari** dell'app, sotto "Riparazioni automatiche".

**Cosa resta segnalato e non viene mai forzato automaticamente**: buchi
di copertura strutturali (monte ore insufficiente — lì la leva è
`--auto-ot` o più organico), stacchi di riposo tra un giorno e l'altro,
e qualunque orario fisso impostato in `Personale` — sono vincoli che
l'utente ha scelto apposta, non bug da correggere in autonomia.

## Analisi AI della rota (opzionale, DeepSeek)

`ai_advisor.py` prende il riepilogo della rota appena generata (ore
richieste/pianificate, straordinari, deficit, elenco violazioni) e lo
manda a DeepSeek, che restituisce un commento in italiano — causa più
probabile del problema e un suggerimento concreto (es. "il deficit di
sabato sera è dovuto a X, valuta `--auto-ot` o un turno fisso in più").

Importante: **l'AI qui spiega, non decide**. Chi *risolve* le violazioni
è sempre il repair pass deterministico sopra (validato passo per passo
con `ok_rest()`/`_full_validate()`); un modello linguistico non è
adatto a garantire da solo il rispetto di vincoli rigidi come il CCNL,
quindi non gli viene mai delegata la scelta di quale turno spostare.

Per attivarlo, in `.streamlit/secrets.toml`:

```toml
[deepseek]
api_key = "sk-xxxxxxxx"
```

Senza questa chiave, `ai_advisor.py` è un no-op silenzioso: il resto del
sistema funziona esattamente come prima.

## Esecuzione locale

```bash
git clone https://github.com/TUO-USER/thinkcore.git
cd thinkcore
pip install -r requirements.txt
streamlit run app_lidl.py
```

Si apre su `http://localhost:8501`. Carica il tuo `TOOL_LIDL.xlsx`,
premi **GENERA TURNI**.

In locale i 3 file di stato (`straordinari_log.csv`, `rota_boundary.csv`,
`rota_history.csv`) restano sul disco in `/tmp/rotosmart` e si
accumulano da una generazione all'altra: nessuna configurazione
aggiuntiva richiesta.

## Deploy online (Streamlit Community Cloud, gratuito)

1. Pusha questo repo su GitHub (pubblico o privato)
2. Vai su [share.streamlit.io](https://share.streamlit.io) → *New app*
3. Seleziona il repo, branch `main`, file principale `app_lidl.py`
4. Deploy — `requirements.txt` viene letto in automatico

### ⚠️ Persistenza dello stato tra settimane

Il filesystem di Streamlit Community Cloud è **effimero**: ad ogni
riavvio del container, i 3 CSV di stato locali spariscono. Questo rompe
due controlli del motore:

- il **tetto annuo straordinari** (letto da `straordinari_log.csv`)
- il **riposo 11h a cavallo tra domenica e lunedì** (letto da
  `rota_boundary.csv`)

Per questo `cloud_storage.py` sa sincronizzare questi 3 file con un
**repo GitHub separato e privato**, usato solo come "database":

1. Crea un repo privato dedicato, es. `thinkcore-state` (vuoto va bene)
2. Genera un GitHub Personal Access Token con permesso `repo` (classic)
   o `Contents: Read and write` (fine-grained), limitato a quel repo
3. Su Streamlit Cloud: **App → Settings → Secrets**, incolla:

   ```toml
   [github]
   token = "ghp_xxx..."
   repo  = "tuo-utente/thinkcore-state"
   path  = "data"
   ```

4. Riavvia l'app. Nella tab **Console** vedrai `Backend: github` e il
   report di sincronizzazione ad ogni generazione (caricato/salvato).

Senza questa configurazione l'app funziona comunque (`Backend: local`),
ma perde la continuità storica tra un riavvio e l'altro del container —
va benissimo per provare l'app, meno per l'uso settimanale reale.

## Modello dati (`TOOL_LIDL.xlsx`)

12 fogli: `Personale` (organico, monte ore, vincoli giornalieri),
`Parametri` (orari apertura/chiusura, riposo minimo, presidi minimi),
`Casse`/`OreRichieste`/`Volumi` (fabbisogno di copertura), `Turni`
(output), più dashboard e grafici. Vedi i commenti in testa a
`generatore_turni_v6.py` per il dettaglio colonna-per-colonna del foglio
Personale (colonne L–S: riposi/permessi/turni fissi per giorno).

## A chi è adatto

Pensato per un discount, ma la logica — copertura minima per
fascia oraria, staff polivalente senza reparti fissi, rotazione
responsabili, vincoli di riposo CCNL — è comune a gran parte dei
supermercati e discount di medie dimensioni. Adattarlo a un altro
punto vendita significa in pratica ricompilare `Parametri` (orari,
presidi minimi) e `Casse`/`OreRichieste` (fabbisogno) con i propri
numeri: il motore e l'interfaccia restano invariati. Punti vendita con
strutture molto diverse (reparti separati, orari 24h, più sedi da
pianificare insieme) richiederebbero invece un adattamento del modello,
non solo dei parametri.

## Licenza

Uso interno / proprietario — 
