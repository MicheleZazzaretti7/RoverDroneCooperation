from ursina import *
import random
import threading
import time
from groq import Groq
from aima import *
from drone1 import *
from rover import *


CHIAVE_API = os.getenv("GROQ_API_KEY", "your_api_key")
client_llm = Groq(api_key=CHIAVE_API)

app = Ursina(title="Mappa Personalizzabile")

# ==========================================
# Variabili Globali
# ==========================================
grid_cells = []
map_w = 0
map_h = 0
descrizione_dispersi = {}
dispersi = []
disperso_corrente_idx = 0
panel_description = None
input_description = None
error_text = None
stato_posizionamento = None
start_drone_pos=(0,0)
start_rover_pos= (0,0)
testo_istruzioni =None
turni_trascorsi = 0
vittime_nascoste = []  # Dispersi posizionati nel setup, ma non ancora visibili
vittime_attive = []    # Dispersi comparsi sulla mappa (colore rosso)
vittime_scoperte = []  # Dispersi trovati dal drone (in attesa di LLM o con Timer attivo)
# Nuove variabili globali
mosse_drone_parziali = 0
mosse_rover_parziali = 0
rover_in_movimento = False # Diventerà True quando implementerete l'A* del rover
piano_volo_drone = []

def avanza_tempo_globale():
    """Questa funzione fa scorrere un turno di vita per tutti i dispersi non salvati e non morti."""
    for cell in dispersi:

        if cell in vittime_nascoste:
            continue
        # Il tempo scorre SOLO se non è morto e NON è stato salvato
        if getattr(cell, 'morto', False) == False and getattr(cell, 'salvato', False) == False:
            cell.ttl -= 1
            
            # Aggiorniamo il testo a schermo
            if getattr(cell, 'scoperto', False) and cell.text_entity:
                cell.text = str(cell.ttl)
                
            # Condizione di morte
            if cell.ttl <= 0:
                cell.morto = True
                if cell.scoperto:
                    cell.color = color.black
                    cell.text = "X"
                    cell.text_color = color.red
                    print(f"[TRAGEDIA] Il soggetto in ({cell.grid_x}, {cell.grid_y}) è deceduto prima dei soccorsi.")
                else:
                    print(f"[SISTEMA] Segnale vitale perso da una posizione sconosciuta...")

