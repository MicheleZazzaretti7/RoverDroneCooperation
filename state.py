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
registro_log = []          # Conterrà le ultime righe di testo inviate
pannello_log_testo = None  # L'entità Text di Ursina che mostrerà i log

def log_messaggio(testo):
    """Stampa in console e aggiorna il pannello 3D andando a capo automaticamente."""
    print(testo)  # Mantiene la stampa standard nel terminale per debug

    # Definisci quanti caratteri al massimo deve contenere una riga prima di andare a capo
    LARGHEZZA_MASSIMA_RIGA = 45 

    # Separiamo prima il testo se ci sono già dei vado a capo (\n) manuali
    righe_originali = testo.strip().split('\n')
    
    for riga in righe_originali:
        if riga.strip():
            # textwrap.wrap spezza la riga in una lista di righe più corte senza tagliare le parole
            righe_formattate = textwrap.wrap(riga, width=LARGHEZZA_MASSIMA_RIGA)
            for riga_wrap in righe_formattate:
                registro_log.append(riga_wrap)

    # Dato che ora andiamo a capo più spesso, aumentiamo il numero di righe 
    # visibili a schermo (es. ultime 14 righe invece di 10)
    while len(registro_log) > 14:
        registro_log.pop(0)

    # Aggiorna il pannello grafico
    if pannello_log_testo:
        pannello_log_testo.text = "\n".join(registro_log)
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

