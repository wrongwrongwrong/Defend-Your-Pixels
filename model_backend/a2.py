"""Miscellaneous Tkinter prototype / reference code.

This file is not imported by the Defend-Your-Pixels runtime (as of today); it is kept
in-repo as standalone reference code. It still has a module docstring so readers can
quickly identify it as non-core to the authoritative game model.
"""

import tkinter as tk
from tkinter import messagebox, filedialog
from typing import Callable, Optional

from support import *

# 4.1.1 initialize attract weapon class
class Weapon:
    def __init__(self):
        self._name= "AbstractWeapon"
        self._symbol= WEAPON_SYMBOL
        self._effect = {}
        self._range = 0
        
    def get_name(self)-> str:
        return self._name
    
    def get_symbol(self)->str:
        return self._symbol
    
    def get_effect(self)->dict[str,int]:
        return self._effect
    
    def get_targets(self,position:Position)->list[Position]:
        # check the reach of weapon within it's range
        target =[]
        curr_row,curr_col = position
        
        for i in range (-self._range, self._range+1):
            #row
            row_point= (curr_row + i, curr_col)
            if row_point != position:
                target.append(row_point)

            #column
            col_point=(curr_row,curr_col+i)
            if col_point!= position:
                target.append(col_point)

        return target
            
    def __str__(self)->str:
        return self._name
    
    def __repr__(self)->str:
        return f"Weapon()"

#4.1.2 PoisonDart（weapon)

class PoisonDart(Weapon):
    def __init__(self):
        self._name= "PoisonDart"
        self._symbol=POISON_DART_SYMBOL
        self._effect ={"poison":2}
        self._range = 2

    def __repr__(self)->str: 
        return "PoisonDart()"
    
#4.1.3 PoisonSword(Weapon)
class PoisonSword(Weapon):
    def __init__(self):
        self._name= "PoisonSword"
        self._symbol=POISON_SWORD_SYMBOL
        self._effect ={"damage":2,"poison":1}
        self._range = 1
        
    def __repr__(self)->str:
        return f"PoisonSword()"

#4.1.4 HealingRock(Weapon)
class HealingRock(Weapon):
    def __init__(self):
        self._name= "HealingRock"
        self._symbol=HEALING_ROCK_SYMBOL
        self._effect ={"healing":2}
        self._range = 2

    def __repr__(self)->str:
        return f"HealingRock()"

#4.1.5 Tile()
class Tile:
    def __init__(self, symbol: str, is_blocking: bool) -> None:
        self._symbol= symbol
        self._is_blocking = is_blocking
        self._weapon = None
        
    def is_blocking(self)->bool:
        return self._is_blocking
    
    def get_weapon(self)->Optional[Weapon]:
        return self._weapon
    
    def set_weapon(self, weapon: Weapon) -> None:
        self._weapon = weapon
            
    def remove_weapon(self) -> None:
        self._weapon = None

    def __str__(self) -> str:
        return self._symbol
    
    def __repr__(self) -> str:
        return f"Tile('{self._symbol}', {self._is_blocking})"

#4.1.6 create tile
def create_tile(symbol:str)->Tile:
    if symbol == WALL_TILE:
        return Tile(WALL_TILE,True)
        
    elif symbol == FLOOR_TILE:
        return Tile(FLOOR_TILE,False)
        
    elif symbol == GOAL_TILE:
        return Tile(GOAL_TILE,False)
        
    elif symbol in [POISON_DART_SYMBOL, POISON_SWORD_SYMBOL,HEALING_ROCK_SYMBOL]:
        if symbol == POISON_DART_SYMBOL:
            #create a weapon
            weapon = PoisonDart()
            #create a empty tile
            tile=Tile(FLOOR_TILE,False)
            #set weapon on the tile
            tile.set_weapon(weapon)
            
            return tile
    
        if symbol == POISON_SWORD_SYMBOL:
            #copy paste 1st code and change object name
            weapon= PoisonSword()
            tile=Tile(FLOOR_TILE,False)
            tile.set_weapon(weapon)
            
            return tile
        
        if symbol == HEALING_ROCK_SYMBOL:
            weapon= HealingRock()
            tile=Tile(FLOOR_TILE,False)
            tile.set_weapon(weapon)
            
            return tile

    return Tile(FLOOR_TILE,False)
        

