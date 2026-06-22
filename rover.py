from ursina import *
from libs.aima import *
import re
import os
import state
import threading
from simulation import avanza_tempo_globale
from dotenv import load_dotenv
from google import genai
from state import log_messaggio

mission_lock = threading.Lock()


load_dotenv()
API_KEYS_GEMINI = [os.getenv(f"GEMINI_API_KEY{i}") for i in range(1,4)]

idx_current_key =0
if API_KEYS_GEMINI:
    client_gemini = genai.Client(api_key=API_KEYS_GEMINI[idx_current_key])
else:
    client_gemini = genai.Client()

class GridNavigationProblem(Problem):
    def __init__(self, initial, goal, map_w, map_h, ostacoli):
        super().__init__(initial, goal)
        self.map_w = map_w
        self.map_h = map_h
        self.ostacoli = ostacoli

    def actions(self, state):
        x, y = state
        possible_actions = []
        if y < self.map_h - 1 and (x, y + 1) not in self.ostacoli: possible_actions.append('UP')
        if y > 0 and (x, y - 1) not in self.ostacoli: possible_actions.append('DOWN')
        if x < self.map_w - 1 and (x + 1, y) not in self.ostacoli: possible_actions.append('RIGHT')
        if x > 0 and (x - 1, y) not in self.ostacoli: possible_actions.append('LEFT')
        return possible_actions

    def result(self, state, action):
        x, y = state
        if action == 'UP': return (x, y + 1)
        if action == 'DOWN': return (x, y - 1)
        if action == 'RIGHT': return (x + 1, y)
        if action == 'LEFT': return (x - 1, y)

    def h(self, node):
        x_curr, y_curr = node.state
        x_goal, y_goal = self.goal
        return abs(x_curr - x_goal) + abs(y_curr - y_goal)

class RoverAgent:
    def __init__(self, initial_position):
        self.position = initial_position
        self.client = client_gemini  
        self.model_name = 'gemini-2.5-flash-lite' 

    def _filtra_coordinate_valide(self, lista_goal):
        """Scarta eventuali coordinate inventate dall'LLM che non corrispondono a vittime realmente scoperte."""
        coordinate_reali = {(v.grid_x, v.grid_y) for v in state.vittime_scoperte}
        validi = []
        for (x, y), priorita in lista_goal:
            if (x, y) in coordinate_reali:
                validi.append(((x, y), priorita))
            else:
                print(f"[ROVER - SCARTO] Coordinate ({x},{y}) non corrispondono a nessuna vittima nota: scartate.")
        return validi

    def _extract_goals_with_llm(self, text_message, coda_attuale):
        global idx_current_key

        current_rover_pos = self.position 
        
        # ORA coda_attuale contiene ((x, y), 'Priorità'). Formattiamo la stringa di conseguenza:
        coda_str = ", ".join([f"({x},{y}) [Priorità: {p}]" for (x, y), p in coda_attuale]) if coda_attuale else "Nessun obiettivo in attesa."

        prompt = f"""
        Sei il sistema di comunicazione di un Rover di soccorso che comunica con un drone di ricognizione in ambiente montano della protezione civile. 
        Posizione attuale del Rover: {current_rover_pos}.
        Obiettivi attuali in attesa: {coda_str}
        
        Hai appena ricevuto questo nuovo dispaccio radio: "{text_message}"
        
        IL TUO COMPITO (OBBLIGATORIO):
        1. Estrai le nuove coordinate dal dispaccio radio e la priorità medica di OGNI vittima menzionata.
        2. Unisci tutte le vittime (quelle attuali + quelle nuove appena ricevute).
        3. ORDINA TUTTE le vittime per priorità medica DECRESCENTE:
           - PRIMA: Alta (massima urgenza)
           - DOPO: Media
           - ULTIMO: Bassa (minima urgenza)
        4. A PARITÀ di priorità, ordina per distanza dal Rover (più vicina per prima).
        
        SCALA DI PRIORITÀ OBBLIGATORIA: Alta > Media > Bassa
        ORDINAMENTO OBBLIGATORIO: Alta viene SEMPRE prima di Media, Media viene SEMPRE prima di Bassa
        
        RISPOSTA TASSATIVA - NON AGGIUNGERE NULLA:
        Rispondi ESCLUSIVAMENTE con la lista completa ORDINATA (niente altro), una per riga nel formato esatto: 
        X, Y, Priorità
        """

        max_tries = len(API_KEYS_GEMINI)

        for tentativo in range(max_tries):
            try:
                # Proviamo a generare il contenuto
                response = self.client.models.generate_content(model=self.model_name, contents=prompt)
                text_output = response.text.strip()
                break
            except Exception as e:
                error_msg = str(e).lower()
                if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg:
                    print(f"[SISTEMA] Chiave {idx_current_key + 1} esaurita. Rotazione in corso...")
                    idx_current_key = (idx_current_key + 1) % len(API_KEYS_GEMINI)
                    self.client = genai.Client(api_key=API_KEYS_GEMINI[idx_current_key])
                    print(f"[SISTEMA] Passaggio alla chiave {idx_current_key + 1} completato. Nuovo tentativo...")
                else:
                    print(f"[SISTEMA] Errore critico API: {e}")
                    return [] # O gestisci l'errore come preferisci



        extracted_goals = []
        for line in text_output.split('\n'):
            # Modifichiamo la Regex per prendere anche la priorità
            match = re.search(r'(\d+)\s*,\s*(\d+)\s*,\s*(Alta|Media|Bassa)', line, re.IGNORECASE)
            if match:
                x = int(match.group(1))
                y = int(match.group(2))
                priorita = match.group(3).capitalize()
                extracted_goals.append(((x, y), priorita))
                
        extracted_goals = self._filtra_coordinate_valide(extracted_goals)
        return extracted_goals
    
    def receive_and_execute_mission(self, drone_message):
        state.log_messaggio(f"\n[ROVER - RADIO] Ricevuto dispaccio:\n{drone_message}")
        
        # Passiamo a Gemini anche la coda di salvataggio attuale dello stato
        nuova_coda_ordinata = self._extract_goals_with_llm(drone_message, state.coda_obiettivi_rover)
        
        state.log_messaggio(f"[ROVER - TATTICA LLM] Nuova coda riordinata: {nuova_coda_ordinata}")
        return nuova_coda_ordinata

