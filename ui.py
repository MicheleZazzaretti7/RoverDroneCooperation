from ursina import *
import state
from map_manager import toggle_obstacle_disperso, is_connected
import drone
import rover

def genera_mappa_vuota():
    try:
        state.map_w = int(state.input_longitude.text)
        state.map_h = int(state.input_latitude.text)
    except ValueError:
        print("Inserisci numeri validi!")
        return

    state.map_panel.enabled = False
    state.pannello_controlli.enabled = True

    offset_x = (state.map_w - 1) / 2
    offset_y = (state.map_h - 1) / 2

    for x in range(state.map_w):
        for y in range(state.map_h):
            cell = Button(
                parent=scene,
                model='quad',
                color=color.hex('#7CFC00'),
                scale=0.95,
                position=(x - offset_x, y - offset_y, 0),
            )
            cell.grid_x = x
            cell.grid_y = y
            cell.is_obstacle = False
            cell.is_disperso = False
            cell.is_ospedale = False
            cell.on_click = Func(toggle_obstacle_disperso, cell) 
            state.grid_cells.append(cell)

    camera.orthographic = True
    camera.fov = max(state.map_w, state.map_h) + 2

def resetta_tutto():
    for cell in state.grid_cells:
        destroy(cell)
    state.grid_cells.clear()

    if state.error_text:
        destroy(state.error_text)
    
    state.pannello_controlli.enabled = False
    state.map_panel.enabled = True
    camera.orthographic = False

def conferma_mappa():
    if state.error_text:
        destroy(state.error_text)
    
    dispersi_presenti = sum(1 for cell in state.grid_cells if getattr(cell, 'is_disperso', False))

    if dispersi_presenti < 3:
        state.error_text = Text(
            text="Errore: Devi posizionare almeno 3 dispersi sulla mappa!",
            color=color.red, scale=1.2, origin=(0,0), y=-0.4, background=True
        )
        return
    
    mappa_logica = [[0 for _ in range(state.map_h)] for _ in range(state.map_w)]
    for cell in state.grid_cells:
        if getattr(cell, 'is_obstacle', False):
            mappa_logica[cell.grid_x][cell.grid_y] = 1

    if not is_connected(mappa_logica, state.map_w, state.map_h):
        state.error_text = Text(
            text="ERRORE: La mappa contiene aree inaccessibili!\nRimuovi alcuni ostacoli e riprova.",
            color=color.red, scale=1.2, origin=(0, 0), y=-0.4, background=True
        )
        return

    print("Connessione mappa verificata!")
    inserimento_descrizioni()

def inserimento_descrizioni():
    state.dispersi = [c for c in state.grid_cells if getattr(c, 'is_disperso', False)]
    state.descrizione_dispersi.clear()

    if not state.dispersi:
        print("[DEBUG] Lista dispersi vuota all'inserimento.")
        state.pannello_controlli.enabled = False
        return
    
    state.disperso_corrente_idx = 0
    state.pannello_controlli.enabled = False
    mostra_ui_descrizione()

