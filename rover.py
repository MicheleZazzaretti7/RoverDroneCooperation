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
API_KEY_GEMINI = os.getenv("GEMINI_API_KEY", "your_api_key")
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
        self.model_name = 'gemini-2.5-flash' 

    def _extract_goals_with_llm(self, text_message):
        current_rover_pos = self.position 
        prompt = f"""
        Sei il sistema di navigazione di un Rover. Posizione attuale: {current_rover_pos}.
        Analizza questo dispaccio radio e ordina le vittime.
        Regole: 1. Priorità medica (Alta, Media, Bassa). 2. A pari priorità, il più vicino.
        Rispondi SOLO con le coordinate numeriche estratte dal testo, una per riga (formato: x,y). Nessun commento.
        Messaggio: "{text_message}"
        """
        response = self.client.models.generate_content(model=self.model_name, contents=prompt)
        text_output = response.text.strip()
        extracted_goals = []
        for line in text_output.split('\n'):
            match = re.search(r'(\d+)\s*,\s*(\d+)', line)
            if match:
                extracted_goals.append((int(match.group(1)), int(match.group(2))))
        return extracted_goals

    def receive_and_execute_mission(self, drone_message):
        state.log_messaggio(f"\n[ROVER - RADIO] Ricevuto dispaccio:\n{drone_message}")
        goals = self._extract_goals_with_llm(drone_message)
        state.log_messaggio(f"[ROVER - LLM] Obiettivi calcolati: {goals}")
        return goals

def calcola_prossimo_percorso_rover():
    if not state.coda_obiettivi_rover:
        state.rover_in_movimento = False
        state.log_messaggio("[ROVER] Tutti gli obiettivi raggiunti. In attesa...")
        return
        
    state.rover_in_movimento = True
    obiettivo_attuale = state.coda_obiettivi_rover.pop(0)
    
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
                state.log_messaggio(f"\n[ROVER] INCONTRO FORTUITO! Salvata vittima non programmata in ({nuovo_x}, {nuovo_y})!")
                if (nuovo_x, nuovo_y) in state.coda_obiettivi_rover:
                    state.coda_obiettivi_rover.remove((nuovo_x, nuovo_y))

    ritardo_prossimo_passo = 1.5 if vittima_incontrata else 0.5
    invoke(esegui_passo_rover, delay=ritardo_prossimo_passo)