# ==========================================
# Variabili per gli Agenti
# ==========================================
drone = None
rover = None
# ==========================================
# Modulo Simulazione 3D
# ==========================================
def avvia_simulazione_3d():
    global drone, rover, testo_istruzioni
    if testo_istruzioni:
        destroy(testo_istruzioni)
    
    # 1. Congela lo stato nascondendo eventuali UI residue
    if 'pannello_controlli' in globals(): pannello_controlli.enabled = False
    if 'map_panel' in globals(): map_panel.enabled = False

    for cell in grid_cells:
        cell.on_click = lambda: None
        cell.collider = None

        if cell.text_entity:
            cell.text_entity.disable()

        cell.model = 'cube'
        cell.texture='montagna.jpg'
        cell.scale_z = 0.2
        cell.z = 0
        Entity(parent=cell, model='cube', color=color.black, wireframe=True, scale=1.05)


        if cell.is_obstacle:
            montagna = Entity(
                parent=scene,
                model=Cone(resolution=4),
                texture='montagna.jpg',
                #color=color.dark_gray,
                scale=(0.7, 1.3, 0.7),
                position=(cell.x, cell.y, -0.50),
                rotation=(-90,0,0)
            )

            Entity(parent=montagna, model=Cone(resolution=4), color=color.black, wireframe=True, scale=1.05)
        elif cell.is_disperso:
            # Nascondiamo i dispersi facendoli sembrare erba normale
            cell.color = color.hex('#7CFC00')
            cell.texture='grass.jpg'
            vittime_nascoste.append(cell)
        else:
            cell.color = color.hex('#7CFC00')
            cell.texture='grass.jpg'


          

    # 2. Transizione Camera 3D (Vista Isometrica/Dall'alto inclinata)
    camera.orthographic = False
    #camera.position = (0, -(map_h / 1.5), -max(map_w, map_h) * 1.2)
    #camera.rotation_x = -35 # Inclina la telecamera
    
    EditorCamera()
    # 3. Impostazione delle coordinate reali vs logiche
    # Nascondi i testi di istruzione se esistono
    if testo_istruzioni:
        destroy(testo_istruzioni)
        
    # [...] (Qui c'è il ciclo for che trasforma le celle in 3D che abbiamo fatto prima) [...]

    # 3. Impostazione delle coordinate reali vs logiche usando le scelte dell'utente
    offset_x = (map_w - 1) / 2
    offset_y = (map_h - 1) / 2
    
    # Preleviamo le coordinate scelte nella fase precedente
    start_drone_x, start_drone_y = start_drone_pos
    start_rover_x, start_rover_y = start_rover_pos
    
    real_drone_x = start_drone_x - offset_x
    real_drone_y = start_drone_y - offset_y
    
    real_rover_x = start_rover_x - offset_x
    real_rover_y = start_rover_y - offset_y
    
    # 4. Istanziazione Agenti con le coordinate reali calcolate
    drone = Entity(model='craft_speederA.obj', color=color.cyan, texture='speeder.jpeg', scale=0.6, position=(real_drone_x, real_drone_y, -2.5), rotation=(-90, 0, 0))
    drone.grid_x = start_drone_x
    drone.grid_y = start_drone_y
    
    rover = Entity(model='craft_miner.obj', color=color.orange, texture='miner.jpeg', scale=0.7, position=(real_rover_x, real_rover_y, -0.5), rotation=(-90, 0, 0))
    rover.grid_x = start_rover_x
    rover.grid_y = start_rover_y

    global rover_agent_instance
    rover_agent_instance = RoverAgent((start_rover_x, start_rover_y)) # Crea l'intelligenza del Rover
    
    # 5. Avvia il comportamento del drone dopo 1 secondo di pausa
    invoke(esegui_piano_volo_drone, delay=1.0)

def calcola_prossimo_percorso_rover():
    global rover_in_movimento, percorso_rover_corrente
    
    if not coda_obiettivi_rover:
        rover_in_movimento = False
        print("[ROVER] Tutti gli obiettivi raggiunti. In attesa...")
        return
        
    rover_in_movimento = True
    obiettivo_attuale = coda_obiettivi_rover.pop(0)
    
    # 1. Raccogliamo gli ostacoli
    ostacoli = set((c.grid_x, c.grid_y) for c in grid_cells if c.is_obstacle)
    
    # 2. Definiamo il problema A*
    start_pos = (rover.grid_x, rover.grid_y)
    problema = GridNavigationProblem(start_pos, obiettivo_attuale, map_w, map_h, ostacoli)
    
    # 3. Risolviamo
    nodo_soluzione = astar_search(problema)
    
    if nodo_soluzione:
        # Estraiamo gli stati (le coordinate) dalla soluzione di AIMA
        percorso_rover_corrente = [n.state for n in nodo_soluzione.path()][1:] # Saltiamo il nodo di partenza
        print(f"  [A*] Rotta per {obiettivo_attuale} calcolata! Passi: {len(percorso_rover_corrente)}")
        esegui_passo_rover()
    else:
        print(f"  [A*] ERRORE: Nessuna rotta sicura per {obiettivo_attuale}. Salto bersaglio.")
        calcola_prossimo_percorso_rover()