#4.1.7 Entity
class Entity:
    def __init__(self, max_health: int) -> None:
        self._name = "Entity"
        self._max_health = max_health
        self._health= max_health
        self._symbol= ENTITY_SYMBOL
        self._poison_stat = 0
        self._weapon = None

    def get_symbol(self) -> str:
        return self._symbol

    def get_name(self) -> str:
        return self._name
    
    def get_health(self) -> int:
        return self._health

    def get_poison(self) -> int:
        return self._poison_stat

    def get_weapon(self) -> str:
        return self._weapon
    
    def equip(self, weapon: Weapon) -> None:
        self._weapon = weapon

    #identify weapon then reuse get_target from 4.1.1
    def get_weapon_targets(self, position: Position) -> list[Position]:
        if self._weapon !=None:
            return self._weapon.get_targets(position)
        else:
            return []
    def get_weapon_effect(self) -> dict[str, int]:
        if self._weapon !=None:
            return self._weapon.get_effect()
        else:
            return {}
        
    def apply_effects(self, effects: dict[str, int]) -> None:
        for effect_type, effect_value in effects.items():
            if effect_type == "healing" :
                self._health += effect_value
                if self._health > self._max_health:
                    self._health = self._max_health

            elif effect_type == "damage":
                self._health -= effect_value
            
                #set negative health to 0 to prevent error
                if self._health < 0:
                    self._health = 0

            elif effect_type == "poison":
                self._poison_stat += effect_value
    
    def apply_poison(self) -> None:
        if self._poison_stat > 0:
            self._health -= self._poison_stat
            #same as damage. set negative health to 0 to prevent error
            if self._health < 0:
                self._health = 0
            self._poison_stat -= 1

    def is_alive(self) -> bool:
        if self._health ==0:
            return False
        else:
            return True

    def __str__(self) -> str:
        return self._name

    def __repr__(self)->str:
        return f'Entity({self._max_health})'
    
#4.1.8 Player
class Player(Entity):
    def __init__(self, max_health: int) -> None:
        #most init same as entity, except name and symbol
        super().__init__(max_health)
        self._name = "Player"
        self._symbol= PLAYER_SYMBOL
        

    def __repr__(self)-> str:
        return f"Player({self._max_health})"

#4.1.9 Slug
class Slug(Entity):
    def __init__(self, max_health: int) -> None:
        #init
        super().__init__(max_health)
        self._name = "Slug"
        self._symbol= SLUG_SYMBOL
        self._move = True
        
    def choose_move(self, candidates: list[Position],
                    current_position: Position, player_position: Position) -> Position:
        raise NotImplementedError("Slug subclasses must implement a choose_move method.")

    def can_move(self)->bool:
        return self._move
        
    def end_turn(self)->None:
        self._move = not self._move

    def __repr__(self)->str:
        return f"Slug({self._max_health})"
  
#4.1.10 Nice Slug
class NiceSlug(Slug):
    def __init__(self) -> None:
        #All NiceSlug instances should hold a HealingRock weapon and have a max_health of 10
        super().__init__(10)
        self._name = "NiceSlug"
        self._symbol = NICE_SLUG_SYMBOL
        self._weapon = HealingRock()

    def choose_move(self, candidates: list[Position],
                    current_position: Position, player_position: Position) -> Position:
        return current_position

    def __repr__(self)->str:
        return 'NiceSlug()'