def mostra_ui_descrizione():
    if state.panel_description:
        destroy(state.panel_description)
    
    if state.disperso_corrente_idx >= len(state.dispersi):
        print("Setup Completato! Avvio Simulazione 3D...")
        inizia_posizionamento_agenti_ospedale()
        return
    
    cell = state.dispersi[state.disperso_corrente_idx]
    cell.color = color.yellow

    state.input_description = InputField(
        default_value=f"Soggetto {state.disperso_corrente_idx+1}",
        character_limit=150,
        max_lines=10,
        scale=(0.8, 0.12)
    )

    tf = state.input_description.text_field
    old_text_scale = tf.text_entity.world_scale_x        # valore PRIMA che WindowPanel lo tocchi
    old_cursor_scale_x = tf.cursor_parent.world_scale_x
    old_cursor_scale_y = tf.cursor_parent.world_scale_y
    
    state.input_ttl = InputField(
        default_value="30",
        character_limit=2
    )


    state.panel_description = WindowPanel(
        title=f'Disperso {state.disperso_corrente_idx+1}/{len(state.dispersi)} a ({cell.grid_x}, {cell.grid_y})',
        position=(0, 0.2),
        content=(
            Text(text='Indica situazione, ferite e stato del disperso.', scale=0.9),
            state.input_description,
            Space(height=0.70),
            Text(text='Turni di vita stimati (Reali):'),
            state.input_ttl,
            Button(text='Salva Descrizione', color=color.green, on_click=salva_descrizione)
        )
    )
    extra=1.1
    state.input_description.scale_y=1+extra
    state.input_description.text_field.text_entity.world_scale = Vec3(20,20,1)
    

    new_text_scale = tf.text_entity.world_scale_x  # ora è 20
    ratio = new_text_scale / old_text_scale

    tf.cursor_parent.world_scale_x = old_cursor_scale_x * ratio
    tf.cursor_parent.world_scale_y = old_cursor_scale_y * ratio

    for element in state.panel_description.content[2:]:
        if hasattr(element, 'y'):
            element.y -= extra
    state.panel_description.panel.scale_y += extra

    
    state.abilita_wordwrap(state.input_description, larghezza=27)



def salva_descrizione():
    cell = state.dispersi[state.disperso_corrente_idx]
    cell.color = color.red
    cell.descrizione = state.input_description.text
    
    try:
        cell.ttl = int(state.input_ttl.text)
    except ValueError:
        cell.ttl = 30
    
    cell.scoperto = False
    cell.morto = False
    cell.salvato = False

    state.descrizione_dispersi[(cell.grid_x, cell.grid_y)] = state.input_description.text
    state.disperso_corrente_idx += 1
    mostra_ui_descrizione()

def inizia_posizionamento_agenti_ospedale():
    for cell in state.grid_cells:
        cell.on_click = Func(seleziona_posizione_agente_ospedale, cell)
    
    state.stato_posizionamento = 'DRONE'

    state.testo_istruzioni = Text(
        text="Fase di deploy: \nClicca su una cella per posizionare il drone",
        origin=(0,0), y=0.4, scale=1.5, color=color.cyan, background=True
    )

def seleziona_posizione_agente_ospedale(cell):
    if state.error_text:
        destroy(state.error_text)
        state.error_text = None
    
    if state.stato_posizionamento == 'DRONE':
        state.start_drone_pos = (cell.grid_x, cell.grid_y)
        #cell.color = color.cyan
        cell.text = "D"

        state.stato_posizionamento = 'ROVER'
        state.testo_istruzioni.text = "Fase di deploy: \nClicca su una cella per posizionare il rover\n(Non può essere su una montagna o un disperso!)"
        state.testo_istruzioni.color = color.orange
        return

    elif state.stato_posizionamento == 'ROVER':
        if getattr(cell, 'is_obstacle', False) or getattr(cell, 'is_disperso', False):
            state.error_text = Text(
                text="Il rover non può partire su una montagna o un disperso!\nScegli una cella libera.",
                color=color.red, scale=1.2, origin=(0, 0), y=-0.4, background=True
            )
            return
        
        state.start_rover_pos = (cell.grid_x, cell.grid_y)
        cell.text ="R"
        cell.color = color.orange

        state.stato_posizionamento = 'OSPEDALE'
        state.testo_istruzioni.text = "Posiziona ora l'ospedale:\n Il luogo dove verranno portati i dispersi una volta curati\n(Non può essere su una montagna o un disperso)"
        state.testo_istruzioni.color = color.green
        return
    

    elif state.stato_posizionamento == 'OSPEDALE':
        if getattr(cell, 'is_obstacle', False) or getattr(cell, 'is_disperso', False):
            state.error_text = Text(
                text="L'ospedale non può essere posizionato su una montagna o un disperso!\nScegli una cella libera.",
                color=color.red, scale=1.2, origin=(0, 0), y=-0.4, background=True
            )
            return
        state.ospedale_posizione = (cell.grid_x, cell.grid_y)
        cell.is_ospedale = True

    cell.color = color.white
    cell.texture="hospital.png"
    state.stato_posizionamento = None
    state.testo_istruzioni.text = "Deploy e posizionamento completato! Avvio simulazione"
    state.testo_istruzioni.color = color.green

    invoke(avvia_simulazione_3d, delay=0.5)