def calcola_prossimo_percorso_rover():
    # 1. Valutazione ritorno all'ospedale: ci vado se sono pieno (3 passeggeri) 
    # OPPURE se ho salvato qualcuno e non ci sono altri allarmi in coda.
    if len(state.passeggeri_rover) >= getattr(state, 'CAPACITA_MAX_ROVER', 3) or (len(state.passeggeri_rover) > 0 and not state.coda_obiettivi_rover):
        state.rover_in_movimento = True
        state.in_viaggio_verso_ospedale = True
        obiettivo_attuale = getattr(state, 'ospedale_posizione', (0,0))
        state.obiettivo_corrente = obiettivo_attuale
        state.log_messaggio(f"[ROVER - MEDEVAC] Ritorno alla base! Direzione OSPEDALE {obiettivo_attuale} con {len(state.passeggeri_rover)} feriti a bordo.")
        
    # 2. Valutazione soccorso: ho allarmi in coda e spazio a bordo
    elif state.coda_obiettivi_rover:
        state.rover_in_movimento = True
        state.in_viaggio_verso_ospedale = False
        obiettivo_dati = state.coda_obiettivi_rover.pop(0)
        obiettivo_attuale = obiettivo_dati[0] 
        priorita = obiettivo_dati[1]          
        
        state.obiettivo_corrente = obiettivo_attuale
        state.log_messaggio(f"[ROVER] Dirigendosi a {obiettivo_attuale} (Priorità: {priorita}). Spazio a bordo: {3 - len(state.passeggeri_rover)}")
        
    # 3. Nessun allarme e stiva vuota
    else:
        state.rover_in_movimento = False
        state.log_messaggio("[ROVER] Tutti gli obiettivi raggiunti. Passeggeri scesi. In attesa...")
        return

    # Calcolo A*
    ostacoli = set((c.grid_x, c.grid_y) for c in state.grid_cells if getattr(c, 'is_obstacle', False))
    start_pos = (state.rover.grid_x, state.rover.grid_y)
    problema = GridNavigationProblem(start_pos, obiettivo_attuale, state.map_w, state.map_h, ostacoli)
    nodo_soluzione = astar_search(problema)
    
    if nodo_soluzione:
        state.percorso_rover_corrente = [n.state for n in nodo_soluzione.path()][1:]
        state.log_messaggio(f"  [A*] Rotta per {obiettivo_attuale} calcolata! Passi: {len(state.percorso_rover_corrente)}")
        esegui_passo_rover()
    else:
        state.log_messaggio(f"  [A*] ERRORE GRAVE: Nessuna rotta per {obiettivo_attuale}.")
        if not state.in_viaggio_verso_ospedale:
            # Salta il bersaglio irragiungibile e riprova
            calcola_prossimo_percorso_rover()
        else:
            # Se l'ospedale è irraggiungibile, fermati
            state.rover_in_movimento = False

