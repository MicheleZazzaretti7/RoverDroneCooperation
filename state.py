grid_cells = []
map_w = 0
map_h = 0
descrizione_dispersi = {}
dispersi = []
disperso_corrente_idx = 0



panel_description = None
input_description = None
input_ttl = None
error_text = None
testo_istruzioni =None
map_panel = None
pannello_controlli = None
input_longitude = None
input_latitude = None


stato_posizionamento = None
start_drone_pos=(0,0)
start_rover_pos= (0,0)
turni_trascorsi = 0


vittime_nascoste = []  # Dispersi posizionati nel setup, ma non ancora visibili
vittime_attive = []    # Dispersi comparsi sulla mappa (colore rosso)
vittime_scoperte = []  # Dispersi trovati dal drone (in attesa di LLM o con Timer attivo)


mosse_drone_parziali = 0
mosse_rover_parziali = 0
rover_in_movimento = False # Diventerà True quando implementerete l'A* del rover
piano_volo_drone = []

rover = None
drone = None
rover_agent_instance = None
coda_obiettivi_rover = []
percorso_rover_corrente = []

# --- SISTEMA DI LOG A SCHERMO ---
registro_log = []          # Conterrà le ultime righe di testo inviate
pannello_log_testo = None  # L'entità Text di Ursina che mostrerà i log