#4.1.11 Angry Slug
class AngrySlug(Slug):
    def __init__(self) -> None:
        super().__init__(5)
        self._name = "AngrySlug"
        self._symbol = ANGRY_SLUG_SYMBOL
        #All AngrySlug instances should hold a PoisonSword weapon and have a max_health of 5
        self._weapon = PoisonSword()
        
    def choose_move(self, candidates: list[Position],
                    current_position: Position, player_position: Position) -> Position:
        a, b = player_position
        final_decision = current_position
        min_distance = float('inf')  # Initialize with a large value
    
        for (x,y) in candidates:
            # Calculate the Euclidean distance
            distance = ((x - a) ** 2 + (y - b) ** 2) ** 0.5

        
            # Find the position with the smallest distance
            if distance < min_distance:
                min_distance = distance
                final_decision = (x, y)

            if distance == min_distance and (x,y) < final_decision:
                final_decision = (x, y)
                    
        return final_decision

    def __repr__(self)->str:
        return 'AngrySlug()'
        
#4.1.12 Scared Slug
class ScaredSlug(Slug):
    def __init__(self) -> None:
        super().__init__(3)
        self._name = "ScaredSlug"
        self._symbol = SCARED_SLUG_SYMBOL
        #All ScaredSlug instances should hold a PoisonDart weapon and have a max_health of 3.
        self._weapon = PoisonDart()

    def choose_move(self,
                    candidates: list[Position],
                    current_position: Position,
                    player_position: Position) -> Position:
        a, b = player_position
        final_decision = current_position
        max_distance = 0
        
        for (x, y) in candidates:
            distance = ((x - a) ** 2 + (y - b) ** 2) ** 0.5

            # Find the position with the farest distance
            if distance > max_distance:
                max_distance = distance
                final_decision = (x, y)

            if distance == max_distance and (x,y) > final_decision:
                final_decision = (x, y)
            
        return final_decision
    
    def __repr__(self)->str:
        return 'ScaredSlug()'

"""
test code for GamePlay step7 :
Oct24: for GamePlay step23:
tiles = [
[create_tile("#"), create_tile("#"), create_tile("#"), create_tile("#")],
[create_tile("#"), create_tile(" "), create_tile(" "), create_tile("#")],
[create_tile("#"), create_tile(" "), create_tile(" "), create_tile("#")],
[create_tile("#"), create_tile(" "), create_tile(" "), create_tile("#")],
[create_tile("#"), create_tile("S"), create_tile(" "), create_tile("#")],
[create_tile("#"), create_tile(" "), create_tile(" "), create_tile("#")],
[create_tile("#"), create_tile("#"), create_tile("#"), create_tile("#")]
]
slugs = {(2, 2): ScaredSlug(),(3,2):NiceSlug()}
player = Player(20)
model = SlugDungeonModel(tiles, slugs, player, (2, 1))

model.handle_player_move((1,0))

model.get_slugs()
"""
    
# A help method for get valid position for player
def check_valid_position(position,game):
    
    #must on the board 0 < row< len(self._tiles) 0< col< len(self._tile[0])
    #exclude blocking tile
    #exlcude other entities(Slug and Player)
    x,y = position
    x_bound,y_bound = game.get_dimensions()
    tile = game._tiles[x][y]
    
    #first condition: on board
    if x< 0 or y < 0 or x > x_bound or y> y_bound:
        return False
    
    #exclude blocking tile
    if tile.is_blocking():
        return False
        
    #exlcude Slug
    if position in game._slugs:
        return False
    
    return True