def esegui_passo_rover():
    if not state.percorso_rover_corrente:
        # Se siamo arrivati alla destinazione finale del percorso attuale
        if getattr(state, 'in_viaggio_verso_ospedale', False):
            # Logica di scarico all'ospedale
            state.log_messaggio(f"[OSPEDALE] Rover arrivato! Sbarco di {len(state.passeggeri_rover)} pazienti completato con successo.")
            state.passeggeri_rover.clear() # Svuota il rover
            
            # AGGIORNA UI DOPO LO SCARICO
            if state.testo_capienza_ui:
                state.testo_capienza_ui.text = f"Capienza Rover: {len(state.passeggeri_rover)}/3"

            state.in_viaggio_verso_ospedale = False
        else:
            state.log_messaggio("[ROVER] Raggiunta l'ultima posizione nota.")
            
        invoke(calcola_prossimo_percorso_rover, delay=1.5)
        return

    nuovo_x, nuovo_y = state.percorso_rover_corrente.pop(0)
    state.rover.grid_x, state.rover.grid_y = nuovo_x, nuovo_y
    state.rover_agent_instance.position = (nuovo_x, nuovo_y) 
    
    offset_x, offset_y = (state.map_w - 1) / 2, (state.map_h - 1) / 2
    state.rover.animate_position((nuovo_x - offset_x, nuovo_y - offset_y, -0.5), duration=0.4, curve=curve.linear)
    
    state.mosse_rover_parziali += 1
    if state.mosse_rover_parziali >= 2:
        state.mosse_rover_parziali = 0
        avanza_tempo_globale()
       
    vittima_incontrata = False
    for c in state.grid_cells:
        if c.grid_x == nuovo_x and c.grid_y == nuovo_y and getattr(c, 'is_disperso', False):

            if c in getattr(state, 'vittime_nascoste', []):
                continue

            if not getattr(c, 'morto', False) and not getattr(c, 'salvato', False):
                
                # Controlla se c'è spazio a bordo
                if len(getattr(state, 'passeggeri_rover', [])) < getattr(state, 'CAPACITA_MAX_ROVER', 3):
                    c.salvato = True
                    c.is_disperso = False # Scompare dalla mappa 3D perché è dentro il Rover
                    c.color= color.hex('#7CFC00')
                    state.passeggeri_rover.append(c)
                    vittima_incontrata = True

                    # AGGIORNA UI DOPO IL CARICO
                    if state.testo_capienza_ui:
                        state.testo_capienza_ui.text = f"Capienza Rover: {len(state.passeggeri_rover)}/3"
    
                    
                    if hasattr(state, 'obiettivo_corrente') and (nuovo_x, nuovo_y) == state.obiettivo_corrente:
                        state.log_messaggio(f"\n[ROVER] Recuperato bersaglio in ({nuovo_x}, {nuovo_y}). Carico: {len(state.passeggeri_rover)}/3")
                    else:
                        state.log_messaggio(f"\n[ROVER] INCONTRO FORTUITO! Caricata vittima extra in ({nuovo_x}, {nuovo_y}). Carico: {len(state.passeggeri_rover)}/3")
                        # Rimuovi l'incontro fortuito dalla coda per non tornarci inutilmente
                        state.coda_obiettivi_rover = [ob for ob in state.coda_obiettivi_rover if ob[0] != (nuovo_x, nuovo_y)]

                else:
                    state.log_messaggio(f"\n[ROVER] Vittima in ({nuovo_x}, {nuovo_y}) trovata, ma il Rover è PIENO (3/3)! Tornerò dopo lo scarico.")

    ritardo_prossimo_passo = 1.5 if vittima_incontrata else 0.5
    invoke(esegui_passo_rover, delay=ritardo_prossimo_passo)
