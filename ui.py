from ursina import *
import state
from map_manager import toggle_obstacle_disperso, is_connected
import drone
import rover
IMAGES_PATH=("models/")

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


    # TEST PER VERIFICARE CHE IL DRONE VEDA ANCHE NEL CASO IN CUI SIA IRRAGGIUNGIBILE
    if not is_connected(mappa_logica, state.map_w, state.map_h):
        state.error_text = Text(
            text="ERRORE: La mappa contiene aree inaccessibili!\nRimuovi alcuni ostacoli e riprova.",
            color=color.red, scale=1.2, origin=(0, 0), y=-0.4, background=True
        )
        return

    print("Connessione mappa verificata!")
    inserimento_descrizioni()

def inserimento_descrizioni():
    for cell in state.grid_cells:
        cell.on_click = lambda: None
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
        character_limit=170,
        max_lines=10,
        scale=(0.8, 0.12)
    )

    tf = state.input_description.text_field
    old_text_scale = tf.text_entity.world_scale_x
    old_cursor_scale_x = tf.cursor_parent.world_scale_x
    old_cursor_scale_y = tf.cursor_parent.world_scale_y
    
    state.input_ttl = InputField(
        default_value="30",
        character_limit=3
    )
    state.input_description.color = color.clear


    state.panel_description = WindowPanel(
        title=f'Disperso {state.disperso_corrente_idx+1}/{len(state.dispersi)} a ({cell.grid_x}, {cell.grid_y})',
        position=(0, 0.2),
        content=(
            Text(text='Indica situazione, ferite e stato del disperso.', scale=0.8),
            state.input_description,
            Space(height=0.80),
            Text(text='Turni di vita stimati (Reali):'),
            state.input_ttl,
            Button(text='Salva Descrizione', color=color.green, on_click=salva_descrizione)
        )
    )
    extra=1.2
    state.input_description.scale_y=1+extra
    state.input_description.text_field.text_entity.world_scale = Vec3(20,20,1)
    

    new_text_scale = tf.text_entity.world_scale_x  # ora è 20
    ratio = new_text_scale / old_text_scale

    tf.cursor_parent.world_scale_x = old_cursor_scale_x * ratio
    tf.cursor_parent.world_scale_y = old_cursor_scale_y * ratio
    for element in state.panel_description.content[:1]:
        if hasattr(element, 'y'):
            element.y += 0.6
    
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
    cell.texture=f"{IMAGES_PATH}hospital.png"
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
        cell.texture = f'{IMAGES_PATH}montagna.jpg'
        cell.scale_z = 0.2
        cell.z = 0
        Entity(parent=cell, model='cube', color=color.black, wireframe=True, scale=1.05)

        if getattr(cell, 'is_obstacle', False):
            montagna = Entity(
                parent=scene,
                model=Cone(resolution=4),
                texture=f'{IMAGES_PATH}montagna.jpg',
                scale=(0.7, 1.3, 0.7),
                position=(cell.x, cell.y, -0.50),
                rotation=(-90,0,0)
            )
            Entity(parent=montagna, model=Cone(resolution=4), color=color.black, wireframe=True, scale=1.05)
        elif getattr(cell, 'is_disperso', False):
            cell.color = color.hex('#7CFC00')
            cell.texture = f'{IMAGES_PATH}grass.jpg'
            state.vittime_nascoste.append(cell)
        
        elif getattr(cell, 'is_ospedale', False):
            cell.color=color.white
            cell.texture= f'{IMAGES_PATH}hospital.png'
        
        else:
            cell.color = color.hex('#7CFC00')
            cell.texture = f'{IMAGES_PATH}grass.jpg'

    camera.orthographic = False
    camera_editor =EditorCamera()
    camera_editor.position=(-2.5,0,-100)
    
    offset_x = (state.map_w - 1) / 2
    offset_y = (state.map_h - 1) / 2

    for x in range(state.map_w):
        real_x = x -offset_x
        real_y_bottom = -0.7 -offset_y
        Text(
            text=str(x),
            position=(real_x, real_y_bottom, -0.5),
            scale=15,
            color=color.black,
            origin=(0,0),
            parent=scene
        )
    
    for y in range(state.map_h):
        real_y = y -offset_y
        real_x_left = -0.7-offset_x
        Text(
            text=str(y),
            position=(real_x_left, real_y, -0.5),
            scale=15,
            color=color.black,
            origin=(0,0),
            parent=scene
        )
    
    start_drone_x, start_drone_y = state.start_drone_pos
    start_rover_x, start_rover_y = state.start_rover_pos
    
    real_drone_x = start_drone_x - offset_x
    real_drone_y = start_drone_y - offset_y
    real_rover_x = start_rover_x - offset_x
    real_rover_y = start_rover_y - offset_y
    
    # Istanziazione Agenti

    state.drone = Entity(model=f'{IMAGES_PATH}craft_speederA.obj', color=color.cyan, texture=f'{IMAGES_PATH}metallo.jpg', scale=0.5, position=(real_drone_x, real_drone_y, -2.5), rotation=(-90, 0, 0))
    state.drone.grid_x = start_drone_x
    state.drone.grid_y = start_drone_y
    
    state.rover = Entity(model=f'{IMAGES_PATH}craft_miner.obj', color=color.orange, texture=f'{IMAGES_PATH}metallo.jpg', scale=0.4, position=(real_rover_x, real_rover_y, -0.5), rotation=(-90, 0, 0))
    state.rover.grid_x = start_rover_x
    state.rover.grid_y = start_rover_y

    state.rover_agent_instance = rover.RoverAgent((start_rover_x, start_rover_y))

    sfondo_console = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba(0, 0, 0, 200),  # Nero con opacità
        scale=(0.55, 0.80),              # Larghezza, Altezza
        position=(-0.55, 0.25),         # Posizionato in alto a sinistra
        z=1,
        collider='box'
    )
    
    # 2. Titolo fisso della console
    Text(
        parent=camera.ui,
        text="[ CONSOLE DI SISTEMA ]",
        color=color.cyan,
        scale=1.1,
        origin=(0, 0),
        position=(-0.55, 0.45) # Centrato rispetto allo sfondo
    )

    # 3. Il testo dinamico vero e proprio
    testo_log_interno = Text(
        parent=camera.ui,
        text="",
        scale=(0.9, 1.5),
        origin=(-0.5, 0.5),      # Allineato in alto a sinistra
        position=(-0.80, 0.42)   # Posizionato dentro lo sfondo scuro
    )
    
    # Salviamo l'entità di testo nello stato
    state.pannello_log_testo = testo_log_interno

    # 4. Creazione della Scrollbar (Slider verticale)
    def on_slider_changed():
        max_scroll = max(0, len(state.registro_log_completo) - state.max_righe_console)
        if max_scroll > 0:
            # Gli slider verticali Ursina hanno lo 0 in basso e il max in alto.
            # Invertiamo il valore in modo che lo 0 (in basso) mostri i log più recenti (max_scroll).
            nuovo_offset = int(max_scroll - state.slider_console.value)
            state.scroll_offset_console = nuovo_offset
            
            # Se l'utente scorre in alto per rileggere la cronologia, disattiviamo l'autoscroll
            state.auto_scroll_console = (nuovo_offset == max_scroll)
            state.aggiorna_vista_console()

    state.slider_console = Slider(
        parent=camera.ui,
        min=0, max=0, default=0,
        step=1,
        dynamic=True,
        orientation='vertical',
        position=(-0.26, 0.05), # Fissato sul bordo destro dello sfondo della console
        scale=(0.04, 0.75),
        on_value_changed=on_slider_changed
    )
    state.slider_console.knob.color = color.light_gray
    state.slider_console.bg.color = color.dark_gray

    elementi_console = [
        sfondo_console, 
        state.slider_console, 
        getattr(state.slider_console, 'bg', None), 
        getattr(state.slider_console, 'knob', None)
    ]

    # 4. Modifichiamo l'input per scorrere la console SOLO se il mouse è sopra di essa
    def scroll_mouse(key):
        if mouse.hovered_entity in elementi_console:
            if key == 'scroll up':
                state.slider_console.value = min(state.slider_console.max, state.slider_console.value + 1)
            elif key == 'scroll down':
                state.slider_console.value = max(0, state.slider_console.value - 1)
                

    state.slider_console.input = scroll_mouse

        # 5. Blocchiamo i comandi dell'EditorCamera se il mouse è sulla console
    def blocca_zoom_camera():
        if mouse.hovered_entity in elementi_console:
            camera_editor.ignore = True  # Disabilita zoom e rotazione della mappa
        else:
            camera_editor.ignore = False # Riabilita i controlli della mappa

    # Assegniamo la funzione di blocco all'update dello sfondo, così viene controllata costantemente
    sfondo_console.update = blocca_zoom_camera

    # Pannello di Stato del Rover (posizionato in alto a destra)
    state.pannello_stato_rover = WindowPanel(
        title='Stato Rover',
        content=(
            Text(text="Capienza Rover: 0/3", color=color.white),
        ),
        position=(0.6, 0.45) # Regola queste coordinate per spostarlo dove preferisci a destra
    )

    # Salviamo il riferimento al Text (che è il primo elemento del contenuto del pannello)
    state.testo_capienza_ui = state.pannello_stato_rover.content[0]
    
    # Inviamo il primo messaggio!
    print("[SISTEMA] Avvio simulazione 3D...")
    invoke(drone.esegui_piano_volo_drone, delay=1.0)