#4.1.13 SlugDungeonModel
class SlugDungeonModel():

    # (x,y):NiceSlug(),(a,b): ScarSlug()
    def __init__(self,tiles:list[list[Tile]],slugs: dict[Position,Slug],
                 player:Player,player_position:Position)->None:
        self._tiles = tiles
        self._slugs = slugs.copy()
        self._player = player
        self._player_position = player_position
        self._player_previous_position = player_position
        

    def get_tiles(self) -> list[list[Tile]]:
        return self._tiles
    
    def get_slugs(self) -> dict[Position, Slug]:
        return self._slugs

    def get_player(self) -> Player:
        return self._player

    def get_player_position(self) -> Position:
        return self._player_position

    def get_tile(self, position: Position) -> Tile:
        x, y = position
        return self._tiles[x][y]

    #get row and column
    def get_dimensions(self) -> tuple[int, int]:
        return (len(self._tiles), len(self._tiles[0]))
    
    def get_slug_position(self,slug: Slug) -> list[Position]:
        for pos, s in self._slugs.items():
            if s == slug:
                return pos  # Return the position if the slug is found
            
        return None  # If the slug is not found, return None
        
    def get_valid_slug_positions(self, slug: Slug) -> list[Position]:
        slug_position = self.get_slug_position(slug)
        valid_position = []
        
        if not slug.can_move() or slug_position is None:
            return valid_position  # Slug can't move or position is not found
        
        # Check adjacent positions (up, down, left, right)
        directions = [
            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1),
            (0,0)]
        x, y = slug_position

        x_bound,y_bound = self.get_dimensions()
        
        # Iterate through possible directions
        for dx, dy in directions:
            potential_pos = (x + dx, y + dy)
            
            # Ensure the position is within bounds
            if 0 <= x + dx < x_bound and 0 <= y + dy < y_bound:
                tile = self.get_tile(potential_pos)
                
                # Check if the tile is not blocking
                if not tile.is_blocking():
                    
                    # Check if the position is not occupied by the player
                    if potential_pos != self.get_player_position():
                        
                        # Allow staying in the same position but exclude other slugs
                        if potential_pos == slug_position or potential_pos not in self._slugs:
                            valid_position.append(potential_pos)

        return valid_position

    def perform_attack(self, entity: Entity, position: Position) -> None:

        #if entity is slug, the can attack player, vis versa
        if entity.get_weapon():
            targets = entity.get_weapon().get_targets(position)

            #entity == player -> slug
            if entity.get_name() =="Player":
                for slug_pos in self._slugs:
                    if slug_pos in targets:
                        self._slugs[slug_pos].apply_effects(entity.get_weapon_effect())
                        

            #entity == slug -> player
            slug_list = ["AngrySlug","ScaredSlug","NiceSlug"]
            if entity.get_name() in slug_list :
                if self.get_player_position() in targets:
                    self._player.apply_effects(entity.get_weapon_effect())

    def end_turn(self) -> None:
        # Step 1: Apply player's poison
        self._player.apply_poison()

        # Step 2: Apply poison to slugs and remove dead slugs
        slug_to_remove = []
            
        slugs_copy = self._slugs.copy()

        for slug_position, slug_name in slugs_copy.items():
            slug_name.apply_poison()
            
            #if dead, drop weapon
            if not slug_name.is_alive():
                tile = self.get_tile(slug_position)
                if slug_name.get_weapon():
                    tile.set_weapon(slug_name.get_weapon())
                #add the key of slugs waiting to be removed 
                slug_to_remove.append(slug_position)
                
        #remove all dead slugs from update_slugs
        for slug_position in slug_to_remove:
            del self._slugs[slug_position]

        #UPDATE The slug_copy after removal of dead slugs
        slugs_copy = self._slugs.copy()
        for slug_position, slug_name in slugs_copy.items():
            #if can move, then moved to the position
            if slug_name.can_move():
                candidates = self.get_valid_slug_positions(slug_name)

                #move to the valid slug position
                new_position = slug_name.choose_move(candidates,slug_position,
                                                     self._player_previous_position)

                # Update the slug's position in _slugs
                del self._slugs[slug_position]  # Remove from the old position
                self._slugs[new_position] = slug_name  # Add to the new position
        
            slug_name.end_turn()

        # after all slugs moved, perform attack
        for position, slug in self._slugs.items():
            self.perform_attack(slug, position)

        #update player previous position 
        self._player_previous_position = self._player_position

    def handle_player_move(self, position_delta: Position) -> None:
        # Step 1: Calculate the new position
        player_position = self.get_player_position()  
        new_position = (player_position[0] + position_delta[0],
                        player_position[1] + position_delta[1])

        # Step 2: Check if the move is valid (within bounds and not blocked)
        if player_position == new_position:
            pass
        else:
            if not check_valid_position(new_position,self):
                return # Invalid move, do nothing

        # Step 3: Update player's position
        self._player_position = new_position


        # Step 4: Check if the new tile has a weapon and equip it
        tile = self.get_tile(new_position)  
        if tile.get_weapon():  # Check if the tile contains a weapon
            weapon = tile.get_weapon()  # Get the weapon
            self.get_player().equip(weapon)  # Equip the player with the weapon
            tile.remove_weapon()  # Remove the weapon from the tile

        # Step 5: Perform an attack from the new position
        self.perform_attack(self._player, new_position)

        # Step 6: Call the end_turn method to finalize the turn
        self.end_turn()
    
    def has_won(self) -> bool:
        # Check if all slugs are killed
        if any(slug.get_health() > 0 for slug in self._slugs.values()):
            return False  # There are still slugs with health left
        
        # Check if player is on the goal tile
        player_position = self.get_player_position()
        if str(self.get_tile(player_position)) == GOAL_TILE:
            return True  # Player has reached the goal and killed all slugs
    
        return False  # Player hasn't reached the goal yet

    
    def has_lost(self) -> bool:
        if self._player.get_health() == 0:
            return True  # The player has no health left and has lost the game
    
        return False  # The player is still alive


