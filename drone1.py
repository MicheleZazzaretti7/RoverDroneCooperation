from aima import *
class DroneExplorationProblem(Problem):
    def __init__(self, initial, goal, map_w, map_h):
        super().__init__(initial, goal)
        self.map_w = map_w
        self.map_h = map_h

    def actions(self, state):
        x, y = state
        possible_actions = []
        
        # Passi da 1 (permettono di raggiungere ogni punto)
        if y < self.map_h - 1: possible_actions.append("Up_1")
        if y > 0: possible_actions.append("Down_1")
        if x < self.map_w - 1: possible_actions.append("Right_1")
        if x > 0: possible_actions.append("Left_1")
        
        # Passi da 2 (permettono salti veloci dove c'è spazio)
        if y < self.map_h - 2: possible_actions.append("Up_2")
        if y > 1: possible_actions.append("Down_2")
        if x < self.map_w - 2: possible_actions.append("Right_2")
        if x > 1: possible_actions.append("Left_2")
        
        return possible_actions

    def result(self, state, action):
        x, y = state
        # Parsing dell'azione per capire direzione e lunghezza
        if action == "Up_1": return (x, y + 1)
        if action == "Up_2": return (x, y + 2)
        if action == "Down_1": return (x, y - 1)
        if action == "Down_2": return (x, y - 2)
        if action == "Right_1": return (x + 1, y)
        if action == "Right_2": return (x + 2, y)
        if action == "Left_1": return (x - 1, y)
        if action == "Left_2": return (x - 2, y)
        return state