def esegui_passo_rover():
    if not percorso_rover_corrente:
        print(f"[ROVER] Arrivato alla destinazione pianificata!")
        # Controlla se c'è un ferito qui e salvalo
        for c in grid_cells:
            if c.grid_x == rover.grid_x and c.grid_y == rover.grid_y and getattr(c, 'is_disperso', False):
                if not getattr(c, 'morto', False) and not getattr(c, 'salvato', False):
                    c.color = color.blue 
                    c.text = "OK"
                    c.salvato = True # Ferma il countdown!
                    print(f"  [ROVER] Vittima in ({c.grid_x}, {c.grid_y}) salvata con successo!")
                
        # Pausa per il salvataggio, poi passa al prossimo obiettivo
        invoke(calcola_prossimo_percorso_rover, delay=1.5)
        return

    # Eseguiamo il passo normale
    nuovo_x, nuovo_y = percorso_rover_corrente.pop(0)
    rover.grid_x, rover.grid_y = nuovo_x, nuovo_y
    rover_agent_instance.position = (nuovo_x, nuovo_y) 
    
    offset_x, offset_y = (map_w - 1) / 2, (map_h - 1) / 2
    rover.animate_position((nuovo_x - offset_x, nuovo_y - offset_y, -0.5), duration=0.4, curve=curve.linear)
    
    # IL ROVER SI MUOVE -> IL TEMPO SCORRE
    global mosse_rover_parziali
    
    offset_x, offset_y = (map_w - 1) / 2, (map_h - 1) / 2
    rover.animate_position((nuovo_x - offset_x, nuovo_y - offset_y, -0.5), duration=0.4, curve=curve.linear)
    
    # IL ROVER SI MUOVE -> IL TEMPO SCORRE (1 turno ogni 2 passi del rover)
    mosse_rover_parziali += 1
    if mosse_rover_parziali >= 2:
        mosse_rover_parziali = 0
        avanza_tempo_globale()
       
    # ====================================================
    # NUOVA LOGICA: INCONTRO FORTUITO DURANTE IL TRAGITTO
    # ====================================================
    vittima_incontrata = False
    
    for c in grid_cells:
        if c.grid_x == nuovo_x and c.grid_y == nuovo_y and getattr(c, 'is_disperso', False):
            # Se ci pestiamo sopra una vittima viva e non ancora salvata
            if not getattr(c, 'morto', False) and not getattr(c, 'salvato', False):
                c.color = color.blue 
                c.text = "OK"
                c.salvato = True # Ferma il countdown!
                vittima_incontrata = True
                print(f"\n[ROVER] INCONTRO FORTUITO! Salvata vittima non programmata in ({nuovo_x}, {nuovo_y})!")
                
                # Se questa vittima era nella coda degli obiettivi futuri, rimuoviamola per non tornarci
                if (nuovo_x, nuovo_y) in coda_obiettivi_rover:
                    coda_obiettivi_rover.remove((nuovo_x, nuovo_y))

    # Se abbiamo curato qualcuno per caso, ci fermiamo 1.5 secondi prima di fare il prossimo passo
    ritardo_prossimo_passo = 1.5 if vittima_incontrata else 0.5
    invoke(esegui_passo_rover, delay=ritardo_prossimo_passo)

def spawna_vittime(quantita=2):
    """Fa comparire un numero specifico di vittime nascoste."""
    for _ in range(quantita):
        if vittime_nascoste:
            # Estrai una vittima a caso tra quelle nascoste
            nuova_vittima = random.choice(vittime_nascoste)
            vittime_nascoste.remove(nuova_vittima)
            vittime_attive.append(nuova_vittima)
            
            # Cambia il colore in rosso per segnalare l'emergenza comparsa
            nuova_vittima.color = color.red
            print(f"[SISTEMA] Nuova emergenza rilevata in ({nuova_vittima.grid_x}, {nuova_vittima.grid_y})!")


# [Sostituisci questa funzione dentro gui.py]