def avvia_simulazione_3d():
    if state.testo_istruzioni:
        destroy(state.testo_istruzioni)
    
    if state.pannello_controlli: state.pannello_controlli.enabled = False
    if state.map_panel: state.map_panel.enabled = False

    for cell in state.grid_cells:
        cell.on_click = lambda: None
        cell.collider = None

        if getattr(cell, 'text_entity', None):
            cell.text_entity.disable()

        cell.model = 'cube'
        cell.texture = 'montagna.jpg'
        cell.scale_z = 0.2
        cell.z = 0
        Entity(parent=cell, model='cube', color=color.black, wireframe=True, scale=1.05)

        if getattr(cell, 'is_obstacle', False):
            montagna = Entity(
                parent=scene,
                model=Cone(resolution=4),
                texture='montagna.jpg',
                scale=(0.7, 1.3, 0.7),
                position=(cell.x, cell.y, -0.50),
                rotation=(-90,0,0)
            )
            Entity(parent=montagna, model=Cone(resolution=4), color=color.black, wireframe=True, scale=1.05)
        elif getattr(cell, 'is_disperso', False):
            cell.color = color.hex('#7CFC00')
            cell.texture = 'grass.jpg'
            state.vittime_nascoste.append(cell)
        
        elif getattr(cell, 'is_ospedale', False):
            cell.color=color.white
            cell.texture= 'hospital.png'
        
        else:
            cell.color = color.hex('#7CFC00')
            cell.texture = 'grass.jpg'

    camera.orthographic = False
    EditorCamera()
    
    offset_x = (state.map_w - 1) / 2
    offset_y = (state.map_h - 1) / 2
    
    start_drone_x, start_drone_y = state.start_drone_pos
    start_rover_x, start_rover_y = state.start_rover_pos
    
    real_drone_x = start_drone_x - offset_x
    real_drone_y = start_drone_y - offset_y
    real_rover_x = start_rover_x - offset_x
    real_rover_y = start_rover_y - offset_y
    
    # Istanziazione Agenti
    state.drone = Entity(model='craft_speederA.obj', color=color.cyan, texture='metallo.jpg', scale=0.6, position=(real_drone_x, real_drone_y, -2.5), rotation=(-90, 0, 0))
    state.drone.grid_x = start_drone_x
    state.drone.grid_y = start_drone_y
    
    state.rover = Entity(model='craft_miner.obj', color=color.orange, texture='metallo.jpg', scale=0.5, position=(real_rover_x, real_rover_y, -0.5), rotation=(-90, 0, 0))
    state.rover.grid_x = start_rover_x
    state.rover.grid_y = start_rover_y

    state.rover_agent_instance = rover.RoverAgent((start_rover_x, start_rover_y))

    sfondo_console = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba(0, 0, 0, 200),  # Nero con opacità
        scale=(0.45, 0.45),              # Larghezza, Altezza
        position=(-0.60, 0.25),         # Posizionato in alto a sinistra
        z=1
    )
    
    # 2. Titolo fisso della console
    Text(
        parent=camera.ui,
        text="[ CONSOLE DI SISTEMA ]",
        color=color.cyan,
        scale=1.1,
        origin=(0, 0),
        position=(-0.60, 0.45) # Centrato rispetto allo sfondo
    )

    # 3. Il testo dinamico vero e proprio
    testo_log_interno = Text(
        parent=camera.ui,
        text="",
        scale=0.9,
        color=color.yellow,
        origin=(-0.5, 0.5),      # Allineato in alto a sinistra
        position=(-0.85, 0.42)   # Posizionato dentro lo sfondo scuro
    )
    
    # Salviamo l'entità di testo nello stato
    state.pannello_log_testo = testo_log_interno
    
    # Inviamo il primo messaggio!
    print("[SISTEMA] Avvio simulazione 3D...")

    
    invoke(drone.esegui_piano_volo_drone, delay=1.0)