#4.1.14 load level(filename: str) -> SlugDungeonModel
def load_level(filename: str) -> SlugDungeonModel:
    with open(filename, 'r') as file:
        # Step 1: Read the player's max health from the first line
        max_health = int(file.readline().strip())
        player = Player(max_health)
        
        tiles = []
        slugs = {}
        player_position = None
        
        # Step 2: Read the rest of the lines for the game state (tiles and slugs)
        for row_idx, line in enumerate(file):
            row = []
            for col_idx, symbol in enumerate(line.strip()):
                # Create a tile for each symbol
                tile = create_tile(symbol)
                row.append(tile)

                # Check for player and slugs in the line
                if symbol == PLAYER_SYMBOL:
                    player_position = (row_idx, col_idx)  # Set player's position
                elif symbol in [ANGRY_SLUG_SYMBOL, SCARED_SLUG_SYMBOL, NICE_SLUG_SYMBOL]:
                    if symbol == ANGRY_SLUG_SYMBOL:
                        slug = AngrySlug()
                    elif symbol == SCARED_SLUG_SYMBOL:
                        slug = ScaredSlug()
                    elif symbol == NICE_SLUG_SYMBOL:
                        slug = NiceSlug()
                    slugs[(row_idx, col_idx)] = slug  # Add slug to dictionary
            
            tiles.append(row)

        # Step 3: Return the SlugDungeonModel
        return SlugDungeonModel(tiles, slugs, player, player_position)


#4.2 View


#4.2.1 DungeonMap(AbstractGrid)
class DungeonMap(AbstractGrid):
    def __init__(self, master, dimensions: tuple[int, int], size: tuple[int, int], **kwargs):
        
        # Initialize using AbstractGrid's constructor
        size = DUNGEON_MAP_SIZE
        super().__init__(master, dimensions, size, **kwargs)
        # Set the window title
        if isinstance(master, tk.Tk):
            master.title("Slug Dungeon")

    def redraw(self, tiles: list[list[Tile]], player_position: Position, slugs: dict[Position, Slug]) -> None:
        # Step 1: Clear the dungeon map
        self.clear()

        # Step 2: Draw each tile in the grid
        for row_idx, row in enumerate(tiles):
            for col_idx, tile in enumerate(row):
                # Get the bounding box for this tile
                x1, y1, x2, y2 = self.get_bbox((row_idx, col_idx))

                # Draw a rectangle for each tile
                if tile.is_blocking():
                    self.create_rectangle(x1, y1, x2, y2, fill=WALL_COLOUR)  # Wall tile color
                elif str(tile) == GOAL_TILE:
                    self.create_rectangle(x1, y1, x2, y2, fill=GOAL_COLOUR)  # Goal tile color
                else:
                    self.create_rectangle(x1, y1, x2, y2, fill=FLOOR_COLOUR)  # Default floor tile color

                # Annotate the tile with the weapon symbol if it has a weapon
                if tile.get_weapon() is not None:
                    weapon_symbol = tile.get_weapon().get_symbol()
                    self.annotate_position((row_idx, col_idx), font = REGULAR_FONT, text=weapon_symbol)

        # Step 3: Draw the player
        x1, y1, x2, y2 = self.get_bbox(player_position)
        self.create_oval(x1, y1, x2, y2, fill=PLAYER_COLOUR)  # Player is drawn in blue
        self.annotate_position(player_position, text="Player")  # Annotate with the player's name

        # Step 4: Draw the slugs
        for slug_position, slug in slugs.items():
            x1, y1, x2, y2 = self.get_bbox(slug_position)

            # Check if the slug can move and adjust the color accordingly
            if slug.can_move():
                self.create_oval(x1, y1, x2, y2, fill="light pink")  # Slug that can move
            else:
                self.create_oval(x1, y1, x2, y2, fill="green")  # Slug that cannot move

            # Annotate with the slug's name
            if slug.get_name() == "NiceSlug":
                self.annotate_position(slug_position, font = REGULAR_FONT, text="Nice\nSlug")

            elif slug.get_name() == "AngrySlug":
                self.annotate_position(slug_position, font = REGULAR_FONT, text="Angry\nSlug")

            elif slug.get_name() == "ScaredSlug":
                 self.annotate_position(slug_position, font = REGULAR_FONT, text="Scared\nSlug")

    
        

