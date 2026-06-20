from ursina import *
from aima import *
import random
import threading
import os
from groq import Groq
import state
from simulation import avanza_tempo_globale, spawna_vittime
import rover
from state import log_messaggio

CHIAVE_API = os.getenv("GROQ_API_KEY")
client_llm = Groq(api_key=CHIAVE_API)

class DroneExplorationProblem(Problem):
    def __init__(self, initial, goal, map_w, map_h):
        super().__init__(initial, goal)
        self.map_w = map_w
        self.map_h = map_h

    def actions(self, state):
        x, y = state
        possible_actions = []
        if y < self.map_h - 1: possible_actions.append("Up_1")
        if y > 0: possible_actions.append("Down_1")
        if x < self.map_w - 1: possible_actions.append("Right_1")
        if x > 0: possible_actions.append("Left_1")
        if y < self.map_h - 2: possible_actions.append("Up_2")
        if y > 1: possible_actions.append("Down_2")
        if x < self.map_w - 2: possible_actions.append("Right_2")
        if x > 1: possible_actions.append("Left_2")
        return possible_actions

    def result(self, state, action):
        x, y = state
        if action == "Up_1": return (x, y + 1)
        if action == "Up_2": return (x, y + 2)
        if action == "Down_1": return (x, y - 1)
        if action == "Down_2": return (x, y - 2)
        if action == "Right_1": return (x + 1, y)
        if action == "Right_2": return (x + 2, y)
        if action == "Left_1": return (x - 1, y)
        if action == "Left_2": return (x - 2, y)
        return state

def esegui_piano_volo_drone():
    if not state.drone: return

    if not state.piano_volo_drone:
        goal_x = random.randint(0, state.map_w - 1)
        goal_y = random.randint(0, state.map_h - 1)
        stato_iniziale = (state.drone.grid_x, state.drone.grid_y)
        obiettivo = (goal_x, goal_y)
        
        if stato_iniziale != obiettivo:
            problema_drone = DroneExplorationProblem(stato_iniziale, obiettivo, state.map_w, state.map_h)
            nodo_soluzione = breadth_first_graph_search(problema_drone)
            if nodo_soluzione:
                state.piano_volo_drone = nodo_soluzione.solution() 
                print(f"[NAVIGAZIONE] Nuovo Waypoint: {obiettivo}. Rotta: {state.piano_volo_drone}")

    if state.piano_volo_drone:
        prossima_mossa = state.piano_volo_drone.pop(0)
        parti_azione = prossima_mossa.split('_')
        direzione = parti_azione[0]
        passi = int(parti_azione[1])

        nuovo_x, nuovo_y = state.drone.grid_x, state.drone.grid_y
        if direzione == "Up": nuovo_y += passi
        elif direzione == "Down": nuovo_y -= passi
        elif direzione == "Right": nuovo_x += passi
        elif direzione == "Left": nuovo_x -= passi

        state.drone.grid_x, state.drone.grid_y = nuovo_x, nuovo_y
        offset_x, offset_y = (state.map_w - 1) / 2, (state.map_h - 1) / 2
        state.drone.animate_position((nuovo_x - offset_x, nuovo_y - offset_y, -2.5), duration=0.3, curve=curve.linear)

        state.turni_trascorsi += 1
        if state.turni_trascorsi == 1: spawna_vittime(2)
        elif state.turni_trascorsi % 7 == 0: spawna_vittime(1)

        if not state.rover_in_movimento:
            state.mosse_drone_parziali += 1
            if state.mosse_drone_parziali >= 6:
                state.mosse_drone_parziali = 0
                avanza_tempo_globale()

        controlla_visione_drone()

    invoke(esegui_piano_volo_drone, delay=0.5)