def esegui_piano_volo_drone():
    global mosse_drone_parziali, turni_trascorsi, piano_volo_drone
    
    if not drone: return

    # 1. GENERAZIONE DEL PIANO (State Space Search - BFS/A*)
    if not piano_volo_drone:
        # Scegli un Waypoint casuale sulla mappa
        goal_x = random.randint(0, map_w - 1)
        goal_y = random.randint(0, map_h - 1)
        
        # Definisci il problema per AIMA
        stato_iniziale = (drone.grid_x, drone.grid_y)
        obiettivo = (goal_x, goal_y)
        
        # Se è già sul punto, saltiamo il calcolo
        if stato_iniziale != obiettivo:
            # Creiamo il problema usando la classe importata da drone1.py
            problema_drone = DroneExplorationProblem(stato_iniziale, obiettivo, map_w, map_h)
            
            # Usiamo BFS (Breadth First Search) per trovare il percorso
            nodo_soluzione = breadth_first_graph_search(problema_drone)
            
            if nodo_soluzione:
                # Recuperiamo la lista di azioni, es: ['Up_2', 'Right_1']
                piano_volo_drone = nodo_soluzione.solution() 
                print(f"[NAVIGAZIONE] Nuovo Waypoint: {obiettivo}. Rotta: {piano_volo_drone}")

    # 2. ESECUZIONE DEL PIANO PASSO PER PASSO
    if piano_volo_drone:
        # Estrai la prima mossa dalla lista (es: 'Up_2')
        prossima_mossa = piano_volo_drone.pop(0)
        
        # Analizziamo la stringa per capire direzione e lunghezza
        # prossima_mossa.split('_') divide 'Up_2' in ['Up', '2']
        parti_azione = prossima_mossa.split('_')
        direzione = parti_azione[0]
        passi = int(parti_azione[1]) # Converte '2' in numero intero

        nuovo_x, nuovo_y = drone.grid_x, drone.grid_y
        
        # Applichiamo la logica AIMA corretta (passi variabili)
        if direzione == "Up": nuovo_y += passi
        elif direzione == "Down": nuovo_y -= passi
        elif direzione == "Right": nuovo_x += passi
        elif direzione == "Left": nuovo_x -= passi

        # Eseguiamo lo spostamento logico e grafico
        drone.grid_x, drone.grid_y = nuovo_x, nuovo_y
        
        offset_x, offset_y = (map_w - 1) / 2, (map_h - 1) / 2
        drone.animate_position((nuovo_x - offset_x, nuovo_y - offset_y, -2.5), duration=0.3, curve=curve.linear)

        # --- GESTIONE TURNI, SPAWN E VITA ---
        turni_trascorsi += 1
        if turni_trascorsi == 1: spawna_vittime(2)
        elif turni_trascorsi % 7 == 0: spawna_vittime(1)

        # Il tempo vita scorre solo se il rover è fermo (regola asimmetrica)
        if not rover_in_movimento:
            mosse_drone_parziali += 1
            if mosse_drone_parziali >= 6:
                mosse_drone_parziali = 0
                avanza_tempo_globale() # Abbassa il TTL di tutti i dispersi

        # Dopo ogni mossa, scansioniamo l'area 3x3
        controlla_visione_drone()

    # Richiama se stessa per il prossimo step del piano
    invoke(esegui_piano_volo_drone, delay=0.5)


