# 🏪 ThinkCore — Gestione Turni Retail

Generatore automatico di turni settimanali per punti vendita retail
(nato su un negozio Lidl, ~1.400 mq), con vincoli CCNL: riposo minimo
11h, presidio responsabile continuo, aperture/chiusure coperte,
straordinari distribuiti e limitati (settimanali + tetto annuo).

Interfaccia web in Streamlit, motore di ottimizzazione in Python puro.

## Struttura del repo

```
app_lidl.py               interfaccia Streamlit (5 tab: Weekly Rotation,
                           Copertura, TimeFlow, Straordinari, Console)
generatore_turni_v6.py     motore di generazione turni (anche da CLI)
write_engine.py            scrittura chirurgica dei turni nel foglio
                           Turni di TOOL_LIDL.xlsx (XML-level, non tocca
                           formattazione condizionale/grafici)
cloud_storage.py           persistenza dei CSV di stato (locale o GitHub)
requirements.txt
.streamlit/secrets.toml.example   modello di configurazione persistenza cloud
TOOL_LIDL_template.xlsx    modello Excel con dipendenti FITTIZI, per demo
                           pubbliche/test — la tua copia reale con i nomi
                           veri NON va mai versionata (vedi .gitignore)
```

Il file `TOOL_LIDL.xlsx` reale (con i nomi e le ore dei tuoi dipendenti)
**non è nel repo**: si carica a runtime dall'interfaccia con l'uploader,
proprio per non dover mai committare dati personali/retributivi.

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

## Licenza

Uso interno / proprietario — adattare secondo necessità prima di
pubblicare il repo.