#4.2.2 DungeonInfo(AbstractGrid)
class DungeonInfo(AbstractGrid):
    def __init__(self, master, dimensions: tuple[int, int], size: tuple[int, int], **kwargs):
        # Initialize using AbstractGrid's constructor
        super().__init__(master, dimensions, size, **kwargs)

    def redraw(self, entities: dict[Position, Entity]) -> None:
        # Step 1: Clear the dungeon info grid
        self.clear()

        # Step 2: Draw the headers in the first row
        headers = ["Name", "Position", "Weapon", "Health", "Poison"]
        for col_idx, header in enumerate(headers):
            self.annotate_position((0, col_idx), text=header, font = TITLE_FONT)  # Headers are in the first row

        # Step 3: Draw each entity's information in subsequent rows
        for row_idx, (position, entity) in enumerate(entities.items(), start=1):
            # Get entity details
            name = entity.get_name()
            weapon = entity.get_weapon().get_name() if entity.get_weapon() else "None"
            health = entity.get_health()
            poison = entity.get_poison()
            
            # Fill the row with entity details
            info = [name, str(position), weapon, str(health), str(poison)]
            for col_idx, detail in enumerate(info):
                self.annotate_position((row_idx, col_idx), text=detail)



#4.2.3 ButtonPanel(tk.Frame)
class ButtonPanel(tk.Frame):
    def __init__(self, root: tk.Tk, on_load: Callable, on_quit: Callable) -> None:
        super().__init__(root)  # Initialize the frame

        # Create the Load Game button, aligned to the left
        load_button = tk.Button(self, text="Load Game", command=on_load)
        load_button.pack(side=tk.LEFT, expand =True, padx=20, pady=10)

        # Create the Quit button, aligned to the right
        quit_button = tk.Button(self, text="Quit", command=on_quit)
        quit_button.pack(side=tk.LEFT, expand =True, padx=20, pady=10)

