from ursina import color
import random
import state

def avanza_tempo_globale():
    """Questa funzione fa scorrere un turno di vita per tutti i dispersi non salvati e non morti."""
    for cell in state.dispersi:

        if cell in state.vittime_nascoste:
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

def spawna_vittime(quantita=2):
    """Fa comparire un numero specifico di vittime nascoste."""
    for _ in range(quantita):
        if state.vittime_nascoste:
            # Estrai una vittima a caso tra quelle nascoste
            nuova_vittima = random.choice(state.vittime_nascoste)
            state.vittime_nascoste.remove(nuova_vittima)
            state.vittime_attive.append(nuova_vittima)
            
            # Cambia il colore in rosso per segnalare l'emergenza comparsa
            nuova_vittima.color = color.red
            print(f"[SISTEMA] Nuova emergenza rilevata in ({nuova_vittima.grid_x}, {nuova_vittima.grid_y})!")