def controlla_visione_drone():
    """Scansiona un quadrante 3x3 centrato sul drone per rilevare dispersi."""
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            check_x = drone.grid_x + dx
            check_y = drone.grid_y + dy
            
            # Cerca nel database dei dispersi ATTIVI. 
            # NOTA: Usiamo [:] per creare una copia della lista su cui ciclare, 
            # così possiamo fare il .remove() in modo sicuro senza sfasare gli indici!
            for disp in vittime_attive[:]: 
                if disp.grid_x == check_x and disp.grid_y == check_y:
                    
                    # ===================================================
                    # LA TUA CONDIZIONE: IGNORIAMO I SALVATI DAL ROVER
                    # ===================================================
                    if getattr(disp, 'salvato', False):
                        vittime_attive.remove(disp) # Lo togliamo dalla lista attiva per non ricontrollarlo
                        continue # Interrompe questo giro e passa oltre!
                    
                    # Rimuove il disperso dalle emergenze e lo segna come scoperto
                    vittime_attive.remove(disp)
                    vittime_scoperte.append(disp)
                    disp.scoperto = True
                    
                    # Se il tempo globale lo ha già ucciso prima che il drone arrivasse
                    if getattr(disp, 'morto', False):
                        disp.color = color.black
                        disp.text = "X"
                        disp.text_color = color.red
                        print(f"\n[DRONE] Avvistato cadavere in ({check_x}, {check_y}). Troppo tardi.")
                    else:
                        # È vivo! Iniziamo il triage radio
                        disp.color = color.magenta
                        disp.text = str(disp.ttl) # Mostriamo la vita reale rimanente
                        disp.text_color = color.white
                        
                        print(f"\n[DRONE] Avvistato soggetto VIVO in ({check_x}, {check_y})!")
                        
                        # Avviamo il thread dell'LLM
                        thread = threading.Thread(target=chiama_llm_triage, args=(disp, disp.descrizione))
                        thread.start()


def chiama_llm_triage(cella_vittima, descrizione_visiva):
    """
    Usa Llama 3 (via Groq) per generare un report di urgenza in linguaggio naturale.
    """
    print(f"\n[LLM] Connessione a Groq... Generazione dispaccio per la situazione: '{descrizione_visiva}'")
    
    # Abbiamo aggiunto le coordinate reali nel prompt e le regole anti-allucinazione
    prompt_drone = f"""
    Sei l'IA visiva a bordo di un drone di ricognizione. 
    Hai appena scansionato un sopravvissuto alle coordinate X={cella_vittima.grid_x}, Y={cella_vittima.grid_y}. 
    La sua descrizione visiva è: "{descrizione_visiva}".
    
    Il tuo compito è inviare un singolo, breve messaggio radio (massimo 2 frasi) all'IA del Rover di recupero.
    
    Regole TASSATIVE:
    1. Includi SEMPRE le coordinate nel messaggio.
    2. Indica la priorità medica (alta, media o bassa) basandoti ESCLUSIVAMENTE sulla descrizione.
    3. SE la descrizione non descrive ferite o sintomi (es. dice solo "Soggetto 1"), NON INVENTARE NULLA. Dichiara che lo stato è "sconosciuto" e assegna priorità "media" per ispezione.
    4. Non menzionare numeri temporali.
    """

    try:
        risposta = client_llm.chat.completions.create(
            messages=[{"role": "user", "content": prompt_drone}],
            model="llama-3.1-8b-instant"
        )
        
        messaggio_radio = risposta.choices[0].message.content.strip()
        
        print(f"\n📡 [DISPACCIO DRONE-TO-ROVER] Da coord({cella_vittima.grid_x}, {cella_vittima.grid_y}):\n"
              f"«{messaggio_radio}»")
              
        # ==========================================
        # ZONA DI COLLEGAMENTO CON IL ROVER
        # ==========================================
        if rover_agent_instance:
            # 1. Otteniamo gli obiettivi calcolati dal file rover.py
            nuovi_obiettivi = rover_agent_instance.receive_and_execute_mission(messaggio_radio)
            
            # 2. Gestiamo la coda e l'avvio qui, dove le variabili esistono!
            global coda_obiettivi_rover, rover_in_movimento
            
            if nuovi_obiettivi:
                for goal in nuovi_obiettivi:
                    if goal not in coda_obiettivi_rover:
                        coda_obiettivi_rover.append(goal)
                        
                print(f"[SISTEMA] Coda attuale del Rover: {coda_obiettivi_rover}")
                
                # Se il rover è fermo e ci sono obiettivi, parte la missione
                if not rover_in_movimento and coda_obiettivi_rover:
                    calcola_prossimo_percorso_rover()

    except Exception as e:
        print(f"[ERRORE RADIO] Comunicazione fallita: {e}")
