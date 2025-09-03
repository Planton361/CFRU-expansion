import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
import re
import os
from PIL import Image, ImageTk
from PIL.Image import Resampling
from difflib import get_close_matches
from tkinter import filedialog
import struct
import numpy as np

# Party type mappings
PARTY_TYPES = [
    ("NoItemDefaultMoves (No item, default moves)", 1),
    ("ItemDefaultMoves (With item, default moves)", 2),
    ("NoItemCustomMoves (No item, custom moves)", 3),
    ("ItemCustomMoves (With item, custom moves, abilities, natures, IVs/EVs)", 4)
]

PARTY_TYPE_STRUCT_MAP = {
    1: "TrainerMonNoItemDefaultMoves",
    2: "TrainerMonItemDefaultMoves", 
    3: "TrainerMonNoItemCustomMoves",
    4: "TrainerMonItemCustomMoves"
}

PARTY_TYPE_UNION_MAP = {
    1: "NoItemDefaultMoves",
    2: "ItemDefaultMoves", 
    3: "NoItemCustomMoves",
   4: "ItemCustomMoves"
}

TRAINER_PICS = {
    "ARCHIE": 0,
    "AQUA_GRUNT_M": 1,
    "AQUA_GRUNT_F": 2,
    "AROMA_LADY_RS": 3,
    "RUIN_MANIAC_RS": 4,
    "CAMERA_DUO": 5,
    "RS_TUBER_F": 6,
    "RS_TUBER_M": 7,
    "RS_COOLTRAINER_M": 8,
    "RS_COOLTRAINER_F": 9,
    "HEX_MANIAC": 10,
    "RS_LADY": 11,
    "RS_BEAUTY": 12,
    "RICH_BOY": 13,
    "RS_POKEMANIAC": 14,
    "RS_SWIMMER_M": 15,
    "RS_BLACK_BELT": 16,
    "GUITARIST": 17,
    "KINDLER": 18,
    "RS_CAMPER": 19,
    "BUG_MANIAC": 20,
    "RS_PSYCHIC_M": 21,
    "RS_PSYCHIC_F": 22,
    "RS_GENTLEMAN": 23,
    "SIDNEY": 24,
    "PHOEBE": 25,
    "ROXANNE": 26,
    "BRAWLY": 27,
    "LIZA_AND_TATE": 28,
    "SCHOOL_BOY": 29,
    "SCHOOL_GIRL": 30,
    "SR_AND_JR": 31,
    "POKEFAN_M": 32,
    "POKRFAN_F": 33,
    "EXPERT_M": 34,
    "EXPERT_F": 35,
    "RS_YOUNGSTER": 36,
    "STEVEN": 37,
    "RS_FISHERMAN": 38,
    "CYCLING_TRIATHLETE_M": 39,
    "CYCLING_TRIATHLETE_F": 40,
    "RUNNING_TRIATHLETE_M": 41,
    "RUNNING_TRIATHLETE_F": 42,
    "SWIMMING_TRIATHLETE_M": 43,
    "SWIMMING_TRIATHLETE_F": 44,
    "DRAGON_TAMER": 45,
    "RS_BIRDKEEPER": 46,
    "NINJA_BOY": 47,
    "RS_CRUSHGIRL": 48,
    "PARASOL_LADY": 49,
    "RS_SWIMMER_F": 50,
    "RS_PICNICKER": 51,
    "RS_TWINS": 52,
    "RS_SAILOR": 53,
    "COLLECTOR": 54,
    "RS_WALLY": 55,
    "RS_BRENDAN": 56,
    "RS_MAY": 57,
    "RS_BREEDER_M": 58,
    "RS_BREEDER_F": 59,
    "RS_RANGER_M": 60,
    "RS_RANGER_F": 61,
    "MAXIE": 62,
    "MAGMA_GRUNT_M": 63,
    "MAGMA_GRUNT_F": 64,
    "RS_LASS": 65,
    "RS_BUGCATCHER": 66,
    "RS_HIKER": 67,
    "RS_YOUNG_COUPLE": 68,
    "EXPERT_DUO": 69,
    "RS_SIS_AND_BRO": 70,
    "MATT": 71,
    "SHELLY": 72,
    "TABITHA": 73,
    "COURTNEY": 74,
    "WATTSON": 75,
    "FLANNERY": 76,
    "NORMAN": 77,
    "WINONA": 78,
    "WALLACE": 79,
    "GLACIA": 80,
    "DRAKE": 81,
    "YOUNGSTER": 82,
    "BUG_CATCHER": 83,
    "LASS": 84,
    "SAILOR": 85,
    "CAMPER": 86,
    "PICNICKER": 87,
    "POKEMANIAC": 88,
    "SUPER_NERD": 89,
    "HIKER": 90,
    "BIKER": 91,
    "BURGLAR": 92,
    "WORKER": 93,
    "FISHERMAN": 94,
    "SWIMMER_M": 95,
    "CUE_BALL": 96,
    "GAMBLER": 97,
    "BEAUTY": 98,
    "SWIMMER_F": 99,
    "PSYCHIC_M": 100,
    "ROCKER": 101,
    "JUGGLER": 102,
    "TAMER": 103,
    "BIRD_KEEPER": 104,
    "BLACK_BELT": 105,
    "BLUE": 106,
    "SCIENTIST_M": 107,
    "GIOVANNI": 108,
    "ROCKET_GRUNT_M": 109,
    "COOLTRAINER_M": 110,
    "COOLTRAINER_F": 111,
    "LORLEI": 112,
    "BRUNO": 113,
    "AGATHA": 114,
    "LANCE": 115,
    "BROCK": 116,
    "MISTY": 117,
    "LT_SURGE": 118,
    "ERIKA": 119,
    "KOGA": 120,
    "BLAINE": 121,
    "SABRINA": 122,
    "GENTLEMAN": 123,
    "BLUE_2": 124,
    "BLUE_3": 125,
    "CHANNELER": 126,
    "TWINS": 127,
    "COOL_COUPLE": 128,
    "YOUNG_COUPLE": 129,
    "CRUSH_KIN": 130,
    "SIS_AND_BRO": 131,
    "PROF_OAK": 132,
    "BRENDAN": 133,
    "MAY": 134,
    "PLAYER_M": 135,
    "PLAYER_F": 136,
    "ROCKET_GRUNT_F": 137,
    "PSYCHIC_F": 138,
    "CRUSH_GIRL": 139,
    "TUBER_F": 140,
    "PKMN_BREEDER_F": 141,
    "PKMN_RANGER_M": 142,
    "PKMN_RANGER_F": 143,
    "AROMA_LADY": 144,
    "RUIN_MANIAC": 145,
    "SELPHY": 146,
    "PAINTER": 147
}

# Tera Type options
TERA_TYPES = [
    "TYPE_NORMAL", "TYPE_FIGHTING", "TYPE_FLYING", "TYPE_POISON", "TYPE_GROUND",
    "TYPE_ROCK", "TYPE_BUG", "TYPE_GHOST", "TYPE_STEEL", "TYPE_MYSTERY",
    "TYPE_FIRE", "TYPE_WATER", "TYPE_GRASS", "TYPE_ELECTRIC", "TYPE_PSYCHIC",
    "TYPE_ICE", "TYPE_DRAGON", "TYPE_DARK", "TYPE_ROOSTLESS", "TYPE_BLANK",
    "TYPE_FAIRY", "TYPE_STELLAR"
]

AI_FLAGS = {
    'AI_SCRIPT_CHECK_BAD_MOVE': 1,
    'AI_SCRIPT_SEMI_SMART': 2,
    'AI_SCRIPT_CHECK_GOOD_MOVE': 4,
    'AI_SCRIPT_TRY_TO_FAINT': 8,
    'AI_SCRIPT_CHECK_VIABILITY': 16,
    'AI_SCRIPT_SETUP_FIRST_TURN': 32,
    'AI_SCRIPT_RISKY': 64,
    'AI_SCRIPT_PREFER_STRONGEST_MOVE': 128,
    'AI_SCRIPT_PREFER_BATON_PASS': 256,
    'AI_SCRIPT_DOUBLE_BATTLE': 512
}

AI_FLAGS_REVERSE = {v: k for k, v in AI_FLAGS.items()}

ABILITY_OPTIONS = [
    'Ability_Hidden', 'Ability_1', 'Ability_2', 'Ability_Random_1_2', 'Ability_RandomAll'
]

NATURES = [
    "HARDY", "LONELY", "BRAVE", "ADAMANT", "NAUGHTY",
    "BOLD", "DOCILE", "RELAXED", "IMPISH", "LAX",
    "TIMID", "HASTY", "SERIOUS", "JOLLY", "NAIVE",
    "MODEST", "MILD", "QUIET", "BASHFUL", "RASH",
    "CALM", "GENTLE", "SASSY", "CAREFUL", "QUIRKY"
]

# Opções de música de encontro
MUSIC_OPTIONS = [
    ("Standard Male", "TRAINER_ENCOUNTER_MUSIC_MALE"),
    ("Standard Female", "TRAINER_ENCOUNTER_MUSIC_FEMALE"),
    ("Girl/Tuber/Young Couple", "TRAINER_ENCOUNTER_MUSIC_GIRL"),
    ("Suspicious", "TRAINER_ENCOUNTER_MUSIC_SUSPICIOUS"),
    ("Intense", "TRAINER_ENCOUNTER_MUSIC_INTENSE"),
    ("Cool", "TRAINER_ENCOUNTER_MUSIC_COOL"),
    ("Aqua", "TRAINER_ENCOUNTER_MUSIC_AQUA"),
    ("Magma", "TRAINER_ENCOUNTER_MUSIC_MAGMA"),
    ("Swimmer", "TRAINER_ENCOUNTER_MUSIC_SWIMMER"),
    ("Twins/Others", "TRAINER_ENCOUNTER_MUSIC_TWINS"),
    ("Elite Four", "TRAINER_ENCOUNTER_MUSIC_ELITE_FOUR"),
    ("Hiker/Others", "TRAINER_ENCOUNTER_MUSIC_HIKER"),
    ("Interviewer", "TRAINER_ENCOUNTER_MUSIC_INTERVIEWER"),
    ("Rich Boy/Gentleman", "TRAINER_ENCOUNTER_MUSIC_RICH")
]

POKEMON_SPRITE_TABLE_ADDRESS = 0x08000128
POKEMON_PALETTE_TABLE_ADDRESS = 0x08000130
POKEMON_SPRITE_SIZE = (64 * 64) // 2  # 4bpp, 2048 bytes para sprites 64x64
POKEMON_PALETTE_SIZE = 0x20  # 32 bytes = 16 cores

