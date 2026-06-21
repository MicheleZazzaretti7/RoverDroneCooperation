import textwrap
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
ospedale_posizione=(0,0)
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
registro_log_completo = [] # Mantiene l'intera cronologia dei log
pannello_log_testo = None  
slider_console = None      # Riferimento alla scrollbar grafica

max_righe_console = 14
scroll_offset_console = 0
auto_scroll_console = True # Scorre in basso in automatico all'arrivo di nuovi log

def aggiorna_vista_console():
    """Aggiorna il testo mostrato in base alla posizione della scrollbar."""
    if pannello_log_testo:
        inizio = scroll_offset_console
        fine = scroll_offset_console + max_righe_console
        righe_visibili = registro_log_completo[inizio:fine]
        pannello_log_testo.text = "\n".join(righe_visibili)
    
    if slider_console:
        max_scroll = max(0, len(registro_log_completo) - max_righe_console)
        slider_console.max = max_scroll
        # Se siamo in autoscroll, manteniamo forzatamente lo slider in basso (valore 0)
        if auto_scroll_console and slider_console.value != 0:
            slider_console.value = 0

def log_messaggio(testo):
    """Stampa in console, colora il testo tramite tag e lo aggiunge allo storico."""
    global scroll_offset_console, auto_scroll_console
    print(testo) 

    LARGHEZZA_MASSIMA_RIGA = 45 
    righe_originali = testo.strip().split('\n')
    
    # 1. Riconoscimento del mittente e assegnazione tag di colore Ursina
    colore_tag = "<white>"
    if "[DRONE]" in testo or "[DISPACCIO DRONE" in testo:
        colore_tag = "<cyan>"
    elif "[ROVER]" in testo or "[A*]" in testo:
        colore_tag = "<orange>"
    elif "[SISTEMA]" in testo or "[OSPEDALE]" in testo:
        colore_tag = "<green>"
    elif "[TRAGEDIA]" in testo or "ERRORE" in testo:
        colore_tag = "<red>"

    # 2. Spezza le righe e inserisci nello storico
    for riga in righe_originali:
        if riga.strip():
            righe_formattate = textwrap.wrap(riga, width=LARGHEZZA_MASSIMA_RIGA)
            for riga_wrap in righe_formattate:
                # Il tag <default> a fine stringa resetta il colore
                registro_log_completo.append(f"{colore_tag}{riga_wrap}<default>")

    # 3. Gestione autoscroll
    max_scroll = max(0, len(registro_log_completo) - max_righe_console)
    if auto_scroll_console:
        scroll_offset_console = max_scroll

    aggiorna_vista_console()
    
def abilita_wordwrap(input_field, larghezza=40):
    tf = input_field.text_field
    tf._wrapping = False  # guardia anti-ricorsione

    def wrap():
        if tf._wrapping:
            return
        y = int(tf.cursor.y)
        lines = tf.text.split('\n')
        if y >= len(lines) or len(lines[y]) <= larghezza:
            return

        riga = lines[y]
        spazio = riga.rfind(' ', 0, larghezza)
        if spazio == -1:
            spazio = larghezza

        sopra, sotto = riga[:spazio], riga[spazio:].lstrip(' ')
        lines[y] = sopra
        lines.insert(y + 1, sotto)

        tf._wrapping = True
        tf.text = '\n'.join(lines)
        tf.cursor.y = y + 1
        tf.cursor.x = len(sotto)
        tf.render()
        tf._wrapping = False
    
    original_text_input = tf.text_input
    def text_input_con_wrap(key):
        original_text_input(key)
        wrap()
    tf.text_input = text_input_con_wrap

# --- SISTEMA DI TRASPORTO ROVER ---
passeggeri_rover = []           # Lista delle vittime attualmente a bordo
CAPACITA_MAX_ROVER = 3          # Limite massimo di trasporto
in_viaggio_verso_ospedale = False # Flag di stato per il pathfinding
testo_capienza_ui = None        # Riferimento all'elemento grafico del testo