# ==========================================
# Funzioni Interattive delle Celle
# ==========================================
def toggle_obstacle_disperso(cell):
    """Alterna lo stato della cella tra 'libera' e 'ostacolo'."""
    if not cell.is_obstacle and not cell.is_disperso:
        cell.color = color.dark_gray
        cell.text = "^"
        cell.is_obstacle = True
    elif cell.is_obstacle:
        cell.color = color.red
        cell.text = "X"
        cell.is_obstacle = False
        cell.is_disperso = True
    else:
        cell.color = color.hex('#7CFC00')  # Verde chiaro per celle libere
        cell.text = ""
        cell.is_disperso = False

# ==========================================
# Logica di Controllo Connettività
# ==========================================
def is_connected(mappa_logica, w, h):
    """
    Usa la ricerca in ampiezza (BFS) per verificare che tutte le 
    celle libere (0) siano raggiungibili tra loro.
    """
    start_node = None
    empty_count = 0
    
    # Trova il numero totale di celle vuote e un punto di partenza
    for x in range(w):
        for y in range(h):
            if mappa_logica[x][y] == 0:
                empty_count += 1
                if start_node is None:
                    start_node = (x, y)
                    
    if empty_count == 0: 
        return True
    
    visited = set([start_node])
    stack = [start_node]
    
    # Espansione a macchia d'olio (Flood fill)
    while stack:
        cx, cy = stack.pop()
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            # Se è dentro i limiti, è vuoto e non è stato visitato
            if 0 <= nx < w and 0 <= ny < h:
                if mappa_logica[nx][ny] == 0 and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    stack.append((nx, ny))
                    
    # Se il numero di celle visitate è uguale al totale delle celle vuote, la mappa è valida
    return len(visited) == empty_count

def genera_ostacoli_casuali():
    """Genera ostacoli in modo casuale senza creare aree irraggiungibili."""
    pulisci_mappa()
    
    totale_celle = map_w * map_h
    # Calcola un numero fisso di ostacoli (es. 25% della mappa)
    num_ostacoli = int(totale_celle * 0.25) 
    
    max_tentativi = 200
    for _ in range(max_tentativi):
        # 0 = Libero, 1 = Ostacolo
        mappa_logica = [[0 for _ in range(map_h)] for _ in range(map_w)]
        ostacoli_piazzati = 0
        
        while ostacoli_piazzati < num_ostacoli:
            rx = random.randint(0, map_w - 1)
            ry = random.randint(0, map_h - 1)
            if mappa_logica[rx][ry] == 0:
                mappa_logica[rx][ry] = 1
                ostacoli_piazzati += 1
                
        # Se la mappa generata è interamente percorribile, applichiamola
        if is_connected(mappa_logica, map_w, map_h):
            for cell in grid_cells:
                x, y = cell.grid_x, cell.grid_y
                if mappa_logica[x][y] == 1:
                    toggle_obstacle_disperso(cell) # Trasforma in ostacolo graficamente
            return
            
    print("Impossibile generare una mappa valida con questa densità in tempi brevi.")

# ==========================================
# Gestione Mappa e Interfaccia
# ==========================================

def genera_dispersi_casuali():
    totale_celle = map_w * map_h
    num_dispersi = int(totale_celle * 0.05)

    for cell in grid_cells:
        if cell.is_disperso:
            cell.is_disperso = False
            cell.color = color.hex('#7CFC00')  # Verde chiaro per celle
            cell.text = ""
    
    celle_libere = [c for c in grid_cells if not c.is_obstacle]
    tot_celle = map_w * map_h
    num_dispersi = max(5, int(tot_celle * 0.05))

    if len(celle_libere) < num_dispersi:
        print("Non ci sono abbastanza celle libere per piazzare i dispersi.")
        return

    celle_scelte = random.sample(celle_libere, num_dispersi)
    for cell in celle_scelte:
        cell.color = color.red
        cell.text = "X"
        cell.is_disperso = True
        cell.is_obstacle = False