def controlla_visione_drone():
    vittime_vive_trovate = []  # accumula tutte le vittime vive scoperte in QUESTO giro di scansione

    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            check_x = state.drone.grid_x + dx
            check_y = state.drone.grid_y + dy
            
            for disp in state.vittime_attive[:]: 
                if disp.grid_x == check_x and disp.grid_y == check_y:
                    if getattr(disp, 'salvato', False):
                        state.vittime_attive.remove(disp)
                        continue 
                    
                    state.vittime_attive.remove(disp)
                    state.vittime_scoperte.append(disp)
                    disp.scoperto = True
                    
                    if getattr(disp, 'morto', False):
                        disp.color = color.black
                        disp.text = "X"
                        disp.text_color = color.red
                        state.log_messaggio(f"\n[DRONE] Avvistato cadavere in ({check_x}, {check_y}). Troppo tardi.")
                    else:
                        disp.color = color.magenta
                        disp.text = str(disp.ttl) 
                        disp.text_color = color.white
                        state.log_messaggio(f"\n[DRONE] Avvistato soggetto VIVO in ({check_x}, {check_y})!")
                        vittime_vive_trovate.append(disp)

    # Solo DOPO aver scandagliato l'intera visuale 3x3, valutiamo tutte le vittime vive trovate insieme
    if vittime_vive_trovate:
        thread = threading.Thread(target=chiama_llm_triage, args=(vittime_vive_trovate,))
        thread.start()

def chiama_llm_triage(lista_vittime):
    descrizioni_str = "\n".join(
        f"- Coordinate ({v.grid_x}, {v.grid_y}): \"{getattr(v, 'descrizione', 'Nessuna')}\""
        for v in lista_vittime
    )
    print(f"\n[LLM] Connessione a Groq... Generazione dispaccio per {len(lista_vittime)} vittima/e.")
    
    prompt_drone = f"""
    Sei un drone di ricognizione di un ambiente montano della protezione civile.
    Hai appena identificato {len(lista_vittime)} ferito/i nella tua visuale, alle seguenti coordinate e con le seguenti descrizioni:
    {descrizioni_str}

    Il tuo compito è inviare UN SOLO messaggio radio al Rover di recupero che riporti TUTTE le vittime sopra elencate.
    Regole TASSATIVE:
    1. Includi SEMPRE le coordinate di OGNI vittima elencata.
    2. Valuta la gravità di CIASCUNA vittima singolarmente, in base alla sua descrizione.
    3. Indica per ognuna la priorità medica ("alta", "media" o "bassa") in base alla gravità valutata.
    4. Se non esiste una descrizione, non inventare nulla e scrivi "Stato sconosciuto".
    5. REGOLA D'ORO: Rispondi SOLO ed ESCLUSIVAMENTE con il testo del messaggio radio, una frase breve per vittima. NON aggiungere premesse, saluti o giustificazioni finali. Qualsiasi parola fuori dal messaggio radio farà fallire la missione.
    """

    try:
        risposta = client_llm.chat.completions.create(
            messages=[{"role": "user", "content": prompt_drone}],
            model="llama-3.1-8b-instant"
        )
        messaggio_radio = risposta.choices[0].message.content.strip()
        coordinate_str = ", ".join(f"({v.grid_x},{v.grid_y})" for v in lista_vittime)
        state.log_messaggio(f"\n [DISPACCIO DRONE-TO-ROVER] Avvistamento {coordinate_str}:\n«{messaggio_radio}»")

        if state.rover_agent_instance:
            nuova_coda_completa = state.rover_agent_instance.receive_and_execute_mission(messaggio_radio)

            if nuova_coda_completa:
                state.coda_obiettivi_rover = nuova_coda_completa
                state.log_messaggio(f"[SISTEMA] Nuova rotta operativa: {state.coda_obiettivi_rover}")

                if not state.rover_in_movimento and state.coda_obiettivi_rover:
                    rover.calcola_prossimo_percorso_rover()

    except Exception as e:
        print(f"[ERRORE RADIO] Comunicazione fallita: {e}")