#4.3 Controller
#4.3.1 SlugDungeon()
class SlugDungeon:
    def __init__(self, root: tk.Tk, filename: str) -> None:
        
        # Initialize the root window
        self.root = root

        # Set the window title 
        self.root.title("Slug Dungeon")

        # Step 1: Load the model from the game file
        self.model = load_level(filename)
        # Winning and pressing yes should restart fix: define current_level for reset_level
        self.current_level = filename

        # Step 2: Create view instances
        # Create a frame to contain the DungeonMap and SlugInfo (red box)
        self.main_frame = tk.Frame(master=root, width=900, height=500)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # DungeonMap on the left (500x500)
        self.dungeon_map = DungeonMap(
            master=self.main_frame, dimensions=self.model.get_dimensions(), size= DUNGEON_MAP_SIZE
        )
        self.dungeon_map.pack(side=tk.LEFT)

        # DungeonInfo instance for slugs on the right (400x500)
        self.slug_info = DungeonInfo(
            master=self.main_frame, dimensions=(7, 5), size= SLUG_INFO_SIZE
        )
        self.slug_info.pack(side=tk.RIGHT)

        # DungeonInfo instance for player (blue box, 900x100)
        self.player_info = DungeonInfo(
            master=root, dimensions=(2, 5), size=PLAYER_INFO_SIZE
        )
        self.player_info.pack(fill=tk.X)

        # Step 3: Create a ButtonPanel instance (purple box)
        self.button_panel = ButtonPanel(
            root,
            on_load=self.load_level,  # Pass your on_load function
            on_quit=self.quit_game  # Pass your on_quit function
        )
        self.button_panel.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        # Step 4: Redraw the display to show the initial game state
        self.redraw()

        # Step 5: Bind events
        self.bind_events()


    def arrange_layout(self):
        # Use grid to arrange the layout of the DungeonMap, DungeonInfo, and ButtonPanel
        # DungeonMap on the left
        self.dungeon_map.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)

        # SlugInfo on the right
        self.slug_info.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.Y)

        # PlayerInfo at the bottom, across the entire width
        self.player_info.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        # ButtonPanel at the bottom, below the player info
        self.button_panel.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

    def bind_events(self):
        # Bind relevant events like player movement
        self.root.bind("<KeyPress>", self.handle_key_press)

    def handle_key_press(self, event: tk.Event) -> None:
        valid_keys = {
            'w': (-1, 0),  # Move up
            'a': (0, -1),  # Move left
            's': (1, 0),   # Move down
            'd': (0, 1),   # Move right
            'space': (0, 0)  # Special action (if any)
        }
        
        if event.keysym in valid_keys:
            move = valid_keys[event.keysym]
            self.model.handle_player_move(move)
            
            # Redraw after movement
            self.redraw()

            # Check if the game is won or lost
            if self.model.has_won():
                self.root.update_idletasks()
                play_again = messagebox.askyesno(WIN_TITLE, WIN_MESSAGE)
                if play_again:
                     #Reset game
                    self.reset_level()
                else:
                    self.quit_game()

            elif self.model.has_lost():
                self.root.update_idletasks()
                play_again = messagebox.askyesno(LOSE_TITLE, LOSE_MESSAGE)
                if play_again:
                    self.load_level()  # Reset game
                else:
                    self.quit_game()


    def redraw(self):
        # Redraw the map, slugs, and player information
        self.dungeon_map.redraw(self.model.get_tiles(), self.model.get_player_position(), self.model.get_slugs())
        self.slug_info.redraw(self.model.get_slugs())
        self.player_info.redraw({self.model.get_player_position(): self.model.get_player()})

    def load_level(self) -> None:
        """Prompts the user to select a file to load and updates the game state."""
        # Open file dialog to choose a file
        file_path = filedialog.askopenfilename(
            title="Select a Game File",
            filetypes=(("Text Files", "*.txt"), ("All Files", "*.*"))
        )

        if file_path:
            # Load the new game model from the selected file
            self.model = load_level(file_path)

            # Update the dungeon_map with new dimensions
            self.dungeon_map.set_dimensions(self.model.get_dimensions())

            # Redraw the display to reflect the new game state
            self.redraw()
            
    def reset_level(self) -> None:
        """Resets the current level and updates the game state."""
        # Reload the model (game state) from the current level
        self.model = load_level(self.current_level)

        # Update the dungeon map with the new model
        self.dungeon_map.set_dimensions(self.model.get_dimensions())
        self.redraw()

        
    def quit_game(self):
        """Quit the game and close the application."""
        self.root.destroy()  # Properly destroy the Tkinter window to close the application


#4.4 Play_game
def play_game(root: tk.Tk, file_path: str) -> None:
    # Step 1: Create the game controller
    game = SlugDungeon(root, file_path)
    
    # Step 2: Start the Tkinter main event loop
    root.mainloop()

#4.5 main
def main() -> None:
    # Step 1: Create the root window
    root = tk.Tk()
    
    # Step 2: Call play_game with the root window and a level file path
    play_game(root, 'levels/level1.txt')

if __name__ == "__main__":
    main()
    
        
        
    
        

        
        
