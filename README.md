# RoverDroneCooperation

Un ambiente di simulazione 3D sviluppato in Python con **Ursina Engine**, progettato per dimostrare la cooperazione multi-agente in scenari di ricerca e soccorso (Search and Rescue). Il sistema coordina un Drone da ricognizione e un Rover terrestre per localizzare, valutare e recuperare dispersi in un ambiente montano generato proceduralmente.

## Caratteristiche Principali

* **Generazione Mappa e Validazione:** Creazione interattiva di mappe a griglia con ostacoli e dispersi. Il sistema garantisce che la mappa sia sempre percorribile verificando la connettività delle celle vuote tramite ricerca BFS.

* **Ricognizione Autonoma (Drone):** Il drone pattuglia l'area utilizzando l'algoritmo *Breadth-First Search* per l'esplorazione, individuando i feriti nel suo raggio visivo 3x3.

* **Triage basato su Intelligenza Artificiale (LLM):** * Il drone analizza le condizioni mediche dei dispersi inviando le descrizioni a un modello LLM tramite **Groq** (`llama-3.1-8b-instant`), formulando un dispaccio radio con priorità mediche.

    * Il Rover processa i messaggi radio in linguaggio naturale tramite **OpenRouter / OpenAI** (`gpt-oss-120b:free` o Gemini), estraendo coordinate e priorità (Alta, Media, Bassa) per riordinare dinamicamente la coda di salvataggio.

* **Navigazione Avanzata (Rover):** Il Rover calcola il percorso ottimale verso i bersagli schivando gli ostacoli grazie all'algoritmo **A*** (A-Star).

* **Logistica Medevac:** Gestione realistica del carico. Il Rover ha una capienza massima di 3 passeggeri; una volta pieno (o in assenza di emergenze), calcola in automatico la rotta di ritorno verso l'Ospedale per lo sbarco dei feriti.

* **Ambiente Dinamico e Temporizzato:** Ogni disperso possiede un *Time-To-Live* (TTL). Il tempo avanza globalmente e le vittime non soccorse in tempo deperiscono. Nuove emergenze (vittime nascoste) possono comparire dinamicamente durante le fasi avanzate della simulazione.

* **Interfaccia Utente e Telemetria:** Console di sistema a scorrimento integrata per il monitoraggio in tempo reale dei log, dei dispacci radio e dei movimenti.

## Requisiti di Sistema

Il progetto fa uso di diverse librerie per la grafica 3D, gli algoritmi di ricerca (basati su AIMA) e l'integrazione con i LLM. Assicurati di installare le dipendenze fornite:

```bash
pip install -r requirements.txt
```
### Librerie principali incluse
Tutte le librerie utilizzate da installare sono state incluse nel file ```requirements.txt``` e sono le seguenti:
* ursina>=6.5.0
* numpy>=1.24.0
* groq>=0.4.0
* python-dotenv>=1.0.0
* google-genai
* openai
## Configurazione
Prima di avviare la simulazione, è necessario configurare le chiavi API per i servizi di intelligenza artificiale. Crea un file chiamato .env nella root del progetto e inserisci le tue chiavi:
```bash
GROQ_API_KEY=la_tua_chiave_groq_qui
OPENROUTER_API_KEY=la_tua_chiave_openrouter_qui
# Eventuali chiavi di fallback per Gemini (opzionale):
GEMINI_API_KEY1=la_tua_chiave_gemini_qui
```
## Come eseguire la simulazione
1. **Esegui** il file principale del progetto: ```python main.py```

2. **Setup Mappa**: Inserisci le dimensioni desiderate e clicca su "Genera Mappa Vuota".

3. **Costruzione Ambiente**: Usa i controlli a schermo per generare ostacoli e dispersi casuali. Clicca sulle singole celle per modificarle manualmente.

4. **Descrizione Vittime**: Inserisci lo stato di salute e il TTL stimato per ogni vittima identificata nella mappa.

5. **Fase di Deploy**: Clicca sulle celle della mappa per posizionare in sequenza:
  * Punto di partenza del Drone
  * Punto di partenza del Rover
  * Ospedale

6. **Avvio 3D**: Una volta completato il deploy, la simulazione passerà in visuale 3D e gli agenti inizieranno a cooperare autonomamente. Usa la console a schermo per monitorare le operazioni e il triage radio.

## Struttura del Progetto
* ```main.py```: Punto d'ingresso e interfaccia iniziale.

* ```ui.py```: Gestione delle transizioni di stato, editor della mappa e inizializzazione ambiente 3D.

* ```state.py```: Variabili globali di stato, gestione della UI e console di log.

* ```map_manager.py```: Logica di validazione della mappa (BFS) e generazione casuale.

* ```drone.py```: Movimento esplorativo e triage basato su Groq.

* ```rover.py```: Algoritmo A*, parsing degli obiettivi via LLM e logistica di trasporto all'ospedale.

* ```simulation.py```: Gestione del passaggio del tempo (TTL) e generazione di eventi imprevisti.

* ```libs/```: Cartella contenente le librerie core per gli algoritmi di ricerca (basate su AIMA):
  * ```aima.py```: Implementazione base delle classi ```Problem```, ```Node``` e degli algoritmi di navigazione (A*, BFS, ecc.).
  * ```search.py```,```utils.py```,```utils4e.py```: Strutture dati di supporto (es. Code di priorità) e utility matematiche per gli algoritmi.

* ```models/```: Cartella contenente le texture con file ```.jpeg``` e i modelli 3d con file ```.obj```
