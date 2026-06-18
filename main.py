from ursina import *
import state
from ui import genera_mappa_vuota, conferma_mappa, resetta_tutto
import map_manager

# Configurazione Iniziale
app = Ursina(title="Mappa Personalizzabile")
window.color = color.rgb(40, 40, 40)

# Costruzione e assegnamento UI allo state
state.input_longitude = InputField(default_value="7")
state.input_latitude = InputField(default_value="7")

state.map_panel = WindowPanel(
    title='Setup Mappa',
    content=(
        Text(text="Larghezza (Celle): "), state.input_longitude,
        Text(text="Altezza (Celle): "), state.input_latitude,
        Space(height=1),
        Button(text='Genera Mappa Vuota', color=color.azure, on_click=genera_mappa_vuota)
    ),
    position=(0, 0.25)
)

state.pannello_controlli = WindowPanel(
    title='Controlli Mappa',
    content=(
        Button(text='Genera Ostacoli Casuali', color=color.azure, on_click=map_manager.genera_ostacoli_casuali),
        Button(text='Svuota Mappa', color=color.gray, on_click=map_manager.pulisci_mappa),
        Button(text='Genera Dispersi Casuali', color=color.cyan, on_click=map_manager.genera_dispersi_casuali),
        Button(text='Conferma Mappa', color=color.green, on_click=conferma_mappa),
        Button(text='Torna al Menu', color=color.orange, on_click=resetta_tutto)
    ),
    position=(0.7, 0.4),
    enabled=False
)

if __name__ == '__main__':
    app.run()