def inserimento_descrizioni():
    global dispersi, disperso_corrente_idx, panel_description

    dispersi = [c for c in grid_cells if c.is_disperso]
    descrizione_dispersi.clear()

    if not dispersi:
        print("[ERRORE] Nessun disperso trovato sulla mappa!")
        pannello_controlli.enabled = False
        return
    
    disperso_corrente_idx = 0
    pannello_controlli.enabled = False
    mostra_ui_descrizione()

def mostra_ui_descrizione():
    global panel_description, input_description, input_ttl

    if panel_description:
        destroy(panel_description)
    
    if disperso_corrente_idx >= len(dispersi):
        print("Setup Completato! Avvio Simulazione 3D...")
        inizia_posizionamento_agenti()
        return
    
    cell = dispersi[disperso_corrente_idx]
    cell.color = color.yellow

    input_description = InputField(default_value=f"Soggetto {disperso_corrente_idx+1}")
    input_ttl = InputField(default_value="30", character_limit=3)

    panel_description = WindowPanel(
        title=f'Disperso {disperso_corrente_idx+1}/{len(dispersi)} a ({cell.grid_x}, {cell.grid_y})',
        content=(
            Text(text='Inserisci la descrizione:  \n inserire la situazione del disperso, se ferito o meno'),
            input_description,
            Space(height=1),
            Text(text='Turni di vita stimati (Reali):'),
            input_ttl,
            Space(height=1),
            Button(text='Salva', color=color.green, on_click=salva_descrizione)
        ),
        position=(0, 0.2)
    )
def inizia_posizionamento_agenti():
    global stato_posizionamento, testo_istruzioni

    for cell in grid_cells:
        cell.on_click = Func(seleziona_posizione_agente, cell)
    
    stato_posizionamento = 'DRONE'

    testo_istruzioni = Text(
        text="Fase di deploy: \nClicca su una cella per posizionare il drone",
        origin=(0,0), y=0.4, scale=1.5, color=color.cyan, background=True
    )
def seleziona_posizione_agente(cell):
    global stato_posizionamento, start_drone_pos, start_rover_pos, testo_istruzioni, error_text

    if error_text:
        destroy(error_text)
        error_text = None
    
    if stato_posizionamento == 'DRONE':
        start_drone_pos = (cell.grid_x, cell.grid_y)

        cell.color = color.cyan
        cell.text = "D"

        stato_posizionamento = 'ROVER'
        testo_istruzioni.text = "Fase di deploy: \nClicca su una cella per posizionare il rover\n(Non può essere su una montagna o un disperso!)"
        testo_istruzioni.color = color.orange
    
        return

    elif stato_posizionamento == 'ROVER':
        if cell.is_obstacle or cell.is_disperso:
            error_text = Text(
                text="Il rover non può partire su una montagna!\nScegli una cella libera."
            )
            return
        start_rover_pos = (cell.grid_x, cell.grid_y)
    
    cell.color = color.orange
    cell.text ="R"

    stato_posizionamento = None
    testo_istruzioni.text = "Deploy completato! Avvio simulazione"
    testo_istruzioni.color = color.green

    invoke(avvia_simulazione_3d, delay=0.5)


def salva_descrizione():
    global disperso_corrente_idx
    cell = dispersi[disperso_corrente_idx]
    cell.color = color.red

    cell.descrizione = input_description.text
    try:
        cell.ttl = int(input_ttl.text)
    except ValueError:
        cell.ttl = 30
    
    cell.scoperto = False
    cell.morto = False
    cell.salvato = False

    descrizione_dispersi[(cell.grid_x, cell.grid_y)] = input_description.text

    disperso_corrente_idx +=1
    mostra_ui_descrizione()

