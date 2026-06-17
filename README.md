# Rover Drone Cooperation 3D Search & Rescue AI Simulation
Una piattaforma di simulazione avanzata per operazioni di ricerca e soccorso, che integra algoritmi di ricerca classici dell'intelligenza artificiale con i moderni modelli linguistici di grandi dimensioni (LLM).

##  Descrizione del Progetto

Questo progetto simula uno scenario di emergenza in un ambiente 3D interattivo sviluppato con il motore **Ursina**. L'obiettivo è coordinare due agenti autonomi per localizzare e salvare vittime disperse in un territorio impervio, gestendo al contempo ostacoli naturali e vincoli temporali.

### Gli Agenti
1.  **Il Drone (Esploratore):** Sorvola la mappa per individuare i dispersi e analizzare le loro condizioni tramite una "visione artificiale" simulata.
2.  **Il Rover (Soccorritore):** Riceve i dispacci dal drone, pianifica il percorso ottimale evitando le montagne e raggiunge le vittime prima che il loro tempo di vita (TTL) scada.

##  Caratteristiche Tecniche

*   **Ambiente 3D Dinamico:** Sviluppato in Python con **Ursina Engine**, con generazione procedurale di ostacoli e validazione della connettività della mappa.
*   **Algoritmi di Ricerca (Framework AIMA):**
    *   **BFS (Breadth-First Search):** Utilizzato dal Drone per l'esplorazione sistematica dei waypoint.
    *   **A* (A-Star Search):** Utilizzato dal Rover per il calcolo del percorso più breve e sicuro verso i target.
*   **Integrazione LLM (Triage e Strategia):**
    *   **Groq (Llama-3.1-8B):** Genera dispacci radio realistici basati su descrizioni testuali delle vittime, assegnando priorità medica.
    *   **Google Gemini (2.5 Flash):** Analizza i messaggi radio ricevuti dal Rover per estrarre coordinate e pianificare la missione in base alla priorità.
*   **Meccaniche di Simulazione:** Turni globali, decadimento della salute delle vittime e spawn dinamico di emergenze.

##  Struttura del Progetto

- `main.py`: Entry point dell'applicazione e inizializzazione UI.
- `ui.py`: Gestione dei flussi di setup, inserimento dati e deploy degli agenti.
- `map_manager.py`: Logica di gestione della griglia, ostacoli e validazione topologica.
- `drone.py`: Comportamento dell'agente aereo e integrazione Groq.
- `rover1.py`: Comportamento dell'agente terrestre, integrazione Gemini e logica A*.
- `state.py`: Gestione centralizzata dei dati globali e degli agenti.
- `aima.py`: Implementazione degli algoritmi di ricerca (Russell & Norvig).
- `simulation.py`: Motore temporale e gestione della vita dei dispersi.

##  Requisiti e Installazione

### Prerequisiti
- Python 3.8 o superiore.
- Una chiave API per **Groq** e **Google Gemini**.

### Installazione
1.  Clona la repository o scarica i file sorgente.
2.  Installa le dipendenze necessarie:
    ```bash
    pip install ursina groq google-genai python-dotenv
    ```
3.  Crea un file `.env` nella cartella principale e inserisci le tue chiavi:
    ```env
    GROQ_API_KEY="tua_chiave_groq"
    GEMINI_API_KEY="tua_chiave_gemini"
    ```

##  Guida all'Uso

1.  Lancia il programma: `python main.py`.
2.  **Setup Mappa:** Imposta dimensioni, genera ostacoli casuali e verifica che non ci siano aree isolate.
3.  **Configurazione Vittime:** Inserisci descrizioni (es. "ferita alla gamba") e i turni di vita stimati.
4.  **Deploy:** Posiziona Drone e Rover sulla griglia.
5.  **Simulazione:** Osserva gli agenti cooperare. Segui il log in console per leggere i dispacci radio generati dalle IA in tempo reale.