class TrainerEditorUI:
    def __init__(self, root):
        self.root = root
        self.BASE_DIR = None
        self.ROM_PATH = None
        self.root.title("CFRU Trainer Editor")
        self.root.geometry("500x300")
        
        self.TRAINER_DATA_PATH = None
        self.TRAINER_PARTIES_PATH = None
        self.OPPONENTS_PATH = None
        self.SPECIES_PATH = None
        self.MOVES_PATH = None
        self.ITEMS_PATH = None
        self.TRAINER_CLASSES_PATH = None
        self.EASY_TEXT_PATH = None
        
        # Sprite viewing variables
        self.SPRITE_WIDTH = 64
        self.SPRITE_HEIGHT = 64
        self.SPRITE_SIZE = (self.SPRITE_WIDTH * self.SPRITE_HEIGHT) // 2  # 4bpp, 2048 bytes
        self.PALETTE_SIZE = 0x20  # 32 bytes = 16 cores
        self.PALETTE_ENTRIES = 16  # 16 cores na paleta
        self.sprite_img = None
        self.tk_img = None
        
        self.pokemon_sprite_addresses = []
        self.pokemon_palette_addresses = []
        self.pokemon_sprite_images = []  # Para armazenar as imagens dos sprites
        self.pokemon_sprite_labels = []  # Para armazenar os labels dos sprites
        
        # Edit Party Funcs
        self.editing_pokemon_mode = False
        self.current_editing_pokemon = None
        
        self.SPRITE_TABLE_ADDRESS = 0x823957C  # Endereço da tabela de sprites
        self.PALETTE_TABLE_ADDRESS = 0x8239A1C  # Endereço da tabela de paletas
        self.ENTRY_SIZE = 8  # Cada entrada na tabela tem 8 bytes
        
        # Define party_type_var before setting up UI
        self.party_type_var = tk.IntVar(value=4)
        self.party_type_var.trace('w', self.update_party_fields)
        
        self.show_folder_selection()
        
    def read_sprite_table(self):
        """Lê a tabela de sprites da ROM e retorna lista de endereços"""
        sprite_addresses = []
        try:
            with open(self.ROM_PATH, 'rb') as rom_file:
                offset = self.gba_addr_to_file_offset(self.SPRITE_TABLE_ADDRESS)
                rom_file.seek(offset)
                
                # Lê entradas até encontrar um endereço nulo (0)
                while True:
                    entry = rom_file.read(self.ENTRY_SIZE)
                    if not entry or len(entry) < 4:
                        break
                        
                    # Os primeiros 4 bytes são o endereço do sprite (little-endian)
                    sprite_addr = struct.unpack('<I', entry[:4])[0]
                    if sprite_addr == 0:
                        break
                        
                    sprite_addresses.append(sprite_addr)
        except Exception as e:
            print(f"Error reading sprite table: {e}")
            # Fallback para lista pré-definida se houver erro
            sprite_addresses = [
                0x8E48D58, 0x8E490BC, 0x8E49444, 0x8E497A8, 0x8E49A94, 0x8E49E58,
                # ... (restante da lista original)
            ]
        
        return sprite_addresses

    def read_palette_table(self):
        """Lê a tabela de paletas da ROM e retorna lista de endereços"""
        palette_addresses = []
        try:
            with open(self.ROM_PATH, 'rb') as rom_file:
                offset = self.gba_addr_to_file_offset(self.PALETTE_TABLE_ADDRESS)
                rom_file.seek(offset)
                
                # Lê entradas até encontrar um endereço nulo (0)
                while True:
                    entry = rom_file.read(self.ENTRY_SIZE)
                    if not entry or len(entry) < 4:
                        break
                        
                    # Os primeiros 4 bytes são o endereço da paleta (little-endian)
                    palette_addr = struct.unpack('<I', entry[:4])[0]
                    if palette_addr == 0:
                        break
                        
                    palette_addresses.append(palette_addr)
        except Exception as e:
            print(f"Error reading palette table: {e}")
            # Fallback para lista pré-definida se houver erro
            palette_addresses = [
                0x8E49094, 0x8E4941C, 0x8E49780, 0x8E49A6C, 0x8E49E30, 0x8E4A2FC,
                # ... (restante da lista original)
            ]
        
        return palette_addresses
        
    def gba_addr_to_file_offset(self, addr):
        return addr - 0x08000000
    
    def gba_to_rgba(self, gba_color):
        r5 = gba_color & 0x1F
        g5 = (gba_color >> 5) & 0x1F
        b5 = (gba_color >> 10) & 0x1F

        # Conversão precisa 5 bits → 8 bits
        red = (r5 * 255) // 31
        green = (g5 * 255) // 31
        blue = (b5 * 255) // 31
        alpha = 255

        return (red, green, blue, alpha)
    
    def decompress_lz77(self, compressed_data):
        """Descomprime dados no formato LZ77 usado em ROMs GBA"""
        if len(compressed_data) < 4 or compressed_data[0] != 0x10:
            return compressed_data  # Não é LZ77, retorna dados originais
        
        # Extrai o tamanho descomprimido (3 bytes little-endian)
        decompressed_size = compressed_data[1] | (compressed_data[2] << 8) | (compressed_data[3] << 16)
        decompressed = bytearray()
        src_index = 4
        
        while len(decompressed) < decompressed_size:
            if src_index >= len(compressed_data):
                break
                
            flags = compressed_data[src_index]
            src_index += 1
            
            for i in range(8):
                if len(decompressed) >= decompressed_size:
                    break
                    
                if flags & (0x80 >> i):
                    # Dados comprimidos
                    if src_index + 1 >= len(compressed_data):
                        break
                        
                    num = (compressed_data[src_index] << 8) | compressed_data[src_index+1]
                    src_index += 2
                    disp = (num & 0x0FFF) + 1
                    count = (num >> 12) + 3
                    
                    # Copia dados da janela deslizante
                    start_pos = len(decompressed) - disp
                    for j in range(count):
                        if start_pos + j < 0:
                            decompressed.append(0)
                        elif start_pos + j < len(decompressed):
                            decompressed.append(decompressed[start_pos + j])
                        else:
                            decompressed.append(0)
                else:
                    # Dados não comprimidos
                    if src_index >= len(compressed_data):
                        break
                    decompressed.append(compressed_data[src_index])
                    src_index += 1
                    
        return bytes(decompressed)
    
    def read_palette(self, palette_gba_addr):
        """Lê a paleta do treinador da ROM"""
        if not self.ROM_PATH or not self.ROM_PATH.exists():
            return None
            
        try:
            with open(self.ROM_PATH, 'rb') as rom_file:
                offset = self.gba_addr_to_file_offset(palette_gba_addr)
                if offset < 0:
                    return None
                    
                rom_file.seek(offset)
                header = rom_file.read(4)
                
                if header[0] == 0x10:  # LZ77 compressed
                    # Lê o tamanho comprimido estimado (máximo)
                    rom_file.seek(offset)
                    compressed_data = rom_file.read(128)  # Suficiente para paletas
                    pal_data = self.decompress_lz77(compressed_data)
                    pal_data = pal_data[:self.PALETTE_SIZE]  # Garante tamanho máximo
                else:
                    # Dados não comprimidos
                    rom_file.seek(offset)
                    pal_data = rom_file.read(self.PALETTE_SIZE)
                
                # Preenche se necessário
                if len(pal_data) < self.PALETTE_SIZE:
                    pal_data += b'\x00' * (self.PALETTE_SIZE - len(pal_data))
                
                palette = []
                for i in range(0, self.PALETTE_SIZE, 2):
                    color_val = struct.unpack("<H", pal_data[i:i+2])[0]
                    palette.append(self.gba_to_rgba(color_val))
                
                return palette
        except Exception as e:
            print(f"Error reading palette: {e}")
            return None
    
    def decode_4bpp_tiled(self, sprite_bytes, palette):
        """Decodifica sprites no formato tile do GBA (8x8 blocos)"""
        img = Image.new("RGBA", (self.SPRITE_WIDTH, self.SPRITE_HEIGHT))
        pixels = img.load()
        
        # Tamanho do tile (8x8 pixels)
        tile_width = 8
        tile_height = 8
        tiles_per_row = self.SPRITE_WIDTH // tile_width
        bytes_per_tile = (tile_width * tile_height) // 2
        
        # Verifica dados suficientes
        if len(sprite_bytes) < (64 * bytes_per_tile):
            sprite_bytes += bytes([0] * (64 * bytes_per_tile - len(sprite_bytes)))
        
        for tile_index in range(64):  # 8x8 tiles para 64x64 sprite
            tile_y = (tile_index // tiles_per_row) * tile_height
            tile_x = (tile_index % tiles_per_row) * tile_width
            
            # Obtém dados do tile
            start = tile_index * bytes_per_tile
            end = start + bytes_per_tile
            tile_data = sprite_bytes[start:end]
            
            # Decodifica cada linha
            for y in range(tile_height):
                for x in range(0, tile_width, 2):
                    byte_index = y * (tile_width // 2) + (x // 2)
                    if byte_index < len(tile_data):
                        byte = tile_data[byte_index]
                        idx1 = byte & 0x0F
                        idx2 = (byte >> 4) & 0x0F
                        
                        px = tile_x + x
                        py = tile_y + y
                        
                        # Índice 0 é transparente
                        pixels[px, py] = palette[idx1] if idx1 != 0 else (0, 0, 0, 0)
                        pixels[px+1, py] = palette[idx2] if idx2 != 0 else (0, 0, 0, 0)
        
        return img
    
    def read_sprite_data(self, sprite_gba_addr):
        """Lê os dados do sprite da ROM com tratamento de erro melhorado"""
        if not self.ROM_PATH or not self.ROM_PATH.exists():
            return None
            
        try:
            with open(self.ROM_PATH, 'rb') as rom_file:
                offset = self.gba_addr_to_file_offset(sprite_gba_addr)
                if offset < 0 or offset >= os.path.getsize(self.ROM_PATH):
                    raise ValueError(f"Invalid sprite offset: 0x{offset:X}")
                    
                rom_file.seek(offset)
                header = rom_file.read(4)
                
                if header[0] == 0x10:  # LZ77 compressed
                    rom_file.seek(offset)
                    compressed_data = rom_file.read(4096)  # Suficiente para sprites
                    sprite_data = self.decompress_lz77(compressed_data)
                else:
                    rom_file.seek(offset)
                    sprite_data = rom_file.read(self.SPRITE_SIZE)
                
                if len(sprite_data) < self.SPRITE_SIZE:
                    sprite_data += bytes([0] * (self.SPRITE_SIZE - len(sprite_data)))
                elif len(sprite_data) > self.SPRITE_SIZE:
                    sprite_data = sprite_data[:self.SPRITE_SIZE]
                
                return sprite_data
        except Exception as e:
            print(f"Error reading sprite data at 0x{sprite_gba_addr:X}: {e}")
            return None
           
    def show_folder_selection(self):
        """Mostra a tela inicial para selecionar a pasta do projeto"""
        self.clear_main_window()
        
        title_label = ttk.Label(self.root, text="CFRU Trainer Editor", font=('Helvetica', 14, 'bold'))
        title_label.pack(pady=20)
        
        desc_label = ttk.Label(self.root, text="Select your CFRU project folder:")
        desc_label.pack(pady=10)
        
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="Select Folder", command=self.select_project_folder).pack(pady=5)
        ttk.Button(btn_frame, text="Exit", command=self.root.quit).pack(pady=5)
        
        # Centraliza a janela
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def select_project_folder(self):
        """Abre o diálogo para selecionar a pasta do projeto"""
        folder_path = filedialog.askdirectory(title="Select CFRU Project Folder")
        if folder_path:
            self.BASE_DIR = Path(folder_path)
            self.verify_project_structure()
            
    def verify_project_structure(self):
        """Verifica se a pasta selecionada tem a estrutura esperada do CFRU"""
        required_paths = [
            "src/Tables/trainer_data.c",
            "src/Tables/trainer_parties.h",
            "include/constants/opponents.h",
            "include/constants/species.h",
            "include/constants/moves.h",
            "include/constants/items.h",
            "include/constants/trainer_classes.h",
            "include/easy_text.h",
        ]
        
        missing_paths = []
        for rel_path in required_paths:
            if not (self.BASE_DIR / rel_path).exists():
                missing_paths.append(rel_path)
        
        if missing_paths:
            messagebox.showerror(
                "Error", 
                f"The selected folder doesn't appear to be a valid CFRU project.\n\nMissing paths:\n- " + 
                "\n- ".join(missing_paths)
            )
            self.show_folder_selection()
        else:
            # Pedimos ao usuário para selecionar a ROM BPRE0.gba
            self.prompt_for_rom()
            
    def prompt_for_rom(self):
        """Pede ao usuário para selecionar la ROM BPRE0.gba"""
        rom_path = filedialog.askopenfilename(
            title="Select BPRE0.gba ROM",
            filetypes=[("GBA ROMs", "*.gba"), ("All files", "*.*")]
        )
        
        if rom_path:
            self.ROM_PATH = Path(rom_path)
            if self.ROM_PATH.name.upper() != "BPRE0.GBA":
                messagebox.showwarning("Warning", "The selected ROM doesn't appear to be BPRE0.gba")
            
            self.initialize_editor()
            
    def clear_main_window(self):
        """Remove todos os widgets da janela principal"""
        for widget in self.root.winfo_children():
            widget.destroy()
            
    def initialize_editor(self):
        """Inicializa o editor após a pasta ser selecionada"""
        self.clear_main_window()
        self.root.geometry("1200x800")
        self.root.state('zoomed')
        
        # Define os paths agora que BASE_DIR está definido
        self.TRAINER_DATA_PATH = self.BASE_DIR / "src" / "Tables" / "trainer_data.c"
        self.TRAINER_PARTIES_PATH = self.BASE_DIR / "src" / "Tables" / "trainer_parties.h"
        self.OPPONENTS_PATH = self.BASE_DIR / "include" / "constants" / "opponents.h"
        self.SPECIES_PATH = self.BASE_DIR / "include" / "constants" / "species.h"
        self.MOVES_PATH = self.BASE_DIR / "include" / "constants" / "moves.h"
        self.ITEMS_PATH = self.BASE_DIR / "include" / "constants" / "items.h"
        self.TRAINER_CLASSES_PATH = self.BASE_DIR / "include" / "constants" / "trainer_classes.h"
        self.EASY_TEXT_PATH = self.BASE_DIR / "include" / "easy_text.h"
        self.TRAINER_PIC_TABLES_PATH = self.BASE_DIR / "src" / "Tables" / "trainer_pic_tables.c"
        self.SPRITES_DIR = self.BASE_DIR / "graphics" / "Other" / "PokeSprites"
        
         # Carrega as tabelas de sprites e paletas
        self.SPRITE_ADDRESSES_GBA = self.read_sprite_table()
        self.PALETTE_ADDRESSES_GBA = self.read_palette_table()
        
        # Carrega as tabelas de sprites e paletas dos Pokémon
        self.load_pokemon_sprite_tables()
        
        # Restante da inicialização
        self.load_initial_data()
        self.setup_styles()
        
        # Carrega o mapeamento de espécies
        self.load_species_mapping()
        
        self.party_type_var = tk.IntVar(value=4)
        self.party_type_var.trace('w', self.update_party_fields)
        
        self.setup_ui()
        self.populate_trainer_tree()
    
    def load_pokemon_sprite_tables(self):
        """Carrega as tabelas de sprites e paletas dos Pokémon da ROM"""
        try:
            # Lê o ponteiro para a tabela de sprites
            sprite_table_ptr = self.read_pointer(POKEMON_SPRITE_TABLE_ADDRESS)
            print(f"Sprite table pointer: 0x{sprite_table_ptr:X}")
            
            # Lê o ponteiro para a tabela de paletas
            palette_table_ptr = self.read_pointer(POKEMON_PALETTE_TABLE_ADDRESS)
            print(f"Palette table pointer: 0x{palette_table_ptr:X}")
            
            # Lê a tabela de sprites (cada entrada tem 8 bytes: 4 bytes de endereço + 4 bytes de info)
            self.pokemon_sprite_addresses = self.read_sprite_address_table(sprite_table_ptr)
            
            # Lê a tabela de paletas (cada entrada tem 8 bytes: 4 bytes de endereço + 4 bytes de info)
            self.pokemon_palette_addresses = self.read_sprite_address_table(palette_table_ptr)
            
            print(f"Loaded {len(self.pokemon_sprite_addresses)} Pokémon sprite addresses")
            print(f"Loaded {len(self.pokemon_palette_addresses)} Pokémon palette addresses")
            
            # Debug: mostra os primeiros endereços
            for i in range(min(10, len(self.pokemon_sprite_addresses))):
                print(f"Sprite {i}: 0x{self.pokemon_sprite_addresses[i]:X}")
            for i in range(min(10, len(self.pokemon_palette_addresses))):
                print(f"Palette {i}: 0x{self.pokemon_palette_addresses[i]:X}")
            
        except Exception as e:
            print(f"Error loading Pokémon sprite tables: {e}")
            # Fallback para evitar quebrar o programa
            self.pokemon_sprite_addresses = []
            self.pokemon_palette_addresses = []

    def read_pointer(self, address):
        """Lê um ponteiro de 4 bytes da ROM e converte para endereço GBA"""
        try:
            with open(self.ROM_PATH, 'rb') as rom_file:
                offset = self.gba_addr_to_file_offset(address)
                rom_file.seek(offset)
                pointer_data = rom_file.read(4)
                if len(pointer_data) == 4:
                    pointer = struct.unpack('<I', pointer_data)[0]
                    print(f"Raw pointer at 0x{address:X}: 0x{pointer:X}")
                    return pointer
        except Exception as e:
            print(f"Error reading pointer at 0x{address:X}: {e}")
        return 0
        
    def read_sprite_address_table(self, table_address):
        """Lê uma tabela de endereços de sprites/paletas (8 bytes por entrada)"""
        addresses = []
        try:
            with open(self.ROM_PATH, 'rb') as rom_file:
                offset = self.gba_addr_to_file_offset(table_address)
                rom_file.seek(offset)
                
                # Lê entradas até encontrar um endereço nulo (0)
                entry_count = 0
                while True:
                    entry_data = rom_file.read(8)
                    if not entry_data or len(entry_data) < 8:
                        break
                    
                    # Os primeiros 4 bytes são o endereço do sprite/paleta
                    sprite_addr = struct.unpack('<I', entry_data[:4])[0]
                    
                    # Verifica se é um endereço válido (não nulo)
                    if sprite_addr == 0:
                        # Pula esta entrada mas continua lendo as próximas
                        addresses.append(0)  # Adiciona zero para manter o índice
                        entry_count += 1
                        continue
                    
                    # Verifica se o endereço está dentro dos limites razoáveis da ROM
                    if sprite_addr < 0x08000000 or sprite_addr > 0x09FFFFFF:
                        print(f"Invalid sprite address: 0x{sprite_addr:X}")
                        break
                    
                    addresses.append(sprite_addr)
                    entry_count += 1
                    
                    # Limita a um número máximo de entradas para evitar loops infinitos
                    if entry_count > 1500:  # Número máximo de espécies
                        break
                        
        except Exception as e:
            print(f"Error reading sprite address table at 0x{table_address:X}: {e}")
        
        return addresses
    
    def load_initial_data(self):
        """Carrega todos os dados iniciais necessários"""
        self.TRAINER_CLASSES = self.load_trainer_classes()
        self.VALID_SPECIES = self.load_file_defines(self.SPECIES_PATH, 'SPECIES_')
        self.VALID_MOVES = self.load_file_defines(self.MOVES_PATH, 'MOVE_')
        self.VALID_ITEMS = self.load_file_defines(self.ITEMS_PATH, 'ITEM_')
        self.TEXT_DEFINITIONS, self.CHAR_TO_DEFINE = self.load_easy_text_definitions()
        
        self.trainer_lines = self.read_file(self.TRAINER_DATA_PATH)
        self.party_lines = self.read_file(self.TRAINER_PARTIES_PATH)
        self.opponents_lines = self.read_file(self.OPPONENTS_PATH)
        
        # DEBUG: Salva o conteúdo analisado para verificação
        with open('debug_trainers.txt', 'w', encoding='utf-8') as f:
            f.write("\n".join([f"{k}: {v}" for k, v in self.parse_trainers().items()]))
        
        with open('debug_parties.txt', 'w', encoding='utf-8') as f:
            f.write("\n".join([f"{k}: {v}" for k, v in self.parse_trainer_parties().items()]))
        
        # Carrega os dados normalmente
        self.trainers = self.parse_trainers()
        self.parties = self.parse_trainer_parties()
        self.opponent_name_to_id, self.opponent_id_to_name = self.parse_opponents_with_ids()
        
        # Carrega species na ordem do arquivo
        self.species_list, self.species_display_list, self.species_mapping = self.load_species_ordered()
        self.items_list = sorted([i.replace('ITEM_', '') for i in self.VALID_ITEMS])
        self.moves_list = sorted([m.replace('MOVE_', '') for m in self.VALID_MOVES])
        
        self.current_editing_id = None
        self.new_parties = {}
        self.modified = False

    def load_species_ordered(self):
        """Carrega as espécies na mesma ordem do arquivo species.h"""
        full_names = []
        display_names = []
        mapping = {}
        
        try:
            with open(self.SPECIES_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("#define SPECIES_"):
                        parts = line.split()
                        if len(parts) >= 2:
                            full_name = parts[1]
                            if full_name.startswith("SPECIES_"):
                                display_name = full_name.replace("SPECIES_", "")
                                full_names.append(full_name)
                                display_names.append(display_name)
                                mapping[display_name] = full_name
        except Exception as e:
            print(f"Error loading ordered species: {e}")
            # Fallback para o método antigo se houver erro
            full_names = list(self.VALID_SPECIES)
            display_names = [s.replace('SPECIES_', '') for s in full_names]
            mapping = {display: full for display, full in zip(display_names, full_names)}
        
        return full_names, display_names, mapping
        
    def parse_trainer_parties(self):
        """Analisa o arquivo de parties e retorna um dicionário com os dados"""
        parties = {}
        current_party = None
        current_pokemon = None
        i = 0
        n = len(self.party_lines)
        
        while i < n:
            line = self.party_lines[i].strip()
            
            # Padrão: static const struct ... party_name[] = {
            if ('static const struct' in line or 'const struct' in line) and '[] = {' in line:
                # Extrai o nome da party
                party_name = line.split('[] = {')[0].split()[-1]
                
                # Extrai o nome da estrutura
                struct_match = re.search(r'struct\s+(\w+)', line)
                if struct_match:
                    struct_name = struct_match.group(1)
                    party_type = self.get_party_type_from_struct(struct_name)
                else:
                    # Fallback - tenta determinar pelo conteúdo da linha
                    if 'ItemCustomMoves' in line:
                        party_type = 4
                    elif 'NoItemCustomMoves' in line:
                        party_type = 3
                    elif 'ItemDefaultMoves' in line:
                        party_type = 2
                    elif 'NoItemDefaultMoves' in line:
                        party_type = 1
                    else:
                        party_type = 4  # Default
                
                current_party = {
                    'name': party_name,
                    'type': party_type,
                    'pokemons': []
                }
                i += 1
                continue
            
            # Se estamos dentro de uma party
            if current_party:
                # Início de um novo Pokémon
                if line.startswith('{'):
                    current_pokemon = {
                        'party_type': current_party['type'],
                        'moves': ['MOVE_NONE', 'MOVE_NONE', 'MOVE_NONE', 'MOVE_NONE'],
                        'ivs': ['0', '0', '0', '0', '0', '0'],
                        'evs': ['0', '0', '0', '0', '0', '0']
                    }
                    i += 1
                    continue
                
                # Processa campos do Pokémon
                if current_pokemon is not None:
                    # Fim do Pokémon
                    if line.startswith('},') or line.startswith('}'):
                        current_party['pokemons'].append(current_pokemon)
                        current_pokemon = None
                        i += 1
                        continue
                    
                    # Campos com valores simples
                    if '.lvl =' in line:
                        current_pokemon['level'] = line.split('=')[1].strip().rstrip(',')
                    elif '.species =' in line:
                        current_pokemon['species'] = line.split('=')[1].strip().rstrip(',')
                    elif '.heldItem =' in line:
                        current_pokemon['item'] = line.split('=')[1].strip().rstrip(',')
                    elif '.ability =' in line:
                        current_pokemon['ability'] = line.split('=')[1].strip().rstrip(',')
                    elif '.nature =' in line:
                        current_pokemon['nature'] = line.split('=')[1].strip().rstrip(',')
                    elif '.teraType =' in line:
                        current_pokemon['tera_type'] = line.split('=')[1].strip().rstrip(',')
                    
                    # Campos com arrays
                    elif '.moves = {' in line:
                        moves = self.parse_array_field(i, 'moves')
                        # Preenche os 4 slots de movimentos
                        for j in range(4):
                            if j < len(moves):
                                current_pokemon['moves'][j] = moves[j]
                            else:
                                current_pokemon['moves'][j] = 'MOVE_NONE'
                        i = self.skip_to_array_end(i)
                    
                    elif '.ivSpread = {' in line:
                        ivs = self.parse_array_field(i, 'ivSpread')
                        # Garante 6 valores
                        for j in range(6):
                            if j < len(ivs):
                                current_pokemon['ivs'][j] = ivs[j]
                            else:
                                current_pokemon['ivs'][j] = '0'
                        i = self.skip_to_array_end(i)
                    
                    elif '.evSpread = {' in line:
                        evs = self.parse_array_field(i, 'evSpread')
                        # Garante 6 valores
                        for j in range(6):
                            if j < len(evs):
                                current_pokemon['evs'][j] = evs[j]
                            else:
                                current_pokemon['evs'][j] = '0'
                        i = self.skip_to_array_end(i)
                
                # Fim da party
                elif line.startswith('};'):
                    parties[current_party['name']] = current_party
                    current_party = None
            
            i += 1
        
        return parties
    
    def skip_to_array_end(self, start_index):
        """Pula para o final de um array"""
        i = start_index
        n = len(self.party_lines)
        brace_count = 0
        
        while i < n:
            line = self.party_lines[i].strip()
            
            if '{' in line:
                brace_count += line.count('{')
            if '}' in line:
                brace_count -= line.count('}')
                if brace_count <= 0:
                    return i
            
            i += 1
        
        return i
    
    def parse_array_field(self, start_index, field_name):
        """Analisa um campo de array como moves, ivSpread, evSpread"""
        values = []
        i = start_index
        n = len(self.party_lines)
        
        # Encontra a linha que começa o array
        while i < n:
            line = self.party_lines[i].strip()
            if f'.{field_name} = {{' in line:
                # Verifica se está em uma linha só
                if '}' in line:
                    # Array em uma linha: .moves = {MOVE_MEGAHORN, MOVE_EARTHQUAKE, MOVE_COUNTER, MOVE_ROCKTOMB},
                    array_content = line.split('{', 1)[1].split('}', 1)[0]
                    values = [v.strip() for v in array_content.split(',') if v.strip()]
                    break
                else:
                    # Array multi-linha
                    i += 1
                    while i < n:
                        line = self.party_lines[i].strip()
                        if line.startswith('}'):
                            break
                        # Remove vírgulas e espaços, mantém apenas valores válidos
                        value = line.strip().rstrip(',')
                        if value and not value.startswith('//'):  # Ignora comentários
                            values.append(value)
                        i += 1
                    break
            i += 1
        
        return values
    
    def get_party_type_from_struct(self, struct_name):
        """Determina o tipo de party baseado no nome da estrutura"""
        type_map = {
            'TrainerMonNoItemDefaultMoves': 1,
            'TrainerMonItemDefaultMoves': 2,
            'TrainerMonNoItemCustomMoves': 3,
            'TrainerMonItemCustomMoves': 4
        }
        
        return type_map.get(struct_name, 4)  # Default para ItemCustomMoves

    def load_trainer_classes(self):
        """Carrega as classes de treinador, removendo o prefixo 'CLASS_'"""
        classes = []
        try:
            with open(self.TRAINER_CLASSES_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    # Remove comentários e espaços em branco
                    line = line.split('//')[0].strip()
                    
                    if not line:
                        continue  # Ignora linhas vazias
                    
                    # Processa #define CLASS_XXX
                    if line.startswith('#define CLASS_'):
                        parts = line.split()
                        if len(parts) >= 2:
                            # Remove o prefixo "CLASS_" e adiciona apenas o resto
                            class_name = parts[1].replace('CLASS_', '', 1)
                            classes.append(class_name)
                    
                    # Processa enum { CLASS_XXX, ... }
                    elif line.startswith('CLASS_'):
                        class_name = line.split('=')[0].split(',')[0].strip()
                        class_name = class_name.replace('CLASS_', '', 1)
                        classes.append(class_name)
                    
                    # Processa enum { CLASS_XXX = value, ... }
                    elif 'enum' in line and '{' in line:
                        # Multilinha - continua lendo até encontrar }
                        while True:
                            line = f.readline()
                            if not line or '}' in line:
                                break
                            line = line.split('//')[0].strip()
                            if line.startswith('CLASS_'):
                                class_name = line.split('=')[0].split(',')[0].strip()
                                class_name = class_name.replace('CLASS_', '', 1)
                                classes.append(class_name)
        
        except Exception as e:
            print(f"Error loading trainer classes: {e}")
            classes = list(CLASS_NAME_TO_ID.keys()) if 'CLASS_NAME_TO_ID' in globals() else []
        
        # Remove duplicatas e ordena
        return sorted(list(set(classes)))
    
    def load_file_defines(self, path, prefix):
        """Carrega defines de um arquivo com um prefixo específico"""
        defines = set()
        try:
            with open(path, 'r', encoding='utf-8') as f:  # path já vem com self.
                for line in f:
                    if f'#define {prefix}' in line:
                        defines.add(line.split()[1])
        except Exception as e:
            print(f"Error loading {path}: {e}")
            defines = {f'{prefix}EXAMPLE1', f'{prefix}EXAMPLE2'}  # Fallback
        return defines
    
    def load_easy_text_definitions(self):
        """Carrega definições de texto do arquivo easy_text.h, incluindo maiúsculas e minúsculas"""
        text_map = {}
        char_to_define = {' ': '_SPACE'}
        
        try:
            with open(self.EASY_TEXT_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    if '#define _' in line and '0x' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            define = parts[1]
                            value = parts[2]
                            text_map[define] = value
                            
                            # Mapeia caracteres para seus defines
                            if define.startswith('_') and len(define) == 2:
                                char = define[1]
                                if char.isalpha():
                                    char_to_define[char] = define
        except Exception as e:
            print(f"Error loading easy_text.h: {e}")
        
        return text_map, char_to_define
    
    def read_file(self, path):
        """Lê um arquivo e retorna suas linhas"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.readlines()
        except Exception as e:
            print(f"Error reading {path}: {e}")
            return []
    
    def parse_trainers(self):
        """Analisa o arquivo de treinadores"""
        trainers = {}
        current_trainer = None
        
        for i, line in enumerate(self.trainer_lines):
            line = line.strip()
            
            # Aceita qualquer coisa dentro dos colchetes (ex: [TRAINER_NONE])
            if line.startswith('[') and '] = {' in line:
                trainer_id = line.split('[')[1].split(']')[0].strip()
                current_trainer = {
                    'id': trainer_id, 
                    'start_line': i, 
                    'data': [],
                    'party_name': None,
                    'party_type': None
                }
            elif current_trainer and line.startswith('.'):
                current_trainer['data'].append(line)
                # Captura o nome e tipo da party
                if '.party = {' in line:
                    # Exemplo: .party =  { .NoItemDefaultMoves = sParty_Rival_Starter_1 },
                    match = re.search(r'\.(\w+) = (\w+)', line)
                    if match:
                        union_field = match.group(1)
                        party_name = match.group(2)
                        # Mapeia o campo da union para o tipo de party
                        if union_field == 'NoItemDefaultMoves':
                            current_trainer['party_type'] = 1
                        elif union_field == 'ItemDefaultMoves':
                            current_trainer['party_type'] = 2
                        elif union_field == 'NoItemCustomMoves':
                            current_trainer['party_type'] = 3
                        elif union_field == 'ItemCustomMoves':
                            current_trainer['party_type'] = 4
                        current_trainer['party_name'] = party_name
            elif line == '},' and current_trainer:
                current_trainer['end_line'] = i
                trainers[current_trainer['id']] = current_trainer
                current_trainer = None
        
        return trainers
    
    def parse_opponents_with_ids(self):
        """Analisa o arquivo de oponentes retornando mapeamentos nome->id e id->nome"""
        name_to_id = {}
        id_to_name = {}
        
        for line in self.opponents_lines:
            line = line.strip()
            if line.startswith('#define') and not line.startswith('//'):
                parts = line.split()
                if len(parts) >= 3:
                    name = parts[1]
                    try:
                        value = parts[2].split('//')[0].strip()
                        if value.startswith('0x'):
                            trainer_id = int(value[2:], 16)
                        else:
                            trainer_id = int(value)
                        
                        name_to_id[name] = trainer_id
                        id_to_name[trainer_id] = name
                    except ValueError:
                        continue
        return name_to_id, id_to_name

    def easy_text_to_normal(self, easy_text):
        """Converte texto no formato easy_text para texto normal"""
        if not easy_text or easy_text == "{}":
            return ""
        
        chars = easy_text.strip('{}').split(',')
        normal_text = []
        
        for char_def in chars:
            char_def = char_def.strip()
            if char_def in self.TEXT_DEFINITIONS:
                for char, define in self.CHAR_TO_DEFINE.items():
                    if define == char_def:
                        normal_text.append(char)
                        break
            elif char_def == '_SPACE':
                normal_text.append(' ')
            elif char_def == '_END':
                break
        
        return ''.join(normal_text)

    def convert_to_easy_text(self, text):
        """Converte texto normal para o formato easy_text, diferenciando maiúsculas de minúsculas"""
        text_array = []
        for char in text:
            if char == ' ':
                text_array.append("_SPACE")
            elif char.isupper() and f'_{char}' in self.TEXT_DEFINITIONS:
                text_array.append(f'_{char}')
            elif char.islower() and f'_{char}' in self.TEXT_DEFINITIONS:
                text_array.append(f'_{char}')
            elif char in self.CHAR_TO_DEFINE:
                text_array.append(self.CHAR_TO_DEFINE[char])
            else:
                # Fallback para espaço se o caractere não for encontrado
                text_array.append("_SPACE")
        
        text_array.append("_END")
        return "{" + ", ".join(text_array) + "}"

    def save_files(self):
        """Salva todas as alterações nos arquivos"""
        try:
            # Limpa dados antigos antes de salvar
            self.clear_old_data_before_save()
            
            # Debug - mostra o que será salvo
            self.print_opponents_changes()
            
            self.save_trainer_data_file()
            self.save_opponents_file()
            self.save_parties_file()
            self.modified = False
            messagebox.showinfo("Success", "All files saved successfully!")
            
            # Recarrega os dados após salvar
            self.refresh_data()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save files: {str(e)}")
            
    def print_opponents_changes(self):
        """Método auxiliar para debug - mostra as alterações que serão salvas"""
        print("\nOpponents to be saved:")
        for name, id in self.opponent_name_to_id.items():
            print(f"{name}: {id}")
        print(f"Max ID: {max(self.opponent_name_to_id.values()) if self.opponent_name_to_id else 0}")

    def save_trainer_data_file(self):
        """Salva as alterações no arquivo trainer_data.c com o nome do treinador nos colchetes"""
        new_lines = []
        i = 0
        n = len(self.trainer_lines)
        inside_stevebels_block = False
        trainers_added = False
        processed_trainers = set()  # Para rastrear quais treinadores já foram processados
        
        while i < n:
            line = self.trainer_lines[i]
            
            # Verifica se estamos entrando no bloco EXPAND_TRAINERS
            if "#ifdef EXPAND_TRAINERS" in line:
                inside_stevebels_block = True
                new_lines.append(line)
                i += 1
                continue
            
            # Dentro do bloco EXPAND_TRAINERS, adicionamos os novos treinadores antes do }; ou #endif
            if inside_stevebels_block and not trainers_added:
                if line.strip() in ["};", "#endif"]:
                    # Adiciona todos os treinadores modificados antes do fechamento
                    for name, trainer in self.trainers.items():
                        if name not in processed_trainers:
                            # Adiciona com o nome do define entre colchetes
                            new_lines.append(f"\t[{name}] = {{\n")
                            for data_line in trainer['data']:
                                new_lines.append(f"\t    {data_line}\n")
                            new_lines.append("\t},\n")
                            processed_trainers.add(name)
                    
                    trainers_added = True
            
            # Verifica se é o início de uma definição de treinador
            if line.strip().startswith('[') and '] = {' in line:
                trainer_id = line.split('[')[1].split(']')[0].strip()
                
                # Verifica se este treinador foi modificado
                if trainer_id in self.trainers:
                    trainer = self.trainers[trainer_id]
                    
                    # Adiciona a nova definição do treinador com o nome entre colchetes
                    new_lines.append(f"[{trainer_id}] = {{\n")
                    
                    # Adiciona todos os campos do treinador atualizados
                    for data_line in trainer['data']:
                        new_lines.append(f"    {data_line}\n")
                    
                    new_lines.append("},\n")
                    processed_trainers.add(trainer_id)
                    
                    # Avança até o final da definição atual no arquivo original
                    while i < n and not self.trainer_lines[i].strip().startswith('},'):
                        i += 1
                    i += 1  # Pula a linha '},'
                    continue
                else:
                    # Treinador não modificado, mantém a linha original
                    new_lines.append(line)
                    i += 1
            else:
                # Adiciona a linha original se não for parte de um treinador modificado
                new_lines.append(line)
                i += 1
        
        # Escreve o arquivo com as alterações
        try:
            with open(self.TRAINER_DATA_PATH, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save {self.TRAINER_DATA_PATH}: {str(e)}")
            raise

    def save_opponents_file(self):
        """Salva as alterações no arquivo opponents.h, inserindo novos defines acima do TRAINERS_COUNT"""
        try:
            # Encontra la posição da linha TRAINERS_COUNT
            trainers_count_index = -1
            trainers_count_line = None
            
            for i, line in enumerate(self.opponents_lines):
                if "TRAINERS_COUNT" in line and not line.strip().startswith('//'):
                    trainers_count_index = i
                    trainers_count_line = line
                    break
            
            if trainers_count_index == -1:
                raise ValueError("Could not find TRAINERS_COUNT in opponents.h")
            
            # Encontra o último trainer (com o maior ID)
            last_trainer_name = None
            max_id = -1
            
            for name, trainer_id in self.opponent_name_to_id.items():
                if trainer_id > max_id:
                    max_id = trainer_id
                    last_trainer_name = name
            
            if last_trainer_name is None:
                # Se não houver trainers, usa um fallback
                last_trainer_name = "TRAINER_NONE"
            
            # Atualiza a linha TRAINERS_COUNT
            new_trainers_count_line = f"#define TRAINERS_COUNT ({last_trainer_name} + 1)\n"
            
            # Cria uma cópia das linhas originais
            new_lines = self.opponents_lines.copy()
            
            # Substitui a linha TRAINERS_COUNT
            new_lines[trainers_count_index] = new_trainers_count_line
            
            # Adiciona todas as novas definições antes do TRAINERS_COUNT
            for name, trainer_id in self.opponent_name_to_id.items():
                # Verifica se já não existe no arquivo
                if not any(f"#define {name} " in l for l in self.opponents_lines):
                    new_line = f"#define {name} {trainer_id}\n"
                    new_lines.insert(trainers_count_index, new_line)
            
            # Escreve o arquivo
            with open(self.OPPONENTS_PATH, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save {self.OPPONENTS_PATH}: {str(e)}")
            raise
            
    def get_last_trainer_name(self):
        """Retorna o nome do trainer com o maior ID"""
        last_trainer_name = None
        max_id = -1
        
        for name, trainer_id in self.opponent_name_to_id.items():
            if trainer_id > max_id:
                max_id = trainer_id
                last_trainer_name = name
        
        return last_trainer_name if last_trainer_name else "TRAINER_NONE"

    def save_parties_file(self):
        """Salva as alterações no arquivo trainer_parties.h"""
        new_party_lines = []
        inside_stevebels_block = False
        parties_added = False
        processed_parties = set()  # Para rastrear quais parties já foram processadas
        
        for i, line in enumerate(self.party_lines):
            if "#ifdef EXPAND_TRAINERS" in line:
                inside_stevebels_block = True
                new_party_lines.append(line)
                continue
            
            if inside_stevebels_block and not parties_added:
                if line.strip() == "#endif":
                    # Adiciona todas as parties modificadas antes do #endif
                    for party_name, party_info in self.new_parties.items():
                        if party_name not in processed_parties:
                            new_party_lines.append(f"\nstatic const struct {party_info['struct']} {party_name}[] = {{\n")
                            
                            for pokemon in party_info['data']:
                                new_party_lines.append("    {\n")
                                new_party_lines.append(f"        .lvl = {pokemon['level']},\n")
                                new_party_lines.append(f"        .species = {pokemon['species']},\n")
                                
                                if pokemon['party_type'] in [3, 4]:
                                    new_party_lines.append(f"        .moves = {{{', '.join(pokemon['moves'])}}},\n")
                                
                                if pokemon['party_type'] in [2, 4]:
                                    new_party_lines.append(f"        .heldItem = {pokemon.get('item', 'ITEM_NONE')},\n")
                                
                                if pokemon['party_type'] == 4:
                                    new_party_lines.append(f"        .ability = {pokemon['ability']},\n")
                                    new_party_lines.append(f"        .nature = NATURE_{pokemon['nature']},\n")
                                    new_party_lines.append(f"        .ivSpread = {{{pokemon['ivs']}}},\n")
                                    new_party_lines.append(f"        .evSpread = {{{pokemon['evs']}}},\n")
                                    new_party_lines.append(f"        .teraType = {pokemon['tera_type']},\n")
                                
                                new_party_lines.append("    },\n")
                            new_party_lines.append("};\n")
                            processed_parties.add(party_name)
                    parties_added = True
            
            # Verifica se é uma definição de party existente
            if 'static const struct' in line and '[] = {' in line:
                parts = line.split()
                for part in parts:
                    if part.endswith('[]'):
                        current_party_name = part[:-2]  # Remove o []
                        break
                else:
                    current_party_name = None
                
                # Se esta party foi modificada, substitui completamente
                if current_party_name and current_party_name in self.new_parties:
                    party_info = self.new_parties[current_party_name]
                    
                    # Adiciona a nova definição da party
                    new_party_lines.append(f"\nstatic const struct {party_info['struct']} {current_party_name}[] = {{\n")
                    
                    for pokemon in party_info['data']:
                        new_party_lines.append("    {\n")
                        new_party_lines.append(f"        .lvl = {pokemon['level']},\n")
                        new_party_lines.append(f"        .species = {pokemon['species']},\n")
                        
                        if pokemon['party_type'] in [3, 4]:
                            new_party_lines.append(f"        .moves = {{{', '.join(pokemon['moves'])}}},\n")
                        
                        if pokemon['party_type'] in [2, 4]:
                            new_party_lines.append(f"        .heldItem = {pokemon.get('item', 'ITEM_NONE')},\n")
                        
                        if pokemon['party_type'] == 4:
                            new_party_lines.append(f"        .ability = {pokemon['ability']},\n")
                            new_party_lines.append(f"        .nature = NATURE_{pokemon['nature']},\n")
                            new_party_lines.append(f"        .ivSpread = {{{pokemon['ivs']}}},\n")
                            new_party_lines.append(f"        .evSpread = {{{pokemon['evs']}}},\n")
                            new_party_lines.append(f"        .teraType = {pokemon['tera_type']},\n")
                        
                        new_party_lines.append("    },\n")
                    new_party_lines.append("};\n")
                    processed_parties.add(current_party_name)
                    
                    # Pula as linhas da party antiga
                    j = i + 1
                    while j < len(self.party_lines):
                        if self.party_lines[j].strip() == '};':
                            break
                        j += 1
                    # Continua a partir do final da party
                    continue
            
            new_party_lines.append(line)
        
        # Escreve o arquivo
        try:
            with open(self.TRAINER_PARTIES_PATH, 'w', encoding='utf-8') as f:
                f.writelines(new_party_lines)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save {self.TRAINER_PARTIES_PATH}: {str(e)}")
            raise
            
    def clear_old_data_before_save(self):
        """Limpa dados antigos antes de salvar para evitar duplicatas"""
        # Para trainer_data.c: remove definições antigas de treinadores modificados
        modified_trainers = set(self.trainers.keys())
        
        new_trainer_lines = []
        skip_until_end = False
        current_trainer = None
        
        for line in self.trainer_lines:
            if line.strip().startswith('[') and '] = {' in line:
                trainer_id = line.split('[')[1].split(']')[0].strip()
                if trainer_id in modified_trainers:
                    current_trainer = trainer_id
                    skip_until_end = True
                    continue
            
            if skip_until_end:
                if line.strip() == '},':
                    skip_until_end = False
                    current_trainer = None
                continue
            
            new_trainer_lines.append(line)
        
        self.trainer_lines = new_trainer_lines
        
        # Para trainer_parties.h: remove parties antigas que foram modificadas
        modified_parties = set(self.new_parties.keys())
        
        new_party_lines = []
        skip_party = False
        current_party = None
        
        for line in self.party_lines:
            if 'static const struct' in line and '[] = {' in line:
                parts = line.split()
                for part in parts:
                    if part.endswith('[]'):
                        party_name = part[:-2]
                        if party_name in modified_parties:
                            current_party = party_name
                            skip_party = True
                            break
                
                if skip_party:
                    continue
            
            if skip_party:
                if line.strip() == '};':
                    skip_party = False
                    current_party = None
                continue
            
            new_party_lines.append(line)
        
        self.party_lines = new_party_lines

    def setup_styles(self):
        """Configura os estilos visuais"""
        style = ttk.Style()
        style.configure("Title.TLabel", font=('Helvetica', 10, 'bold'))
        style.configure("Section.TFrame", relief=tk.GROOVE, borderwidth=2)
        style.configure("Section.TLabel", font=('Helvetica', 9, 'bold'))
        style.configure("Blue.TLabelframe.Label", foreground="blue", font=('Helvetica', 9, 'bold'))
        
    def setup_ui(self):
        """Configura a interface do usuário"""
        # Frame principal com grid layout
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configura expansão
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Painel esquerdo (lista de treinadores + botões)
        left_frame = ttk.Frame(main_frame, width=300)
        left_frame.grid(row=0, column=0, rowspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Configura o treeview de treinadores
        self.setup_trainer_list(left_frame)
        
        # Painel direito dividido em 3 seções
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, rowspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Seção superior direita (Trainer Data + Items)
        top_right_frame = ttk.Frame(right_frame)
        top_right_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N))
        
        # Trainer Data (canto superior esquerdo)
        trainer_data_frame = ttk.LabelFrame(top_right_frame, text="Trainer Data", padding="5", style="Blue.TLabelframe")
        trainer_data_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), padx=(0, 10))
        self.setup_trainer_data_tab(trainer_data_frame)
        
        # Items (canto superior direito)
        items_frame = ttk.LabelFrame(top_right_frame, text="Items", padding="5", style="Blue.TLabelframe")
        items_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N))
        self.setup_items_tab(items_frame)
        
        # Options (abaixo de Items)
        options_frame = ttk.LabelFrame(right_frame, text="Options", padding="5", style="Blue.TLabelframe")
        options_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), pady=(10, 10))
        self.setup_options_tab(options_frame)
        
        # Party (parte de baixo)
        party_frame = ttk.LabelFrame(right_frame, text="Party", padding="5", style="Blue.TLabelframe")
        party_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.setup_party_tab(party_frame)
        
        # Botões inferiores (agora na coluna esquerda)
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Save Trainer", command=self.save_trainer).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Save All Files", command=self.save_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Cancel", command=self.root.quit).pack(side=tk.RIGHT, padx=2)
        
        # Configura expansão dos frames
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(2, weight=1)
        top_right_frame.columnconfigure(0, weight=1)
        top_right_frame.columnconfigure(1, weight=1)
        party_frame.columnconfigure(0, weight=1)
        party_frame.rowconfigure(0, weight=1)

    def setup_trainer_list(self, parent):
        """Configura o painel esquerdo com a lista de treinadores"""
        # Frame de título
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill=tk.X, pady=5)
        ttk.Label(title_frame, text="Trainer List", style="Title.TLabel").pack()
        
        # Treeview para lista de treinadores
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.trainer_tree = ttk.Treeview(tree_frame, columns=("ID", "Trainer"), show="headings")
        self.trainer_tree.heading("ID", text="ID")
        self.trainer_tree.heading("Trainer", text="Trainer")
        self.trainer_tree.column("ID", width=50, anchor=tk.CENTER)
        self.trainer_tree.column("Trainer", width=200, anchor=tk.W)
        
        # Configura bind para seleção
        self.trainer_tree.bind('<<TreeviewSelect>>', self.on_trainer_selected)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.trainer_tree.yview)
        self.trainer_tree.configure(yscrollcommand=scrollbar.set)
        
        self.trainer_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botões de ação dos treinadores
        trainer_btn_frame = ttk.Frame(parent)
        trainer_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(trainer_btn_frame, text="Add Trainer", command=self.add_trainer).pack(side=tk.LEFT, padx=2)
        ttk.Button(trainer_btn_frame, text="Remove Trainer", command=self.remove_trainer).pack(side=tk.LEFT, padx=2)
        ttk.Button(trainer_btn_frame, text="Refresh", command=self.refresh_data).pack(side=tk.LEFT, padx=2)

    def setup_trainer_data_tab(self, parent):
        """Configura a seção de dados do treinador"""
        # Frame para sprite
        sprite_frame = ttk.LabelFrame(parent, text="Sprite", style="Section.TFrame")
        sprite_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        # Canvas para mostrar o sprite
        self.sprite_canvas = tk.Canvas(sprite_frame, width=64, height=64, bg="#F0F0F0")
        self.sprite_canvas.pack(pady=5)
        
        # Combobox para selecionar sprite
        self.trainer_pic_combo = ttk.Combobox(
            sprite_frame, 
            values=list(TRAINER_PICS.keys()),
            state="readonly"
        )
        self.trainer_pic_combo.pack(pady=5)
        self.trainer_pic_combo.bind("<<ComboboxSelected>>", self.update_sprite_preview)
        
        # Frame para ID do sprite
        sprite_id_frame = ttk.Frame(sprite_frame)
        sprite_id_frame.pack(pady=5)
        
        ttk.Label(sprite_id_frame, text="Sprite ID:").pack(side=tk.LEFT, padx=5)
        
        # Spinbox para o ID do sprite
        self.sprite_id_spinbox = tk.Spinbox(
            sprite_id_frame, 
            from_=0, 
            to=len(TRAINER_PICS)-1, 
            width=5,
            command=self.on_sprite_id_changed
        )
        self.sprite_id_spinbox.pack(side=tk.LEFT, padx=5)
        self.sprite_id_spinbox.bind("<KeyRelease>", self.on_sprite_id_changed)
        self.sprite_id_spinbox.bind("<ButtonRelease>", self.on_sprite_id_changed)
        
        # Frame para dados básicos
        data_frame = ttk.LabelFrame(parent, text="Trainer Info", style="Section.TFrame")
        data_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        # Trainer ID
        ttk.Label(data_frame, text="Trainer ID:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.trainer_id_entry = ttk.Entry(data_frame)
        self.trainer_id_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        # Define Name
        ttk.Label(data_frame, text="Define Name:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.define_name_entry = ttk.Entry(data_frame)
        self.define_name_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        
        # Display Name
        ttk.Label(data_frame, text="Display Name:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.display_name_entry = ttk.Entry(data_frame)
        self.display_name_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        
        # Class Name
        ttk.Label(data_frame, text="Class Name:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.class_name_combo = ttk.Combobox(data_frame, values=self.TRAINER_CLASSES)
        self.class_name_combo.grid(row=3, column=1, sticky="ew", padx=5, pady=2)
        self.class_name_combo.bind("<<ComboboxSelected>>", self.on_class_selected)
        
        # Gênero
        ttk.Label(data_frame, text="Gender:").grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self.gender_var = tk.StringVar(value="1")  # 1 = Male, 2 = Female
        ttk.Radiobutton(data_frame, text="Male", variable=self.gender_var, value="1").grid(row=4, column=1, sticky="w")
        ttk.Radiobutton(data_frame, text="Female", variable=self.gender_var, value="2").grid(row=5, column=1, sticky="w")
        
        parent.grid_columnconfigure(1, weight=1)
    
    def on_sprite_id_changed(self, event=None):
        """Quando o ID do sprite é alterado no spinbox"""
        try:
            sprite_id = int(self.sprite_id_spinbox.get())
            # Encontra o nome do sprite correspondente ao ID
            for sprite_name, sprite_id_value in TRAINER_PICS.items():
                if sprite_id_value == sprite_id:
                    self.trainer_pic_combo.set(sprite_name)
                    self.update_sprite_preview()
                    break
        except ValueError:
            pass
        
    def update_sprite_preview(self, event=None):
        """Atualiza a visualização do sprite e o ID quando selecionado"""
        selected_class = self.trainer_pic_combo.get()
        if not selected_class or not self.ROM_PATH or not self.ROM_PATH.exists():
            return
            
        # Atualiza o spinbox com o ID do sprite
        if selected_class in TRAINER_PICS:
            sprite_id = TRAINER_PICS[selected_class]
            self.sprite_id_spinbox.delete(0, tk.END)
            self.sprite_id_spinbox.insert(0, str(sprite_id))
        else:
            return
            
        # Verifica se temos um sprite válido para este ID
        if sprite_id < len(self.SPRITE_ADDRESSES_GBA) and sprite_id < len(self.PALETTE_ADDRESSES_GBA):
            sprite_addr = self.SPRITE_ADDRESSES_GBA[sprite_id]
            palette_addr = self.PALETTE_ADDRESSES_GBA[sprite_id]
            
            try:
                # Lê os dados do sprite
                sprite_data = self.read_sprite_data(sprite_addr)
                if not sprite_data:
                    raise ValueError("Failed to read sprite data")
                
                # Lê a paleta
                palette = self.read_palette(palette_addr)
                if not palette:
                    palette = [(0, 0, 0, 0)] * 16  # Paleta padrão se não encontrada
                
                # Converte para imagem
                img = self.decode_4bpp_tiled(sprite_data, palette)
                
                # Redimensiona para 64x64
                img = img.resize((64, 64), Image.Resampling.NEAREST)
                
                # Exibe no canvas
                self.tk_img = ImageTk.PhotoImage(img)
                self.sprite_canvas.delete("all")
                self.sprite_canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
                
            except Exception as e:
                print(f"Error loading sprite: {e}")
                self.sprite_canvas.delete("all")
                self.sprite_canvas.create_text(32, 32, text="Sprite\nError", fill="white")
        else:
            self.sprite_canvas.delete("all")
            self.sprite_canvas.create_text(32, 32, text="Sprite\nNot Found", fill="white")

    def setup_items_tab(self, parent):
        """Configura a seção de itens"""
        # Cria 4 comboboxes para itens
        self.item_combos = []
        for i in range(4):
            ttk.Label(parent, text=f"Item {i+1}:").grid(row=i, column=0, padx=5, pady=2, sticky="w")
            combo = ttk.Combobox(parent, values=self.items_list)
            combo.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            self.item_combos.append(combo)
        
        parent.grid_columnconfigure(1, weight=1)
    
    def setup_options_tab(self, parent):
        """Configura a seção de opções"""
        # Music
        ttk.Label(parent, text="Music:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.music_combo = ttk.Combobox(parent, values=[opt[1] for opt in MUSIC_OPTIONS])
        self.music_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        # AI Flags (usando os nomes definidos)
        ttk.Label(parent, text="AI Flags:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ai_frame = ttk.Frame(parent)
        ai_frame.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        
        self.ai_flag_vars = {}
        row_num = 0
        col_num = 0
        for flag_name in AI_FLAGS:
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(ai_frame, text=flag_name, variable=var)
            cb.grid(row=row_num, column=col_num, sticky="w", padx=5)
            self.ai_flag_vars[flag_name] = var
            
            col_num += 1
            if col_num > 2:
                col_num = 0
                row_num += 1
        
        # Double Battle
        self.double_battle_var = tk.BooleanVar()
        ttk.Checkbutton(parent, text="Double Battle", variable=self.double_battle_var).grid(
            row=2, column=0, columnspan=2, sticky="w", padx=5, pady=2)
        
        parent.grid_columnconfigure(1, weight=1)
        
    def setup_species_autocomplete(self):
        """Configura auto-complete para o combobox de espécies"""
        def autocomplete(event):
            # Obtém o texto atual
            typed = self.poke_species_combo.get().upper()
            
            if not typed:
                # Se estiver vazio, mostra todas as opções
                self.poke_species_combo['values'] = self.species_display_list
                return
            
            # Filtra as espécies que começam com o texto digitado
            matches = [species for species in self.species_display_list 
                      if species.upper().startswith(typed)]
            
            # Atualiza a lista de valores
            self.poke_species_combo['values'] = matches
            
            # Mantém o texto digitado e seleciona a parte não digitada
            if matches:
                self.poke_species_combo.set(typed)
                # Seleciona o texto que ainda não foi digitado
                self.poke_species_combo.icursor(tk.END)
                self.poke_species_combo.selection_range(len(typed), tk.END)
        
        # Vincula a função ao evento de digitação
        self.poke_species_combo.bind('<KeyRelease>', autocomplete)
    
    def setup_party_tab(self, parent):
        """Configura a seção de Pokémon com sprites abaixo da treeview"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Frame superior com Party Type e botões de ação da party
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(top_frame, text="Party Type:").pack(side=tk.LEFT, padx=5)
        
        # Combobox para selecionar o tipo de party
        self.party_type_combo = ttk.Combobox(top_frame, values=[pt[0] for pt in PARTY_TYPES], width=30)
        self.party_type_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.party_type_combo.bind("<<ComboboxSelected>>", self.on_party_type_selected)
        
        # Botões de ação da party (adicionar/remover Pokémon)
        party_btn_frame = ttk.Frame(top_frame)
        party_btn_frame.pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(party_btn_frame, text="+ Add Pokémon", command=self.add_pokemon).pack(side=tk.LEFT, padx=2)
        ttk.Button(party_btn_frame, text="- Remove Pokémon", command=self.remove_pokemon).pack(side=tk.LEFT, padx=2)
        
        # Frame principal para lista de Pokémon e sprites (coluna esquerda)
        left_column_frame = ttk.Frame(main_frame)
        left_column_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Treeview para Pokémon (apenas Species e Level)
        tree_frame = ttk.Frame(left_column_frame)
        tree_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.party_tree = ttk.Treeview(tree_frame, columns=("Species", "Level"), show="headings", height=6)
        self.party_tree.heading("Species", text="Species")
        self.party_tree.heading("Level", text="Level")
        self.party_tree.column("Species", width=150)
        self.party_tree.column("Level", width=40)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.party_tree.yview)
        self.party_tree.configure(yscrollcommand=scrollbar.set)
        
        self.party_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind para atualizar automaticamente quando selecionar um Pokémon
        self.party_tree.bind('<<TreeviewSelect>>', self.on_pokemon_selected)
        
        # Frame para os sprites dos Pokémon (abaixo da treeview) - SEM BORDA
        sprite_frame = ttk.Frame(left_column_frame)
        sprite_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Cria 6 frames para os sprites em uma única linha - SEM BORDA E SEM TEXTO
        sprite_row_frame = ttk.Frame(sprite_frame)
        sprite_row_frame.pack(fill=tk.X)
        
        self.pokemon_sprite_frames = []
        self.pokemon_sprite_images = []
        self.pokemon_sprite_labels = []
        
        for i in range(6):
            # Frame sem borda, sem relief e sem label
            frame = ttk.Frame(sprite_row_frame, width=64, height=64)
            frame.pack(side=tk.LEFT, padx=2)
            frame.pack_propagate(False)
            
            # Canvas para o sprite - fundo branco sem borda
            canvas = tk.Canvas(frame, width=64, height=64, bg="#F0F0F0", highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)
            
            # Canvas inicialmente vazio (sem texto "No Pokémon" e sem label)
            
            self.pokemon_sprite_images.append(None)
            self.pokemon_sprite_labels.append((canvas, None))  # Sem label
            self.pokemon_sprite_frames.append(frame)
        
        # Frame de edição do Pokémon (direita - mantendo o layout original)
        edit_frame = ttk.LabelFrame(main_frame, text="Pokémon Details", style="Section.TFrame")
        edit_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configura grid com 4 colunas para organizar os campos em pares
        for i in range(4):
            edit_frame.grid_columnconfigure(i, weight=1)
        
        # Linha 0: Species - Level
        ttk.Label(edit_frame, text="Species:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.poke_species_combo = ttk.Combobox(edit_frame, values=self.species_display_list, width=12)
        self.poke_species_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Label(edit_frame, text="Level:").grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.poke_level_entry = ttk.Entry(edit_frame, width=3)
        self.poke_level_entry.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        # Configura o auto-complete
        self.setup_species_autocomplete()
        
        # Linha 1: Held Item - Ability
        ttk.Label(edit_frame, text="Held Item:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.poke_item_combo = ttk.Combobox(edit_frame, values=self.items_list, width=12)
        self.poke_item_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        
        self.ability_label = ttk.Label(edit_frame, text="Ability:")
        self.ability_label.grid(row=1, column=2, sticky="w", padx=5, pady=2)
        self.ability_combo = ttk.Combobox(edit_frame, values=ABILITY_OPTIONS, width=16)
        self.ability_combo.grid(row=1, column=3, sticky="ew", padx=5, pady=2)
        self.ability_combo.set("Ability_1")
        
        # Linha 2: Move 1 - Move 2
        self.move_label1 = ttk.Label(edit_frame, text="Move 1:")
        self.move_label1.grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.move_combo1 = ttk.Combobox(edit_frame, values=self.moves_list, width=12)
        self.move_combo1.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        
        self.move_label2 = ttk.Label(edit_frame, text="Move 2:")
        self.move_label2.grid(row=2, column=2, sticky="w", padx=5, pady=2)
        self.move_combo2 = ttk.Combobox(edit_frame, values=self.moves_list, width=12)
        self.move_combo2.grid(row=2, column=3, sticky="ew", padx=5, pady=2)
        
        # Linha 3: Move 3 - Move 4
        self.move_label3 = ttk.Label(edit_frame, text="Move 3:")
        self.move_label3.grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.move_combo3 = ttk.Combobox(edit_frame, values=self.moves_list, width=12)
        self.move_combo3.grid(row=3, column=1, sticky="ew", padx=5, pady=2)
        
        self.move_label4 = ttk.Label(edit_frame, text="Move 4:")
        self.move_label4.grid(row=3, column=2, sticky="w", padx=5, pady=2)
        self.move_combo4 = ttk.Combobox(edit_frame, values=self.moves_list, width=12)
        self.move_combo4.grid(row=3, column=3, sticky="ew", padx=5, pady=2)
        
        # Atualiza as listas de move_combos
        self.move_combos = [self.move_combo1, self.move_combo2, self.move_combo3, self.move_combo4]
        self.move_labels = [self.move_label1, self.move_label2, self.move_label3, self.move_label4]
        
        # Linha 4: Nature - Tera Type
        self.nature_label = ttk.Label(edit_frame, text="Nature:")
        self.nature_label.grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self.nature_combo = ttk.Combobox(edit_frame, values=NATURES)
        self.nature_combo.grid(row=4, column=1, sticky="ew", padx=5, pady=2)
        self.nature_combo.set("HARDY")
        
        self.tera_label = ttk.Label(edit_frame, text="Tera Type:")
        self.tera_label.grid(row=4, column=2, sticky="w", padx=5, pady=2)
        self.tera_combo = ttk.Combobox(edit_frame, values=TERA_TYPES, width=12)
        self.tera_combo.grid(row=4, column=3, sticky="ew", padx=5, pady=2)
        self.tera_combo.set("TYPE_NORMAL")
        
        # Linha 5: IVs (ocupando toda a linha)
        self.iv_label = ttk.Label(edit_frame, text="IVs (0-31):")
        self.iv_label.grid(row=5, column=0, columnspan=4, sticky="w", padx=5, pady=2)
        
        iv_frame = ttk.Frame(edit_frame)
        iv_frame.grid(row=6, column=0, columnspan=4, sticky="ew", padx=5, pady=2)
        
        self.iv_entries = []
        for i in range(6):
            entry = ttk.Entry(iv_frame, width=3, validate="key")
            entry['validatecommand'] = (entry.register(self.validate_iv_entry), '%P')
            entry.insert(0, "0")
            entry.pack(side=tk.LEFT, padx=2)
            self.iv_entries.append(entry)
        
        # Linha 7: EVs (ocupando toda a linha)
        self.ev_label = ttk.Label(edit_frame, text="EVs (0-255):")
        self.ev_label.grid(row=5, column=2, columnspan=4, sticky="w", padx=5, pady=2)
        
        ev_frame = ttk.Frame(edit_frame)
        ev_frame.grid(row=6, column=2, columnspan=4, sticky="ew", padx=5, pady=2)
        
        self.ev_entries = []
        for i in range(6):
            entry = ttk.Entry(ev_frame, width=4, validate="key")
            entry['validatecommand'] = (entry.register(self.validate_ev_entry), '%P')
            entry.insert(0, "0")
            entry.pack(side=tk.LEFT, padx=2)
            self.ev_entries.append(entry)

        # Adiciona trace para verificar o total de EVs
        for entry in self.ev_entries:
            entry.bind('<FocusOut>', self.check_ev_total)
            entry.bind('<KeyRelease>', self.check_ev_total)
        
        # Botão de edição
        edit_btn_frame = ttk.Frame(edit_frame)
        edit_btn_frame.grid(row=9, column=0, columnspan=4, pady=10)
        
        self.edit_button = ttk.Button(edit_btn_frame, text="Edit", command=self.toggle_edit_mode)
        self.edit_button.pack(side=tk.LEFT, padx=5)
        
        self.party_tree.bind('<Double-1>', self.on_pokemon_selected)
        
        # Define o tipo de party padrão
        self.party_type_combo.current(0)
        self.update_party_fields()
        
        # Variável para controlar o Pokémon atual sendo editado
        self.current_pokemon_item = None
        self.editing_mode = False
        
    def toggle_edit_mode(self):
        """Alterna entre modo de edição e visualização"""
        if not self.editing_mode:
            self.enter_edit_mode()
        else:
            self.apply_pokemon_changes()
    
    def update_pokemon_sprites(self):
        """Atualiza a exibição dos sprites dos Pokémon baseado na party atual"""
        # Limpa todos os sprites atuais (apenas deixa o canvas vazio)
        for canvas, label in self.pokemon_sprite_labels:
            canvas.delete("all")
        
        # Atualiza os sprites para cada slot da party
        children = self.party_tree.get_children()
        for i, child in enumerate(children):
            if i >= 6:  # Máximo de 6 Pokémon
                break
                
            values = self.party_tree.item(child)['values']
            species_display_name = values[0].upper() if values else ""
            
            # Encontra o índice da espécie usando o mapeamento
            species_index = -1
            species_clean_name = species_display_name
            
            # Primeiro tenta encontrar pelo nome limpo (ex: POLIWAG)
            if species_clean_name in self.species_name_to_index:
                species_index = self.species_name_to_index[species_clean_name]
            else:
                # Se não encontrou, procura no mapeamento reverso
                for name, idx in self.species_name_to_index.items():
                    if name.upper() == species_clean_name:
                        species_index = idx
                        break
            
            if species_index > 0:
                # Verifica se o índice está dentro dos limites válidos das tabelas
                if (species_index < len(self.pokemon_sprite_addresses) and
                    species_index < len(self.pokemon_palette_addresses)):
                    
                    # Verifica se os endereços são válidos (não zero)
                    sprite_addr = self.pokemon_sprite_addresses[species_index]
                    palette_addr = self.pokemon_palette_addresses[species_index]
                    
                    if sprite_addr != 0 and palette_addr != 0:
                        self.load_pokemon_sprite(i, species_index)
                    else:
                        print(f"Skipping species {species_index} - addresses are zero")
                        # Não carrega nada (mantém o canvas vazio)
                else:
                    print(f"Species index {species_index} out of range")

    def load_pokemon_sprite(self, slot_index, species_index):
        """Carrega e exibe o sprite de um Pokémon específico usando o índice de species.h"""
        # Verificação adicional de segurança
        if (species_index <= 0 or 
            species_index >= len(self.pokemon_sprite_addresses) or 
            species_index >= len(self.pokemon_palette_addresses)):
            print(f"Species index {species_index} out of range")
            return
        
        sprite_addr = self.pokemon_sprite_addresses[species_index]
        palette_addr = self.pokemon_palette_addresses[species_index]
        
        # Verifica se os endereços são válidos (não zero)
        if sprite_addr == 0 or palette_addr == 0:
            print(f"Skipping species {species_index} - addresses are zero")
            return
        
        try:
            print(f"Loading species {species_index}: sprite=0x{sprite_addr:X}, palette=0x{palette_addr:X}")
            
            # Lê os dados do sprite
            sprite_data = self.read_sprite_data(sprite_addr)
            if not sprite_data:
                print(f"Failed to read sprite data at 0x{sprite_addr:X}")
                return
            
            # Lê a paleta
            palette = self.read_palette(palette_addr)
            if not palette:
                print(f"Failed to read palette at 0x{palette_addr:X}")
                palette = [(0, 0, 0, 0)] * 16
            
            # Converte para imagem
            img = self.decode_4bpp_tiled(sprite_data, palette)
            img = img.resize((64, 64), Image.Resampling.NEAREST)
            
            # Converte para PhotoImage e armazena
            tk_img = ImageTk.PhotoImage(img)
            self.pokemon_sprite_images[slot_index] = tk_img  # Mantém referência
            
            # Atualiza o canvas
            canvas, label = self.pokemon_sprite_labels[slot_index]
            canvas.delete("all")
            canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
            
        except Exception as e:
            print(f"Error loading Pokémon sprite for species {species_index}: {e}")
            canvas, label = self.pokemon_sprite_labels[slot_index]
            canvas.delete("all")
            
    def load_species_mapping(self):
        """Carrega o mapeamento de nomes de espécies para seus valores numéricos"""
        self.species_name_to_index = {}
        self.species_index_to_name = {}
        
        try:
            with open(self.SPECIES_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#define SPECIES_'):
                        parts = line.split()
                        if len(parts) >= 3:
                            species_name = parts[1]  # Ex: SPECIES_POLIWAG
                            value_str = parts[2]
                            
                            # Remove prefixo SPECIES_
                            clean_name = species_name.replace('SPECIES_', '')
                            
                            # Converte o valor (pode ser hex 0x3C ou decimal 60)
                            if value_str.startswith('0x'):
                                species_index = int(value_str[2:], 16)
                            else:
                                species_index = int(value_str)
                            
                            self.species_name_to_index[clean_name] = species_index
                            self.species_index_to_name[species_index] = clean_name
                            
            print(f"Loaded {len(self.species_name_to_index)} species mappings")
            
        except Exception as e:
            print(f"Error loading species mapping: {e}")
            # Fallback básico
            self.species_name_to_index = {'BULBASAUR': 1, 'CHARMANDER': 4, 'SQUIRTLE': 7}
            self.species_index_to_name = {1: 'BULBASAUR', 4: 'CHARMANDER', 7: 'SQUIRTLE'}    
        
    def on_pokemon_selected(self, event=None):
        """Quando um Pokémon é selecionado na lista"""
        selected = self.party_tree.selection()
        if selected:
            self.current_pokemon_item = selected[0]
            self.load_pokemon_for_editing(selected[0])
            self.exit_edit_mode()  # Garante que está em modo visualização
            self.update_pokemon_sprites()

    def apply_pokemon_changes(self):
        """Aplica as mudanças do Pokémon atual (edição ou adição)"""
        # Validação básica
        species = self.poke_species_combo.get()
        level = self.poke_level_entry.get()
        
        if not species or not level.isdigit():
            messagebox.showerror("Error", "Species and valid Level are required")
            return
        
        # Coleta os dados do formulário
        party_type = self.party_type_var.get()
        moves = [combo.get() for combo in self.move_combos] if party_type in [3, 4] else []
        
        # Prepara os valores para a treeview
        values = [species.upper(), level]
        
        # Adiciona item se aplicável
        if party_type in [2, 4]:
            values.append(self.poke_item_combo.get().upper() if self.poke_item_combo.get() else 'NONE')
        
        # Adiciona movimentos se aplicável
        if party_type in [3, 4]:
            for move in moves:
                values.append(move.upper() if move else 'NONE')
        
        # Atualiza ou adiciona o Pokémon
        if self.current_pokemon_item:  # Modo edição
            self.party_tree.item(self.current_pokemon_item, values=values)
        else:  # Modo adição
            self.current_pokemon_item = self.party_tree.insert('', tk.END, values=values)
        
        # Atualiza a estrutura de dados da party
        self.update_party_data_structure()
        
        # Sai do modo de edição
        self.exit_edit_mode()
        
        # Atualiza os sprites
        self.update_pokemon_sprites()
        
        # Marca como modificado
        self.modified = True
        
        # Feedback
        if self.current_pokemon_item:
            messagebox.showinfo("Success", "Pokémon updated successfully!")
        else:
            messagebox.showinfo("Success", "Pokémon added successfully!")

    def update_party_data_structure(self):
        """Atualiza a estrutura de dados interna da party com os valores atuais"""
        if not self.current_pokemon_item or not self.current_editing_id:
            return
        
        # Encontra o treinador atual
        trainer_name = None
        for name, data in self.trainers.items():
            if data['id'] == self.current_editing_id:
                trainer_name = name
                break
        
        if not trainer_name:
            return
        
        # Encontra la party correspondente
        party_name = self.trainers[trainer_name].get('party_name')
        if not party_name:
            return
        
        # Encontra a party nos dados
        party_data = self.parties.get(party_name) or self.new_parties.get(party_name)
        if not party_data:
            return
        
        # Encontra o índice do Pokémon sendo editado
        pokemon_index = self.party_tree.index(self.current_pokemon_item)
        if pokemon_index >= len(party_data.get('pokemons', [])):
            return
        
        # Atualiza os dados do Pokémon com os valores atuais dos campos
        pokemon = party_data['pokemons'][pokemon_index]
        
        # Dados básicos
        pokemon['species'] = f"SPECIES_{self.poke_species_combo.get().upper()}"
        pokemon['level'] = self.poke_level_entry.get()
        
        # Item
        party_type = self.party_type_var.get()
        if party_type in [2, 4]:
            item = self.poke_item_combo.get()
            pokemon['item'] = f"ITEM_{item.upper()}" if item else "ITEM_NONE"
        
        # Movimentos
        if party_type in [3, 4]:
            moves = []
            for combo in self.move_combos:
                move = combo.get()
                moves.append(f"MOVE_{move.upper()}" if move else "MOVE_NONE")
            pokemon['moves'] = moves
        
        # Dados avançados
        if party_type == 4:
            # Ability
            pokemon['ability'] = self.ability_combo.get()
            
            # Nature
            pokemon['nature'] = f"NATURE_{self.nature_combo.get()}"
            
            # IVs
            ivs = []
            for entry in self.iv_entries:
                value = entry.get().strip()
                ivs.append(value if value.isdigit() else "0")
            pokemon['ivs'] = ivs
            
            # EVs
            evs = []
            for entry in self.ev_entries:
                value = entry.get().strip()
                evs.append(value if value.isdigit() else "0")
            pokemon['evs'] = evs
            
            # Tera Type
            pokemon['tera_type'] = self.tera_combo.get()
        
    def toggle_edit_pokemon(self):
        """Alterna entre modo de edição e visualização"""
        if not self.editing_pokemon_mode:
            self.enter_edit_mode()
        else:
            self.save_pokemon_edits()

    def enter_edit_mode(self):
        """Entra no modo de edição"""
        if not self.party_tree.selection():
            messagebox.showwarning("Warning", "Please select a Pokémon to edit")
            return
            
        self.editing_mode = True
        self.edit_button.config(text="Apply Changes")
        self.enable_pokemon_fields(True)
        
    def exit_edit_mode(self):
        """Sai do modo de edição"""
        self.editing_mode = False
        self.edit_button.config(text="Edit")
        self.enable_pokemon_fields(False)
        
    def enable_pokemon_fields(self, enable):
        """Habilita ou desabilita os campos de edição de Pokémon"""
        state = "normal" if enable else "disabled"
        self.poke_species_combo.config(state=state)
        self.poke_level_entry.config(state=state)
        self.poke_item_combo.config(state=state)
        for combo in self.move_combos:
            combo.config(state=state)
        for entry in self.iv_entries:
            entry.config(state=state)
        for entry in self.ev_entries:
            entry.config(state=state)
        self.nature_combo.config(state=state)
        self.ability_combo.config(state=state)
        self.tera_combo.config(state=state)
            
    def load_pokemon_for_editing(self, item_id):
        """Carrega os dados do Pokémon selecionado para os campos de edição"""
        item = self.party_tree.item(item_id)
        values = item['values']
        
        # Carrega dados básicos
        self.poke_species_combo.set(values[0])
        self.poke_level_entry.delete(0, tk.END)
        self.poke_level_entry.insert(0, values[1])
        
        # Carrega item se existir
        party_type = self.party_type_var.get()
        if party_type in [2, 4] and len(values) > 2:
            self.poke_item_combo.set(values[2])
        
        # Carrega movimentos se existirem
        if party_type in [3, 4]:
            move_start_idx = 3 if party_type in [2, 4] else 2
            for i in range(4):
                if len(values) > move_start_idx + i:
                    self.move_combos[i].set(values[move_start_idx + i])
                else:
                    self.move_combos[i].set('')

    def save_pokemon_edits(self):
        """Salva as alterações do Pokémon em edição"""
        if not self.current_editing_pokemon:
            return
        
        # Validações básicas
        species = self.poke_species_combo.get()
        level = self.poke_level_entry.get()
        
        if not species or not level.isdigit():
            messagebox.showerror("Error", "Species and valid Level are required")
            return
        
        # Prepara os novos valores
        new_values = [species.upper(), level]
        
        # Adiciona item se necessário
        party_type = self.party_type_var.get()
        if party_type in [2, 4]:
            item = self.poke_item_combo.get()
            new_values.append(item.upper() if item else "NONE")
        
        # Adiciona movimentos se necessário
        if party_type in [3, 4]:
            for combo in self.move_combos:
                move = combo.get()
                new_values.append(move.upper() if move else "NONE")
        
        # Atualiza o item na treeview
        self.party_tree.item(self.current_editing_pokemon, values=new_values)
        
        # Atualiza também na estrutura de dados da party se existir
        self.update_party_data_structure(new_values)
        
        # Sai do modo de edição
        self.exit_edit_mode()
        
        # Auto-refresh e feedback
        messagebox.showinfo("Success", "Pokémon updated successfully!")
        self.modified = True
        
    def validate_iv_entry(self, new_value):
        """Valida a entrada de IV (0-31, máximo 2 caracteres)"""
        if not new_value:  # Permite campo vazio temporariamente
            return True
        if not new_value.isdigit():
            return False
        if len(new_value) > 2:
            return False
        if int(new_value) > 31:
            return False
        return True

    def validate_ev_entry(self, new_value):
        """Valida la entrada de EV (0-252, máximo 3 caracteres)"""
        if not new_value:  # Permite campo vazio temporariamente
            return True
        if not new_value.isdigit():
            return False
        if len(new_value) > 3:
            return False
        if int(new_value) > 252:
            return False
        return True

    def check_ev_total(self, event=None):
        """Verifica se a soma total de EVs não ultrapassa 510"""
        total = 0
        for entry in self.ev_entries:
            value = entry.get()
            if value.isdigit():
                total += int(value)
            else:
                # Se algum campo não for número válido, considera como erro
                return False
        
        if total > 510:
            # Destaca os campos de EV
            for entry in self.ev_entries:
                entry.config(foreground='red')
            return False
        
        # Remove o destaque se estiver ok
        for entry in self.ev_entries:
            entry.config(foreground='black')
        return True
    
    def on_party_type_selected(self, event):
        """Atualiza o tipo de party quando selecionado no combobox"""
        selected = self.party_type_combo.current()
        if selected >= 0:
            self.party_type_var.set(PARTY_TYPES[selected][1])
    
    def update_party_fields(self, *args):
        """Atualiza os campos visíveis com base no tipo de party selecionado"""
        party_type = self.party_type_var.get()
        
        # Atualiza a visibilidade dos campos
        show_moves = party_type in [3, 4]
        show_item = party_type in [2, 4]
        show_advanced = party_type == 4
        
        # Atualiza os campos de movimento
        for label in self.move_labels:
            if show_moves:
                label.grid()
            else:
                label.grid_remove()
                
        for combo in self.move_combos:
            if show_moves:
                combo.grid()
            else:
                combo.grid_remove()
        
        # Atualiza o campo de item
        if show_item:
            self.poke_item_combo.grid()
        else:
            self.poke_item_combo.grid_remove()
            self.poke_item_combo.set('NONE')
        
        # Atualiza os campos avançados
        if show_advanced:
            self.ability_label.grid()
            self.ability_combo.grid()
            self.nature_label.grid()
            self.nature_combo.grid()
            self.iv_label.grid()
            for entry in self.iv_entries:
                entry.master.grid()
            self.ev_label.grid()
            for entry in self.ev_entries:
                entry.master.grid()
            self.tera_label.grid()
            self.tera_combo.grid()
        else:
            self.ability_label.grid_remove()
            self.ability_combo.grid_remove()
            self.nature_label.grid_remove()
            self.nature_combo.grid_remove()
            self.iv_label.grid_remove()
            for entry in self.iv_entries:
                entry.master.grid_remove()
            self.ev_label.grid_remove()
            for entry in self.ev_entries:
                entry.master.grid_remove()
            self.tera_label.grid_remove()
            self.tera_combo.grid_remove()
    
    def on_class_selected(self, event):
        """Quando uma classe é selecionada, atualiza o sprite e o ID"""
        selected_class = self.class_name_combo.get()
        
        # Atualiza o sprite
        if selected_class in TRAINER_PICS:
            self.trainer_pic_combo.set(selected_class)
            self.update_sprite_preview()
    
    def get_class_id(self, class_name):
        """Obtém o ID numérico de uma classe de treinador"""
        # Primeiro tenta encontrar no arquivo de classes
        try:
            with open(self.TRAINER_CLASSES_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
                pattern = rf"{class_name}\s*=\s*(\d+)"
                match = re.search(pattern, content)
                if match:
                    return int(match.group(1))
        except:
            pass
        
        # Se não encontrou, usa o mapeamento manual
        if 'CLASS_NAME_TO_ID' in globals() and class_name in CLASS_NAME_TO_ID:
            return CLASS_NAME_TO_ID[class_name]
        
        return None
    
    def populate_trainer_tree(self):
        """Popula a lista de treinadores"""
        for item in self.trainer_tree.get_children():
            self.trainer_tree.delete(item)
        
        for name, data in self.trainers.items():
            display_name = ""
            
            for line in data['data']:
                if '.trainerName' in line:
                    display_name = line.split('=')[1].strip(' ,')
                    display_name = self.easy_text_to_normal(display_name)
                    break
            
            self.trainer_tree.insert('', tk.END, values=(data['id'], display_name))
    
    def on_trainer_selected(self, event):
        """Quando um treinador é selecionado na lista"""
        selected = self.trainer_tree.selection()
        if not selected:
            return
        
        item = self.trainer_tree.item(selected[0])
        trainer_id = item["values"][0]
        
        for name, data in self.trainers.items():
            if data['id'] == trainer_id:
                self.current_editing_id = trainer_id
                self.load_trainer_data(name, data)
                break
    
    def load_trainer_data(self, name, data):
        """Carrega os dados do treinador nos campos, incluindo a party"""
        self.clear_editor_fields()
        
        # Preenche campos básicos
        self.define_name_entry.insert(0, name)
        
        # Busca o ID no opponents.h usando o dicionário opponent_name_to_id
        trainer_id = str(self.opponent_name_to_id.get(name, data['id']))
        self.trainer_id_entry.insert(0, trainer_id)
        
        # Restante do código permanece o mesmo...
        # Extrai informações adicionais
        party_name = None
        party_type = None
        for line in data['data']:
            if '.trainerClass' in line:
                trainer_class = line.split('=')[1].strip(' ,').replace('CLASS_', '')
                self.class_name_combo.set(trainer_class)
            elif '.trainerName' in line:
                display_name = line.split('=')[1].strip(' ,')
                normal_name = self.easy_text_to_normal(display_name)
                self.display_name_entry.insert(0, normal_name)
            elif '.encounterMusic' in line:
                music = line.split('=')[1].strip(' ,')
                self.music_combo.set(music)
            elif '.doubleBattle' in line:
                self.double_battle_var.set("TRUE" in line)
            elif '.aiFlags' in line:
                flags = line.split('=')[1].strip(' ,')
                self.load_ai_flags(flags)
            elif '.items' in line:
                items = re.findall(r'ITEM_\w+', line)
                for i, item in enumerate(items[:4]):
                    if i < len(self.item_combos):
                        self.item_combos[i].set(item.replace('ITEM_', ''))
            elif '.party = {' in line:
                party_line = line.split('=', 1)[1].strip()
                if '.ItemCustomMoves = ' in party_line:
                    party_name = party_line.split('.ItemCustomMoves = ')[1].strip(' {},')
                    party_type = 4
                elif '.NoItemCustomMoves = ' in party_line:
                    party_name = party_line.split('.NoItemCustomMoves = ')[1].strip(' {},')
                    party_type = 3
                elif '.ItemDefaultMoves = ' in party_line:
                    party_name = party_line.split('.ItemDefaultMoves = ')[1].strip(' {},')
                    party_type = 2
                elif '.NoItemDefaultMoves = ' in party_line:
                    party_name = party_line.split('.NoItemDefaultMoves = ')[1].strip(' {},')
                    party_type = 1
            elif '.trainerPic' in line:
                pic_name = line.split('=')[1].strip(' ,').replace('TRAINER_PIC_', '')
                self.trainer_pic_combo.set(pic_name)
                
                # Atualiza o ID do sprite também
                if pic_name in TRAINER_PICS:
                    sprite_id = TRAINER_PICS[pic_name]
                    self.sprite_id_spinbox.delete(0, tk.END)
                    self.sprite_id_spinbox.insert(0, str(sprite_id))
                
                self.update_sprite_preview()
        
        # Carrega a party se encontrou o nome
        if party_name:
            self.load_party_data(party_name, party_type)
                
    def load_party_data(self, party_name, party_type=None):
        """Carrega os dados da party na interface"""
        # Limpa a treeview atual
        for item in self.party_tree.get_children():
            self.party_tree.delete(item)
        
        # Encontra a party nos dados carregados
        party_data = None
        if party_name in self.parties:
            party_data = self.parties[party_name]
        elif party_name in self.new_parties:
            party_data = self.new_parties[party_name]
        
        if not party_data:
            print(f"Party '{party_name}' not found in loaded data")
            return
        
        # Se party_type não foi especificado, tenta determinar do party_data
        if party_type is None:
            party_type = party_data['type']
        
        # Atualiza o combobox de party type
        for i, (desc, pt) in enumerate(PARTY_TYPES):
            if pt == party_type:
                self.party_type_combo.current(i)
                self.party_type_var.set(party_type)
                break
        
        # Adiciona cada Pokémon ao treeview
        for pokemon in party_data.get('pokemons', []):
            species = pokemon.get('species', 'SPECIES_NONE').replace('SPECIES_', '')
            level = pokemon.get('level', '0')
            item = pokemon.get('item', 'ITEM_NONE').replace('ITEM_', '')
            
            # Prepara os movimentos para exibição
            moves = []
            if 'moves' in pokemon:
                moves = [m.replace('MOVE_', '') for m in pokemon['moves']]
            
            # Adiciona ao treeview com os movimentos
            self.party_tree.insert('', tk.END, values=(
                species,
                level,
                item,
                *moves[:4]  # Garante no máximo 4 movimentos
            ))
        
        # Atualiza os campos visíveis
        self.update_party_fields()
        
        # Atualiza os sprites após carregar a party
        self.update_pokemon_sprites()
        
        # Se houver Pokémon selecionado, carrega seus detalhes
        if self.party_tree.get_children():
            self.party_tree.selection_set(self.party_tree.get_children()[0])
            # Chama o método correto para carregar os detalhes
            self.load_pokemon_for_editing_preview(self.party_tree.get_children()[0])
    
    def load_ai_flags(self, flags_str):
        """Carrega as flags AI nos checkboxes usando os nomes das flags"""
        try:
            # Extrai os nomes das flags da string
            flag_names = [f.strip() for f in flags_str.split('|')]
            
            # Verifica cada flag pelo nome
            for flag_name in self.ai_flag_vars:
                self.ai_flag_vars[flag_name].set(flag_name in flag_names)
        except:
            # Fallback para o método antigo se a string não estiver no formato esperado
            try:
                if 'x' in flags_str:
                    flags_value = int(flags_str.split('x')[-1], 16)
                else:
                    flags_value = int(flags_str)
                
                for flag_name in self.ai_flag_vars:
                    flag_value = AI_FLAGS.get(flag_name, 0)
                    if flag_value > 0:
                        self.ai_flag_vars[flag_name].set(bool(flags_value & flag_value))
            except ValueError:
                pass
    
    def clear_editor_fields(self):
        """Limpa todos os campos do editor"""
        self.define_name_entry.delete(0, tk.END)
        self.trainer_id_entry.delete(0, tk.END)
        self.display_name_entry.delete(0, tk.END)
        self.class_name_combo.set('')
        self.gender_var.set("1")
        self.music_combo.set('')
        self.double_battle_var.set(False)
        
        for var in self.ai_flag_vars.values():
            var.set(False)
        
        for combo in self.item_combos:
            combo.set('')
        
        for item in self.party_tree.get_children():
            self.party_tree.delete(item)
        
        self.poke_species_combo.set('')
        self.poke_level_entry.delete(0, tk.END)
        self.poke_item_combo.set('')
        
        for entry in self.iv_entries:
            entry.delete(0, tk.END)
            entry.insert(0, "0")
        
        for entry in self.ev_entries:
            entry.delete(0, tk.END)
            entry.insert(0, "0")
            
        self.nature_combo.set("HARDY")
        self.ability_combo.set("Ability_1")
        self.tera_combo.set("TYPE_NORMAL")
        
        for combo in self.move_combos:
            combo.set('')
    
    def refresh_data(self):
        """Recarrega todos os dados dos arquivos"""
        self.load_initial_data()
        self.populate_trainer_tree()
        messagebox.showinfo("Info", "Data refreshed from files")
    
    def add_trainer(self):
        """Prepara a interface para adicionar um novo treinador"""
        self.current_editing_id = None
        self.clear_editor_fields()
        
        # Define um ID padrão baseado no maior ID existente + 1
        max_id = max([int(data['id']) for data in self.trainers.values()] + [0])
        self.trainer_id_entry.delete(0, tk.END)
        self.trainer_id_entry.insert(0, str(max_id + 1))
    
    def remove_trainer(self):
        """Remove o treinador selecionado"""
        selected = self.trainer_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a trainer first")
            return
        
        item = self.trainer_tree.item(selected[0])
        trainer_id = item["values"][0]
        
        if messagebox.askyesno("Confirm", f"Delete trainer {trainer_id}?"):
            for name, data in list(self.trainers.items()):
                if data['id'] == trainer_id:
                    del self.trainers[name]
                    break
            
            self.populate_trainer_tree()
            messagebox.showinfo("Success", "Trainer deleted successfully")
            self.modified = True
    
    def add_pokemon(self):
        """Adiciona um novo Pokémon ao time"""
        # Limpa os campos de edição
        self.clear_pokemon_fields()
        
        # Habilita a edição
        self.enable_pokemon_fields(True)
        
        # Configura para modo de adição
        self.editing_mode = True
        self.edit_button.config(text="Add Pokémon")
        self.current_pokemon_item = None
        
        # Foca no campo de espécie
        self.poke_species_combo.focus()
        
    def clear_pokemon_fields(self):
        """Limpa todos os campos de edição de Pokémon"""
        self.poke_species_combo.set('')
        self.poke_level_entry.delete(0, tk.END)
        self.poke_level_entry.insert(0, '')  # Level padrão
        self.poke_item_combo.set('')
        
        for combo in self.move_combos:
            combo.set('')
            
        for entry in self.iv_entries:
            entry.delete(0, tk.END)
            entry.insert(0, '0')
            
        for entry in self.ev_entries:
            entry.delete(0, tk.END)
            entry.insert(0, '0')
            
        self.nature_combo.set('')
        self.ability_combo.set('')
        self.tera_combo.set('')
    
    def edit_pokemon(self, event=None):
        """Handler para quando um Pokémon é selecionado (double-click ou seleção)"""
        if not self.editing_pokemon_mode:
            selected = self.party_tree.selection()
            if selected:
                self.load_pokemon_for_editing_preview(selected[0])
                
    def load_pokemon_for_editing_preview(self, item_id):
        """Carrega os dados do Pokémon selecionado para visualização/edição"""
        item = self.party_tree.item(item_id)
        values = item['values']
        
        # Preenche os campos básicos
        self.poke_species_combo.set(values[0])
        self.poke_level_entry.delete(0, tk.END)
        self.poke_level_entry.insert(0, values[1])
        
        # Para carregar os dados completos, precisamos acessar a estrutura de dados da party
        if self.current_editing_id:
            # Encontra o treinador atual
            trainer_name = None
            for name, data in self.trainers.items():
                if data['id'] == self.current_editing_id:
                    trainer_name = name
                    break
            
            if trainer_name:
                # Encontra la party correspondente
                party_name = self.trainers[trainer_name].get('party_name')
                if party_name:
                    # Encontra a party nos dados
                    party_data = self.parties.get(party_name) or self.new_parties.get(party_name)
                    if party_data:
                        # Encontra o índice do Pokémon sendo editado
                        pokemon_index = self.party_tree.index(item_id)
                        if pokemon_index < len(party_data.get('pokemons', [])):
                            pokemon = party_data['pokemons'][pokemon_index]
                            
                            # Carrega dados avançados se existirem
                            if 'item' in pokemon:
                                item_name = pokemon['item'].replace('ITEM_', '')
                                self.poke_item_combo.set(item_name)
                            
                            if 'ability' in pokemon:
                                self.ability_combo.set(pokemon['ability'])
                            
                            if 'nature' in pokemon:
                                nature = pokemon['nature'].replace('NATURE_', '')
                                self.nature_combo.set(nature)
                            
                            if 'ivs' in pokemon:
                                # ivs pode ser uma string ou lista
                                if isinstance(pokemon['ivs'], str):
                                    # Se for string, divide por vírgulas
                                    iv_values = [v.strip() for v in pokemon['ivs'].split(',')]
                                else:
                                    iv_values = pokemon['ivs']
                                
                                for i, iv_value in enumerate(iv_values[:6]):
                                    if i < len(self.iv_entries):
                                        self.iv_entries[i].delete(0, tk.END)
                                        self.iv_entries[i].insert(0, iv_value)
                            
                            if 'evs' in pokemon:
                                # evs pode ser uma string ou lista
                                if isinstance(pokemon['evs'], str):
                                    # Se for string, divide por vírgulas
                                    ev_values = [v.strip() for v in pokemon['evs'].split(',')]
                                else:
                                    ev_values = pokemon['evs']
                                
                                for i, ev_value in enumerate(ev_values[:6]):
                                    if i < len(self.ev_entries):
                                        self.ev_entries[i].delete(0, tk.END)
                                        self.ev_entries[i].insert(0, ev_value)
                            
                            if 'tera_type' in pokemon:
                                self.tera_combo.set(pokemon['tera_type'])
                            
                            # Carrega movimentos se existirem
                            if 'moves' in pokemon:
                                for i, move in enumerate(pokemon['moves'][:4]):
                                    if i < len(self.move_combos):
                                        move_name = move.replace('MOVE_', '')
                                        self.move_combos[i].set(move_name)
    
    def remove_pokemon(self):
        """Remove o Pokémon selecionado"""
        selected = self.party_tree.selection()
        if selected:
            self.party_tree.delete(selected[0])
            self.update_pokemon_sprites()
            self.modified = True
    
    def save_trainer(self):
        """Salva o treinador atual"""
        if not self.validate_inputs():
            return
        
        # Verifica os IVs
        for entry in self.iv_entries:
            value = entry.get()
            if not value.isdigit() or int(value) > 31:
                messagebox.showerror("Error", f"Invalid IV value: {value}. Must be between 0-31")
                return
        
        if not self.check_ev_total():
            messagebox.showerror("Error", "Cannot save: Total EVs exceed 510")
            return
        
        define_name = self.define_name_entry.get()
        try:
            trainer_id = int(self.trainer_id_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Trainer ID must be a numeric value")
            return
        
        # Verifica se é uma edição de treinador existente
        is_existing = self.current_editing_id is not None
        
        # Mantém a party existente se estiver editando
        party_name = f"sParty_{define_name.title().replace('_', '')}"
        if is_existing and define_name in self.trainers:
            old_party = self.trainers[define_name].get('party_name')
            if old_party and old_party in self.parties:
                party_name = old_party
        
        # Determina o tipo de party
        party_type = self.party_type_var.get()
        
        # Prepara os dados do party
        party_data = []
        for child in self.party_tree.get_children():
            values = self.party_tree.item(child)['values']
            pokemon = {
                'species': f"SPECIES_{values[0].upper()}",
                'level': values[1],
                'party_type': party_type
            }
            
            # Adiciona item se necessário
            if party_type in [2, 4]:
                pokemon['item'] = f"ITEM_{values[2].upper()}" if len(values) > 2 and values[2] else "ITEM_NONE"
            
            # Adiciona moves se necessário (valores 3-6 são os movimentos)
            if party_type in [3, 4]:
                moves = []
                for i in range(3, min(7, len(values))):  # Pega os 4 movimentos (índices 3-6)
                    move = values[i] if i < len(values) and values[i] != 'NONE' else 'NONE'
                    moves.append(f"MOVE_{move}")
                
                # Garante 4 movimentos
                while len(moves) < 4:
                    moves.append("MOVE_NONE")
                
                pokemon['moves'] = moves
            
            # Adiciona dados avançados se necessário
            if party_type == 4:
                # Coletar IVs: list of 6 valores
                ivs = []
                for entry in self.iv_entries:
                    value = entry.get().strip()
                    if value.isdigit():
                        ivs.append(str(min(31, max(0, int(value)))))
                    else:
                        ivs.append("0")
                
                # Coletar EVs: list of 6 valores
                evs = []
                for entry in self.ev_entries:
                    value = entry.get().strip()
                    if value.isdigit():
                        evs.append(str(min(255, max(0, int(value)))))
                    else:
                        evs.append("0")
                
                pokemon.update({
                    'ability': self.ability_combo.get(),
                    'nature': self.nature_combo.get(),
                    'ivs': ", ".join(ivs),
                    'evs': ", ".join(evs),
                    'tera_type': self.tera_combo.get()
                })
            
            party_data.append(pokemon)
        
        # Prepara as flags do party
        party_flags = []
        if party_type in [3, 4]:
            party_flags.append("PARTY_FLAG_CUSTOM_MOVES")
        if party_type in [2, 4]:
            party_flags.append("PARTY_FLAG_HAS_ITEM")
        
        trainer_data = {
            'id': trainer_id,
            'data': [
                f".partyFlags = {' | '.join(party_flags) if party_flags else '0'},",
                f".trainerClass = CLASS_{self.class_name_combo.get().upper()},",
                f".encounterMusic = {self.music_combo.get()},",
                f".trainerPic = TRAINER_PIC_{self.trainer_pic_combo.get()},",
                f".trainerName = {self.convert_to_easy_text(self.display_name_entry.get())},",
                f".items = {{{', '.join([f'ITEM_{combo.get().upper()}' if combo.get() else 'ITEM_NONE' for combo in self.item_combos])}}},",
                f".doubleBattle = {'TRUE' if self.double_battle_var.get() else 'FALSE'},",
                f".aiFlags = {self.get_ai_flags_value()},  // Flags: {hex(self.calculate_ai_flags_numeric())}",
                f".partySize = NELEMS({party_name}),",
                f".party = {{.{PARTY_TYPE_UNION_MAP[party_type]} = {party_name}}}"
            ],
            'party_name': party_name,
            'party_data': party_data,
            'party_struct': PARTY_TYPE_STRUCT_MAP[party_type]
        }
        
        # Adiciona/atualiza nos dados
        self.trainers[define_name] = trainer_data
        self.new_parties[party_name] = {
            'data': party_data,
            'struct': PARTY_TYPE_STRUCT_MAP[party_type]
        }
        self.opponent_name_to_id[define_name] = trainer_id
        self.opponent_id_to_name[trainer_id] = define_name
        
        self.modified = True
        self.populate_trainer_tree()
        messagebox.showinfo("Success", "Trainer saved to memory. Don't forget to save files!")
    
    def calculate_ai_flags_numeric(self):
        """Calcula o valor numérico das flags para referência"""
        flags_value = 0
        for flag_name, var in self.ai_flag_vars.items():
            if var.get():
                flags_value |= AI_FLAGS.get(flag_name, 0)
        return flags_value
    
    def get_ai_flags_value(self):
        """Retorna as flags AI como uma string com os nomes das flags"""
        active_flags = []
        
        for flag_name, var in self.ai_flag_vars.items():
            if var.get():
                active_flags.append(flag_name)
        
        if not active_flags:
            return "0"
        
        return " | ".join(active_flags)
    
    def validate_inputs(self):
        """Valida todos os campos de entrada antes de salvar"""
        errors = []
        
        # Validação do nome e ID
        if not self.define_name_entry.get():
            errors.append("Define Name is required")
        
        try:
            int(self.trainer_id_entry.get())
        except ValueError:
            errors.append("Trainer ID must be a number")
        
        # Validação da classe
        if not self.class_name_combo.get():
            errors.append("Trainer Class is required")
        
        # Validação da música
        if not self.music_combo.get():
            errors.append("Encounter Music is required")
        
        # Validação de AI Flags (pelo menos uma flag deve estar marcada)
        if not any(var.get() for var in self.ai_flag_vars.values()):
            errors.append("At least one AI Flag must be selected")
        
        # Validação do party
        if not self.party_tree.get_children():
            errors.append("Trainer must have at least one Pokémon")
        
        # Validação dos IVs
        for i, entry in enumerate(self.iv_entries):
            value = entry.get()
            if not value.isdigit() or int(value) > 31:
                errors.append(f"IV {i+1} must be between 0-31")
        
        # Validação dos EVs
        if not self.check_ev_total():
            errors.append("Total EVs cannot exceed 510")

        # Validação do sprite
        if not self.trainer_pic_combo.get():
            errors.append("Trainer Sprite is required")
        
        # Mostra todos os erros de uma vez
        if errors:
            messagebox.showerror("Validation Error", 
                            "Please fix the following errors:\n\n- " + "\n- ".join(errors))
            return False
        
        return True

if __name__ == "__main__":
    root = tk.Tk()
    app = TrainerEditorUI(root)
    root.mainloop()