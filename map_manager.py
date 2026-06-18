from ursina import color
import random
import state

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
    
    #controlla che tutte le celle vuote siano raggiungibili
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


def genera_ostacoli_casuali():
    """Genera ostacoli in modo casuale senza creare aree irraggiungibili."""
    pulisci_mappa()
    
    totale_celle = state.map_w * state.map_h
    # Calcola un numero fisso di ostacoli (es. 25% della mappa)
    num_ostacoli = int(totale_celle * 0.25) 
    
    max_tentativi = 200
    for _ in range(max_tentativi):
        # 0 = Libero, 1 = Ostacolo
        mappa_logica = [[0 for _ in range(state.map_h)] for _ in range(state.map_w)]
        ostacoli_piazzati = 0
        
        while ostacoli_piazzati < num_ostacoli:
            rx = random.randint(0, state.map_w - 1)
            ry = random.randint(0, state.map_h - 1)
            if mappa_logica[rx][ry] == 0:
                mappa_logica[rx][ry] = 1
                ostacoli_piazzati += 1
                
        # Se la mappa generata è interamente percorribile, applichiamola
        if is_connected(mappa_logica, state.map_w, state.map_h):
            for cell in state.grid_cells:
                x, y = cell.grid_x, cell.grid_y
                if mappa_logica[x][y] == 1:
                    toggle_obstacle_disperso(cell) # Trasforma in ostacolo graficamente
            return
            
    print("Impossibile generare una mappa valida con questa densità in tempi brevi.")

# ==========================================
# Gestione Mappa e Interfaccia
# ==========================================

def genera_dispersi_casuali():
    totale_celle = state.map_w * state.map_h
    num_dispersi = int(totale_celle * 0.05)

    for cell in state.grid_cells:
        if cell.is_disperso:
            cell.is_disperso = False
            cell.color = color.hex('#7CFC00')  # Verde chiaro per celle
            cell.text = ""
    
    celle_libere = [c for c in state.grid_cells if not c.is_obstacle]
    tot_celle = state.map_w * state.map_h
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

def pulisci_mappa():
    """Rimuove tutti gli ostacoli presenti riportando la mappa in stato 'Vuoto'."""
    for cell in state.grid_cells:
        cell.color = color.hex('#7CFC00')
        cell.text = ""
        cell.is_obstacle = False
        cell.is_disperso = False