def genera_mappa_vuota():
    global map_w, map_h
    try:
        map_w = int(input_longitude.text)
        map_h = int(input_latitude.text)
    except ValueError:
        print("Inserisci numeri validi!")
        return

    map_panel.enabled = False
    pannello_controlli.enabled = True

    offset_x = (map_w - 1) / 2
    offset_y = (map_h - 1) / 2

    # Crea la griglia cliccabile
    for x in range(map_w):
        for y in range(map_h):
            cell = Button(
                parent=scene,
                model='quad',
                color=color.hex('#7CFC00'),
                scale=0.95,
                position=(x - offset_x, y - offset_y, 0),
                grid_x=x,
                grid_y=y
            )
            cell.is_obstacle = False
            cell.is_disperso = False
            # Colleghiamo il click alla funzione toggle
            cell.on_click = Func(toggle_obstacle_disperso, cell) 
            grid_cells.append(cell)

    camera.orthographic = True
    camera.fov = max(map_w, map_h) + 2

def pulisci_mappa():
    """Rimuove tutti gli ostacoli presenti riportando la mappa in stato 'Vuoto'."""
    for cell in grid_cells:
        cell.color = color.hex('#7CFC00')
        cell.text = ""
        cell.is_obstacle = False
        cell.is_disperso = False


def resetta_tutto():
    """Distrugge la griglia e torna al menu iniziale."""
    global grid_cells, error_text
    for cell in grid_cells:
        destroy(cell)
    grid_cells.clear()

    if error_text:
        destroy(error_text)
    

    
    pannello_controlli.enabled = False
    map_panel.enabled = True
    camera.orthographic = False

def conferma_mappa():
    global error_text
    if error_text:
        destroy(error_text)
    
    dispersi_presenti = sum(1 for cell in grid_cells if cell.is_disperso)

    if dispersi_presenti < 3:
        error_text = Text(
            text="Errore: Devi posizionare almeno 3 dispersi sulla mappa!",
            color=color.red, scale=1.2, origin=(0,0), y=-0.4, background=True
        )
        return
    
    # Costruisci la mappa logica per il controllo
    mappa_logica = [[0 for _ in range(map_h)] for _ in range(map_w)]
    for cell in grid_cells:
        if cell.is_obstacle:
            mappa_logica[cell.grid_x][cell.grid_y] = 1

    # Controllo che non ci siano aree bloccate o isolate
    if not is_connected(mappa_logica, map_w, map_h):
        error_text = Text(
            text="ERRORE: La mappa contiene aree inaccessibili!\nRimuovi alcuni ostacoli e riprova.",
            color=color.red, scale=1.2, origin=(0, 0), y=-0.4, background=True
        )
        return

    print("Connessione mappa verificata!")
    inserimento_descrizioni()
    #map_panel.enabled = False
    #pannello_controlli.enabled = False
    #panel_description.enabled = False
# ==========================================
# Pannelli UI
# ==========================================
window.color = color.rgb(40, 40, 40) # Colore di sfondo leggermente più neutro

textlong = Text(text="Larghezza (Celle): ")
input_longitude = InputField(default_value="7")
textlat = Text(text="Altezza (Celle): ")
input_latitude = InputField(default_value="7")

map_panel = WindowPanel(
    title='Setup Mappa',
    content=(
        textlong, input_longitude,
        textlat, input_latitude,
        Space(height=1),
        Button(text='Genera Mappa Vuota', color=color.azure, on_click=genera_mappa_vuota)
    ),
    position=(0, 0.25)
)

pannello_controlli = WindowPanel(
    title='Controlli Mappa',
    content=(
        Button(text='Genera Ostacoli Casuali', color=color.azure, on_click=genera_ostacoli_casuali),
        Button(text='Svuota Mappa', color=color.gray, on_click=pulisci_mappa),
        Button(text='Genera Dispersi Casuali', color=color.cyan, on_click=genera_dispersi_casuali),
        Button(text='Conferma Mappa', color=color.green, on_click=conferma_mappa),
        Button(text='Torna al Menu', color=color.orange, on_click=resetta_tutto)
    ),
    position=(0.7, 0.4),
    enabled=False
)

app.run()
