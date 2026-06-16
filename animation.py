from ursina import *
import random
import threading
import time

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

# ==========================================
# Variabili per gli Agenti
# ==========================================
drone = None
rover = None
pyramid = Cone(resolution=4)
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
        cell.scale_z = 0.2
        cell.z = 0
        Entity(parent=cell, model='cube', color=color.black, wireframe=True, scale=1.05)


        if cell.is_obstacle:
            montagna = Entity(
                parent=scene,
                model=Cone(resolution=4),
                color=color.dark_gray,
                scale=(0.7, 1.3, 0.7),
                position=(cell.x, cell.y, -0.50),
                rotation=(-90,0,0)
            )

            Entity(parent=montagna, model=Cone(resolution=4), color=color.black, wireframe=True, scale=1.05)
        elif cell.is_disperso:
            # Nascondiamo i dispersi facendoli sembrare erba normale
            cell.color = color.hex('#7CFC00')
            cell.ttl = None  # Time To Live (Turni prima della "morte")
            vittime_nascoste.append(cell)
        else:
            cell.color = color.hex('#7CFC00')
          

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
    drone = Entity(model='sphere', color=color.cyan, scale=0.6, position=(real_drone_x, real_drone_y, -2.5))
    drone.grid_x = start_drone_x
    drone.grid_y = start_drone_y
    
    rover = Entity(model='cube', color=color.orange, scale=0.7, position=(real_rover_x, real_rover_y, -0.5))
    rover.grid_x = start_rover_x
    rover.grid_y = start_rover_y
    
    # 5. Avvia il comportamento del drone dopo 1 secondo di pausa
    invoke(muovi_drone_random, delay=1.0)

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

def aggiorna_timer_vittime():
    """Scala il TTL (Time To Live) delle vittime scoperte ad ogni turno."""
    for vittima in vittime_scoperte:
        if vittima.ttl is not None and vittima.ttl > 0:
            vittima.ttl -= 1
            # Aggiorna il testo sulla cella per far vedere il countdown
            if vittima.text_entity:
                vittima.text_entity.enable()
                vittima.text = str(vittima.ttl)
                vittima.text_color = color.white
            
            if vittima.ttl <= 0:
                print(f"[CRITICO] Il soggetto in ({vittima.grid_x}, {vittima.grid_y}) non ce l'ha fatta.")
                vittima.color = color.black
                vittima.text = "X"
                vittima.text_color = color.red

def muovi_drone_random():
    """Muove il drone di una cella adiacente in modo casuale, ignorando gli ostacoli."""
    if not drone: return
    
    mosse_possibili = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    dx, dy = random.choice(mosse_possibili)
    
    nuovo_x, nuovo_y= drone.grid_x + dx, drone.grid_y + dy
    
    # Verifica che il drone non esca dai confini della mappa
    if 0 <= nuovo_x < map_w and 0 <= nuovo_y < map_h:
        drone.grid_x = nuovo_x
        drone.grid_y = nuovo_y
        
        offset_x, offset_y = (map_w - 1) / 2, (map_h - 1) / 2
        
        
        # Ursina anima il passaggio da A a B fluidamente
        drone.animate_position((nuovo_x - offset_x, nuovo_y - offset_y, -2.5), duration=0.3, curve=curve.linear)
        
        turni_trascorsi +=1

        if turni_trascorsi ==1:
            spawna_vittime(2)

        elif turni_trascorsi % 7 == 0:
            spawna_vittime(1)
        
        aggiorna_timer_vittime()

        # Dopo lo spostamento, il drone scansiona il terreno sotto di lui
        controlla_visione_drone()
        
    # Richiama se stessa dopo 0.5 secondi creando un loop infinito senza bloccare il gioco
    invoke(muovi_drone_random, delay=0.5)

def controlla_visione_drone():
    """Scansiona un quadrante 3x3 centrato sul drone per rilevare dispersi."""
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            check_x = drone.grid_x + dx
            check_y = drone.grid_y + dy
            
            # Cerca nel database dei dispersi
            for disp in vittime_attive:
                # Se la cella coincide e non è stata già "scoperta" (evita spam)
                if disp.grid_x == check_x and disp.grid_y == check_y:

                    vittime_attive.remove(disp)
                    vittime_scoperte.append(disp)

                    descrizione = descrizione_dispersi[(check_x, check_y)]
                    print(f"\n[DRONE] Avvistato soggetto in ({check_x}, {check_y})!")
                    disp.color = color.magenta

                    thread = threading.Thread(target=chiama_llm_asincrono, args=(disp, descrizione))
                    thread.start()

                    
                    # --------------------------------------------------------
                    # QUI IN FUTURO INSERIREMO IL THREAD PER LA CHIAMATA LLM
                    # --------------------------------------------------------


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
    num_dispersi = int(totale_celle * 0.03)

    for cell in grid_cells:
        if cell.is_disperso:
            cell.is_disperso = False
            cell.color = color.hex('#7CFC00')  # Verde chiaro per celle
            cell.text = ""
    
    celle_libere = [c for c in grid_cells if not c.is_obstacle]
    tot_celle = map_w * map_h
    num_dispersi = max(3, int(tot_celle * 0.03))

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
        print("sborra ingoiata")
        pannello_controlli.enabled = False
        return
    
    disperso_corrente_idx = 0
    pannello_controlli.enabled = False
    mostra_ui_descrizione()

def mostra_ui_descrizione():
    global panel_description, input_description

    if panel_description:
        destroy(panel_description)
    
    if disperso_corrente_idx >= len(dispersi):
        print("Setup Completato! Avvio Simulazione 3D...")
        inizia_posizionamento_agenti()
        return
    
    cell = dispersi[disperso_corrente_idx]
    cell.color = color.yellow

    input_description = InputField(default_value=f"Soggetto {disperso_corrente_idx+1}")

    panel_description = WindowPanel(
        title=f'Disperso {disperso_corrente_idx+1}/{len(dispersi)} a ({cell.grid_x}, {cell.grid_y})',
        content=(
            Text(text='Inserisci la descrizione:  \n inserire la situazione del disperso, se ferito o meno'),
            input_description,
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
