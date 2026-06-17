# 1. Installiamo la libreria corretta (google-genai) e rimuoviamo quella vecchia per evitare conflitti
from aima import *
import re
import os
from dotenv import load_dotenv
# 2. Questo è l'import corretto per il nuovo SDK del 2026
from google import genai 
# Carica la chiave dal file .env se presente
load_dotenv()
API_KEY_GEMINI = os.getenv("GEMINI_API_KEY", "AIzaSyBMZzOOY0SZuCqLU2PrGnSe_nMtRaHuEdk")
client_gemini = genai.Client(api_key=API_KEY_GEMINI) if API_KEY_GEMINI else genai.Client()

# Coda di animazione del Rover
rover_agent_instance = None
coda_obiettivi_rover = []
percorso_rover_corrente = []


class GridNavigationProblem(Problem):
    def __init__(self, initial, goal, map_w, map_h, ostacoli):
        super().__init__(initial, goal)
        self.map_w = map_w
        self.map_h = map_h
        self.ostacoli = ostacoli # Set di tuple (x, y) con le montagne

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
        self.model_name = 'gemini-2.5-flash' # Flash è più veloce per il testing

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
        # Niente più 'global' qui dentro!
        print(f"\n[ROVER - RADIO] Ricevuto dispaccio:\n{drone_message}")
        goals = self._extract_goals_with_llm(drone_message)
        print(f"[ROVER - LLM] Obiettivi calcolati: {goals}")
        
        # Restituiamo la lista al file principale
        return goals
