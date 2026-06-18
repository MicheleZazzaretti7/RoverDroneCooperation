from ursina import *
from aima import *
import re
import os
import state
from simulation import avanza_tempo_globale
from dotenv import load_dotenv
from google import genai
from state import log_messaggio

load_dotenv()
API_KEY_GEMINI = os.getenv("GEMINI_API_KEY2")
client_gemini = genai.Client(api_key=API_KEY_GEMINI) if API_KEY_GEMINI else genai.Client()

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

    def _extract_goals_with_llm(self, text_message, coda_attuale):
        current_rover_pos = self.position 
        
        # ORA coda_attuale contiene ((x, y), 'Priorità'). Formattiamo la stringa di conseguenza:
        coda_str = ", ".join([f"({x},{y}) [Priorità: {p}]" for (x, y), p in coda_attuale]) if coda_attuale else "Nessun obiettivo in attesa."

        prompt = f"""
        Sei il sistema di comunicazione di un Rover di soccorso che comunica con un drone di ricognizione in ambiente montano della protezione civile. 
        Posizione attuale del Rover: {current_rover_pos}.
        Obiettivi attuali in attesa in ordine di priorità: {coda_str}
        
        Hai appena ricevuto questo nuovo dispaccio radio: "{text_message}"
        
        IL TUO COMPITO:
        1. Estrai le nuove coordinate dal dispaccio radio e identifica la priorità medica indicata.
        2. Concatena il nuovo obiettivo agli "Obiettivi attuali in attesa" riordinandoli rispetto alla priorità assegnatagli.  la scala di priorità è "Alta > Media > Bassa".
        3. A parità di priorità, metti per primo l'obiettivo più vicino al Rover.
        
        RISPOSTA TASSATIVA:
        Rispondi SOLO con la lista completa e aggiornata, una per riga nel formato esatto: X, Y, Priorità.
        Non aggiungere testo, commenti o altro.
        """
        response = self.client.models.generate_content(model=self.model_name, contents=prompt)
        text_output = response.text.strip()
        
        extracted_goals = []
        for line in text_output.split('\n'):
            # Modifichiamo la Regex per prendere anche la priorità
            match = re.search(r'(\d+)\s*,\s*(\d+)\s*,\s*(Alta|Media|Bassa)', line, re.IGNORECASE)
            if match:
                x = int(match.group(1))
                y = int(match.group(2))
                priorita = match.group(3).capitalize()
                extracted_goals.append(((x, y), priorita))
                
        return extracted_goals
    
    def receive_and_execute_mission(self, drone_message):
        state.log_messaggio(f"\n[ROVER - RADIO] Ricevuto dispaccio:\n{drone_message}")
        
        # Passiamo a Gemini anche la coda di salvataggio attuale dello stato
        nuova_coda_ordinata = self._extract_goals_with_llm(drone_message, state.coda_obiettivi_rover)
        
        state.log_messaggio(f"[ROVER - TATTICA LLM] Nuova coda riordinata: {nuova_coda_ordinata}")
        return nuova_coda_ordinata

def calcola_prossimo_percorso_rover():
    if not state.coda_obiettivi_rover:
        state.rover_in_movimento = False
        state.log_messaggio("[ROVER] Tutti gli obiettivi raggiunti. In attesa...")
        return
        
    state.rover_in_movimento = True
    # Adesso estraiamo sia le coordinate che la priorità
    obiettivo_dati = state.coda_obiettivi_rover.pop(0)
    obiettivo_attuale = obiettivo_dati[0] # Prende solo (X, Y)
    priorita = obiettivo_dati[1]          # Prende la priorità (es. 'Alta')
    
    state.obiettivo_corrente = obiettivo_attuale # Salviamo nello state per esegui_passo_rover
    state.log_messaggio(f"[ROVER] Dirigendosi a {obiettivo_attuale} (Priorità: {priorita})")
    
    ostacoli = set((c.grid_x, c.grid_y) for c in state.grid_cells if getattr(c, 'is_obstacle', False))
    start_pos = (state.rover.grid_x, state.rover.grid_y)
    problema = GridNavigationProblem(start_pos, obiettivo_attuale, state.map_w, state.map_h, ostacoli)
    nodo_soluzione = astar_search(problema)
    
    if nodo_soluzione:
        state.percorso_rover_corrente = [n.state for n in nodo_soluzione.path()][1:]
        state.log_messaggio(f"  [A*] Rotta per {obiettivo_attuale} calcolata! Passi: {len(state.percorso_rover_corrente)}")
        esegui_passo_rover()
    else:
        state.log_messaggio(f"  [A*] ERRORE: Nessuna rotta sicura per {obiettivo_attuale}. Salto bersaglio.")
        calcola_prossimo_percorso_rover()

def esegui_passo_rover():
    if not state.percorso_rover_corrente:
        state.log_messaggio(f"[ROVER] Arrivato alla destinazione pianificata!")
        for c in state.grid_cells:
            if c.grid_x == state.rover.grid_x and c.grid_y == state.rover.grid_y and getattr(c, 'is_disperso', False):
                if not getattr(c, 'morto', False) and not getattr(c, 'salvato', False):
                    c.color = color.blue 
                    c.text = "OK"
                    c.salvato = True 
                    state.log_messaggio(f"  [ROVER] Vittima in ({c.grid_x}, {c.grid_y}) salvata con successo!")
        
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
            if not getattr(c, 'morto', False) and not getattr(c, 'salvato', False):
                c.color = color.blue 
                c.text = "OK"
                c.salvato = True
                vittima_incontrata = True
                
                # Controlla se è l'obiettivo principale o un incontro fortuito
                if hasattr(state, 'obiettivo_corrente') and (nuovo_x, nuovo_y) == state.obiettivo_corrente:
                    state.log_messaggio(f"\n[ROVER] Obiettivo raggiunto! Salvata vittima in ({nuovo_x}, {nuovo_y}).")
                else:
                    state.log_messaggio(f"\n[ROVER] INCONTRO FORTUITO! Salvata vittima non programmata in ({nuovo_x}, {nuovo_y})!")
                    # Rimuove l'obiettivo raggiunto dalla coda filtrandolo
                    state.coda_obiettivi_rover = [ob for ob in state.coda_obiettivi_rover if ob[0] != (nuovo_x, nuovo_y)]
    ritardo_prossimo_passo = 1.5 if vittima_incontrata else 0.5
    invoke(esegui_passo_rover, delay=ritardo_prossimo_passo)
