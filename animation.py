from ursina import *
import random

app = Ursina(title="Maze Generator - Setup Entita")

# Variabili globali
grid_cells = []
maze_data = [] 

# Variabili per lo stato del gioco
click_mode = '0' # Può essere: 'agent1', 'agent2', 'goal'
node_agent1 = None
node_agent2 = None
node_goal = None

# ==========================================
# UI Iniziale (Dimensioni)
# ==========================================
textlong = Text(text="Larghezza (Stanze): ")
input_longitude = InputField(default_value="5")
textlat = Text(text="Altezza (Stanze): ")
input_latitude = InputField(default_value="5")

def resetta_tutto():
    """Distrugge il labirinto e torna al menu iniziale."""
    global grid_cells, maze_data, node_agent1, node_agent2, node_goal
    for cell in grid_cells:
        destroy(cell)
    grid_cells.clear()
    maze_data.clear()
    
    node_agent1 = None
    node_agent2 = None
    node_goal = None
    
    pannello_posizioni.enabled = False
    map_panel.enabled = True
    camera.orthographic = False

# ==========================================
# Logica di Posizionamento (Click)
# ==========================================
def imposta_modalita(nuova_modalita):
    global click_mode
    click_mode = nuova_modalita
    print(f"Modalità click: {click_mode}")

def gestisci_click_cella(cella):
    global node_agent1, node_agent2, node_goal


    if click_mode== '0':
        return # Modalità di default, non fare nulla
    
    # Rimuove il colore dal nodo precedente e lo resetta
    if click_mode == 'agent1':
        if node_agent1: 
            node_agent1.color = color.white
            node_agent1.text = ""
        cella.color = color.green
        cella.text = "A1"
        node_agent1 = cella
        
    elif click_mode == 'agent2':
        if node_agent2: 
            node_agent2.color = color.white
            node_agent2.text = ""
        cella.color = color.cyan
        cella.text = "A2"
        node_agent2 = cella
        
    elif click_mode == 'goal':
        if node_goal: 
            node_goal.color = color.white
            node_goal.text = ""
        cella.color = color.red
        cella.text = "G"
        node_goal = cella

def conferma_setup():
    """Controlla che tutto sia piazzato e avvia la fase successiva."""
    if not node_agent1 or not node_agent2 or not node_goal:
        print("Errore: Devi piazzare entrambi gli agenti e l'uscita!")
        return
        
    print(f"Setup completato! \nAgent1: ({node_agent1.grid_x}, {node_agent1.grid_y}) \nAgent2: ({node_agent2.grid_x}, {node_agent2.grid_y}) \nGoal: ({node_goal.grid_x}, {node_goal.grid_y})")
    imposta_modalita('0')
    pannello_posizioni.enabled = False
    Text(text="Setup Completato!\nInizio Esplorazione...", origin=(0,0), scale=2, color=color.green, y=0.4)
    
    # Qui, in futuro, inizializzeremo la tua classe Environment e Agent di AIMA!

# ==========================================
# Algoritmo e Generazione Labirinto
# ==========================================
def genera_labirinto():
    global maze_data, node_agent1, node_agent2, node_goal
    
    # Reset delle posizioni se si rigenera
    node_agent1 = node_agent2 = node_goal = None
    
    try:
        w_stanze = int(input_longitude.text)
        h_stanze = int(input_latitude.text)
    except ValueError:
        print("Inserisci numeri validi!")
        return

    map_panel.enabled = False
    pannello_posizioni.enabled = True # Mostra il menu per piazzare gli agenti

    w = w_stanze * 2 + 1
    h = h_stanze * 2 + 1
    maze_data = [[1 for y in range(h)] for x in range(w)]

    stack = [(1, 1)]
    maze_data[1][1] = 0

    while stack:
        cx, cy = stack[-1]
        vicini_non_visitati = []

        for dx, dy in [(0, 2), (0, -2), (2, 0), (-2, 0)]:
            nx, ny = cx + dx, cy + dy
            if 0 < nx < w and 0 < ny < h and maze_data[nx][ny] == 1:
                vicini_non_visitati.append((nx, ny))

        if vicini_non_visitati:
            nx, ny = random.choice(vicini_non_visitati)
            muro_x = (cx + nx) // 2
            muro_y = (cy + ny) // 2
            maze_data[muro_x][muro_y] = 0
            maze_data[nx][ny] = 0
            stack.append((nx, ny))
        else:
            stack.pop()

    offset_x = (w - 1) / 2
    offset_y = (h - 1) / 2

    for x in range(w):
        for y in range(h):
            is_wall = (maze_data[x][y] == 1)
            
            cell = Button(
                parent=scene,
                model='quad',
                color=color.dark_gray if is_wall else color.white,
                scale=0.95,
                position=(x - offset_x, y - offset_y, 0),
                is_wall=is_wall,
                grid_x=x,
                grid_y=y
            )
            
            if is_wall:
                cell.disabled = True # I muri NON possono essere cliccati
            else:
                # Se è un percorso, assegniamo la funzione di click
                cell.on_click = Func(gestisci_click_cella, cell)
                
            grid_cells.append(cell)

    camera.orthographic = True
    camera.fov = max(w, h) + 2

# ==========================================
# Pannelli UI
# ==========================================
map_panel = WindowPanel(
    title='Setup Labirinto',
    content=(
        textlong, input_longitude,
        textlat, input_latitude,
        Space(height=1),
        Button(text='Genera Labirinto', color=color.azure, on_click=genera_labirinto)
    ),
    position=(0, 0.25)
)

pannello_posizioni = WindowPanel(
    title='Piazza le Entità',
    content=(
        Text("Clicca sulla mappa per posizionare:"),
        Button(text='Agente 1 (Verde)', color=color.green, on_click=lambda: imposta_modalita('agent1')),
        Button(text='Agente 2 (Azzurro)', color=color.cyan, on_click=lambda: imposta_modalita('agent2')),
        Button(text='Uscita (Rosso)', color=color.red, on_click=lambda: imposta_modalita('goal')),
        Space(height=1),
        Button(text='Conferma Setup', color=color.azure, on_click=conferma_setup),
        Button(text='Rigenera Labirinto', color=color.gray, on_click=lambda: [resetta_tutto(), genera_labirinto()])
    ),
    position=(0.7, 0.4),
    enabled=False
)

app.run()
