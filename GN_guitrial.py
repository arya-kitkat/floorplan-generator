import tkinter as tk
import json
import os
import time
from tkinter import messagebox

# Import your algorithm
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__))) #converts this file's path into absolute to extract just directory where it can look for GN_assignment next
from GN_assignment import find_valid_solution, compute_stretch

# Dark mode color scheme
BG_COLOR = "#2d2d2d"
FG_COLOR = "#ffffff"
ENTRY_BG = "#3d3d3d"
ENTRY_FG = "#ffffff"
CANVAS_BG = "#1e1e1e"
GRID_COLOR = "#4d4d4d"
BUTTON_BG = "#4a4a4a"
BUTTON_ACTIVE = "#5a5a5a"

# Room colors (similar to your image)
ROOM_COLORS = {
    "A": "#F9EA4C",  
    "B": "#6BA9FB",  
    "C": "#FC9595",  
    "D": "#0193F5",  
    "E": "#FC73BE",  
    "F": "#FBD9A7",  
    "G": "#E37AE3",  
    "H": "#9F78EF",  
    "I": "#CCFFCC",  
    "J": "#BAB7BA"   
}

user_inputs = {}
SAVE_FILE = "last_input.json"
room_placements = {}
actual_edges_satisfied = []  # Store which edges were actually satisfied

def show_instructions():
    instructions = """
ROOM LAYOUT PLANNER - INSTRUCTIONS

GENERAL USAGE:
1. Enter outer grid dimensions (width and height)
2. Specify number of holes and their dimensions  
3. Set room sizes and labels for each room (A-J)
4. Add adjacency requirements (e.g., "A B" means rooms A and B must be adjacent)
5. Click Submit to generate the layout

FEATURES:
- Room Labels: Each room can have a custom name/label
- Dimension Display: Shows both user requirements (in brackets) and actual placement
- Adjacency Lines: Green lines show satisfied adjacencies
- Swapping Lines: Red dashed lines show room conflicts
- Dynamic Holes: Red areas show holes as you input them
- Real Algorithm: Uses Z3 solver for optimal room placement

KEYBOARD SHORTCUTS:
- Tab: Move to next input field
- Enter: Move to next field or generate layout
- Escape: Close application
"""
    messagebox.showinfo("Application Instructions", instructions.strip())

def save_inputs():
    with open(SAVE_FILE, "w") as f:
        json.dump(user_inputs, f)

def load_inputs():
    if not os.path.exists(SAVE_FILE):
        return
    with open(SAVE_FILE, "r") as f: # Opens the save file (last_input.json) in read mode ("r"); Uses a context manager (with) to ensure proper file handling/closure; f becomes the file object
        data = json.load(f) #loads entire json file into a python dictionary called data
        entry_width.insert(0, str(data.get("outer_width", ""))) #data.get("outer_width", ""): Safely gets value for "outer_width" key, returns empty string if not found
        entry_height.insert(0, str(data.get("outer_height", ""))) #str(): Converts the value to string (input fields need text)
        entry_num_holes.insert(0, str(len(data.get("holes", [])))) #entry_width.insert(0, ...): Inserts this text at position 0 (beginning) of the "Width" input field
        adj_text = data.get("edges_text", "")
        text_edges.delete("1.0", "end")
        text_edges.insert("1.0", adj_text)
        
        generate_hole_fields() #First creates empty input fields for holes based on the saved count
        for i, hole in enumerate(data.get("holes", [])): #enumerate() allows you to loop through data["holes"] and get the index (i) for each hole, each hole is a list/ tuple of 4 values [x,y,w,h] looped over by j: thus upadating all 4 fields of each hole
            for j in range(4):
                hole_entries[i][j].insert(0, str(hole[j]))

        room_labels_saved = data.get("room_labels", {})

        for name, room_data in data.get("rooms", {}).items(): #This fetches the value of "rooms" in the dictionary data, If "rooms" does not exist, it defaults to an empty dictionary ({}) to prevent errors; For dictionaries, .items() returns each key-value ("A":"dimensions + label") pair as a tuple. 
            if name in room_entries:
                if isinstance(room_data, (tuple, list)): #Checks if the data for this room is a tuple or list (old-style data format)
                    dims = room_data
                    label = name
                elif isinstance(room_data, dict):
                    dims = room_data.get("dims", (0,0,0,0))
                    label = room_data.get("label", name) 
                else:
                    dims = (0,0,0,0)
                    label = name

                # Use saved label if present
                if room_labels_saved.get(name): 
                    label = room_labels_saved[name]

                dims = list(dims) + [0]*(4-len(dims))
                room_entries[name][0].insert(0, str(dims[0]))
                room_entries[name][1].insert(0, str(dims[1]))
                room_entries[name][2].insert(0, str(dims[2]))
                room_entries[name][3].insert(0, str(dims[3]))
                room_entries[name][4].insert(0, label)
room_names = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]

def submit_data(event=None):
    try:
        if not entry_width.get() or not entry_height.get():   #Checks if the outer grid's width/height fields are empty. Shows an error if missing
            messagebox.showerror("Input Error", "Outer grid dimensions must be specified")
            return

        outer_width = int(entry_width.get()) #Converts input values to integers. Handles empty hole count as 0
        outer_height = int(entry_height.get())
        num_holes = int(entry_num_holes.get()) if entry_num_holes.get() else 0 

        holes = []
        for i in range(num_holes):
            if (not hole_entries[i][0].get() or not hole_entries[i][1].get() or
                not hole_entries[i][2].get() or not hole_entries[i][3].get()): #Processes holes.If any field is missing, skips this hole entirely (continue) since cant convert blank string to int: error prevention
                continue 
            try:
                x = int(hole_entries[i][0].get()) #For holes with all fields filled, tries to convert inputs to integers
                y = int(hole_entries[i][1].get()) #Creates a tuple (x, y, w, h) with hole coordinates/size
                w = int(hole_entries[i][2].get())
                h = int(hole_entries[i][3].get())
                holes.append((x, y, w, h)) # Adds this hole to the holes list
            except ValueError:
                messagebox.showerror("Input Error", f"Invalid hole #{i+1} dimensions") #If conversion to integers fails (non-numeric input), shows error with hole number
                return

        rooms = {}

        for name in room_names:
            if (not room_entries[name][0].get() or not room_entries[name][1].get() or
                room_entries[name][0].get() == "0" or room_entries[name][1].get() == "0"):
                continue
            try:
                min_width  = int(room_entries[name][0].get())
                min_height = int(room_entries[name][1].get())
                max_width_str = room_entries[name][2].get().strip()
                max_height_str = room_entries[name][3].get().strip()
        
        # -- HERE IS THE PATCH --
                max_width = int(max_width_str) if max_width_str else outer_width
                max_height = int(max_height_str) if max_height_str else outer_height

                label = room_entries[name][4].get() or name
                rooms[name] = (min_width, min_height, max_width, max_height)
            except ValueError:
                messagebox.showerror("Input Error", f"Invalid dimensions for room {name}")
                return


        edges_raw = text_edges.get("1.0", "end").strip()
        edges_list = []
        for line in edges_raw.splitlines():
            line = line.strip()
            if line:
                parts = line.split()
                if len(parts) == 2 and parts[0] in room_names and parts[1] in room_names:
                    edges_list.append((parts[0], parts[1]))
        
        user_inputs["edges"] = edges_list
        user_inputs["edges_text"] = edges_raw  # Save raw text here

        # Store for algorithm
        user_inputs["outer_width"] = outer_width
        user_inputs["outer_height"] = outer_height  
        user_inputs["holes"] = holes
        user_inputs["rooms"] = rooms
        user_inputs["edges"] = edges_list
        
        # Store labels separately for display
        user_inputs["room_labels"] = {}
        for name in room_names:
            if room_entries[name][4].get():
                user_inputs["room_labels"][name] = room_entries[name][4].get()
            else:
                user_inputs["room_labels"][name] = name
        
        save_inputs()
        
        # Generate and display the layout using real algorithm
        generate_layout()
        
    except Exception as e:
        messagebox.showerror("Input Error", str(e))

def generate_layout():
    """Generate the actual room layout using the GN_assignment algorithm"""
    global room_placements, actual_edges_satisfied
    
    try:
        # Set up the global variables that GN_assignment expects
        import GN_assignment
        GN_assignment.rooms = user_inputs["rooms"]
        GN_assignment.edges = user_inputs["edges"]
        GN_assignment.outer_width = user_inputs["outer_width"]
        GN_assignment.outer_height = user_inputs["outer_height"]
        GN_assignment.holes = user_inputs["holes"]
        
        print("Running room layout algorithm...")
        
        # Call the actual algorithm
        initial_layout, used_edges = find_valid_solution(
            user_inputs["rooms"], 
            user_inputs["edges"], 
            user_inputs["outer_width"], 
            user_inputs["outer_height"], 
            user_inputs["holes"])
        
        if initial_layout is None:
            messagebox.showerror("Algorithm Error", "No valid layout found by the algorithm")
            return
            
        print("Initial layout found, computing stretch...")
        
        # Compute the stretched layout
        stretched_rectangles = compute_stretch(
            initial_layout, 
            user_inputs["rooms"], 
            used_edges, 
            user_inputs["outer_width"], 
            user_inputs["outer_height"], 
            user_inputs["holes"])
        
        print("Stretch computation complete")
        
        # Convert to format expected by GUI
        room_placements = {}
        for name, (x, y, w, h) in stretched_rectangles.items():
            room_placements[name] = {
                "pos": (x, y),
                "size": (w, h),
                "label": user_inputs["room_labels"].get(name, name)
            }
        
        # Store which edges were actually satisfied
        actual_edges_satisfied = used_edges
        
        print(f"Layout generated with {len(room_placements)} rooms")
        print(f"Satisfied {len(actual_edges_satisfied)} out of {len(user_inputs['edges'])} adjacency constraints")
        
        draw_layout()
        
    except Exception as e:
        print(f"Error in generate_layout: {e}")
        messagebox.showerror("Algorithm Error", f"Error running layout algorithm: {str(e)}")

def draw_layout():
    """Draw the complete layout with rooms, labels, and adjacency lines"""
    layout_canvas.delete("all")
    
    try:
        width = user_inputs["outer_width"]
        height = user_inputs["outer_height"]
        
        canvas_width = layout_canvas.winfo_width()
        canvas_height = layout_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            layout_canvas.after(100, draw_layout)
            return
            
        scale = min(canvas_width / width, canvas_height / height) * 0.85
        offset_x = (canvas_width - width * scale) / 2
        offset_y = (canvas_height - height * scale) / 2
        
        # Draw grid outline
        layout_canvas.create_rectangle(
            offset_x, offset_y,
            offset_x + width * scale, offset_y + height * scale,
            outline=FG_COLOR, width=2
        )
        
        # Draw holes first (so they appear behind rooms)
        draw_holes(offset_x, offset_y, scale, height)
        
        # Draw rooms on top
        for room_id, room_data in room_placements.items():
            x, y = room_data["pos"]
            w, h = room_data["size"]
            label = room_data["label"]
            
            # Get user requested dimensions
            user_dims = user_inputs["rooms"][room_id]
            user_w, user_h = user_dims[0], user_dims[1]
            
            # Calculate screen coordinates
            x1 = offset_x + x * scale
            y1 = offset_y + (height - y - h) * scale
            x2 = x1 + w * scale
            y2 = y1 + h * scale
            
            # Draw room rectangle
            layout_canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=ROOM_COLORS.get(room_id, "#CCCCCC"),
                outline="black",
                width=1
            )
            
            # Draw room label and dimensions
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            
            # Room label
            layout_canvas.create_text(
                center_x, center_y - 15,
                text=label,
                fill="black",
                font=("Arial", 9, "bold"),
                anchor="center"
            )
            
            # Actual dimensions
            layout_canvas.create_text(
                center_x, center_y,
                text=f"{w}x{h}",
                fill="black", 
                font=("Arial", 8),
                anchor="center"
            )
            
            # User requested dimensions (in brackets)
            layout_canvas.create_text(
                center_x, center_y + 15,
                text=f"(from {user_w}x{user_h})",
                fill="black",
                font=("Arial", 7),
                anchor="center"
            )

            # Draw adjacency lines (green) - on top of rooms
            draw_adjacency_lines(offset_x, offset_y, scale, height)
        
            # Draw unsatisfied adjacency lines (red dashed) - on top of rooms  
            draw_unsatisfied_adjacency_lines(offset_x, offset_y, scale, height)
        
    except Exception as e:
        print(f"Error drawing layout: {e}")

def draw_holes(offset_x, offset_y, scale, grid_height):
    """Draw holes as WHITE rectangles (changed from red)"""
    for hole in user_inputs.get("holes", []):
        x, y, w, h = hole
        # Convert to screen coordinates
        x1 = offset_x + x * scale
        y1 = offset_y + (grid_height - y - h) * scale
        x2 = x1 + w * scale
        y2 = y1 + h * scale
        # Draw hole as WHITE rectangle (changed from red)
        layout_canvas.create_rectangle(
            x1, y1, x2, y2,
            fill="white",     # Changed from "#d63031" to "white"
            outline="gray",   # Changed from "#a61e1e" to "gray"
            width=1
        )

def draw_adjacency_lines(offset_x, offset_y, scale, grid_height):
    """Draw GREEN lines for satisfied adjacencies"""
    for edge in actual_edges_satisfied:
        room1, room2 = edge
        if room1 in room_placements and room2 in room_placements:
            r1_data = room_placements[room1]
            r2_data = room_placements[room2]
            r1_x = r1_data["pos"][0] + r1_data["size"][0] / 2
            r1_y = r1_data["pos"][1] + r1_data["size"][1] / 2
            r2_x = r2_data["pos"][0] + r2_data["size"][0] / 2
            r2_y = r2_data["pos"][1] + r2_data["size"][1] / 2
            x1 = offset_x + r1_x * scale
            y1 = offset_y + (grid_height - r1_y) * scale
            x2 = offset_x + r2_x * scale
            y2 = offset_y + (grid_height - r2_y) * scale
            layout_canvas.create_line(
                x1, y1, x2, y2,
                fill="lime",      # Bright green
                width=2
            )

def draw_unsatisfied_adjacency_lines(offset_x, offset_y, scale, grid_height):
    """Draw RED dashed lines for unsatisfied adjacencies"""
    all_edges = set(user_inputs.get("edges", []))
    satisfied_edges = set(actual_edges_satisfied)
    unsatisfied_edges = all_edges - satisfied_edges
    for edge in unsatisfied_edges:
        room1, room2 = edge
        if room1 in room_placements and room2 in room_placements:
            r1_data = room_placements[room1]
            r2_data = room_placements[room2]
            r1_x = r1_data["pos"][0] + r1_data["size"][0] / 2
            r1_y = r1_data["pos"][1] + r1_data["size"][1] / 2
            r2_x = r2_data["pos"][0] + r2_data["size"][0] / 2
            r2_y = r2_data["pos"][1] + r2_data["size"][1] / 2
            x1 = offset_x + r1_x * scale
            y1 = offset_y + (grid_height - r1_y) * scale
            x2 = offset_x + r2_x * scale
            y2 = offset_y + (grid_height - r2_y) * scale
            layout_canvas.create_line(
                x1, y1, x2, y2,
                fill="red",
                width=2,
                dash=(8,4)
            )

def on_hole_entry_change(*args):
    """Update canvas when hole entries change"""
    layout_canvas.after(50, draw_preview)

def draw_preview():
    """Draw preview with holes while user is inputting"""
    if not entry_width.get() or not entry_height.get():
        return
        
    try:
        width = int(entry_width.get())
        height = int(entry_height.get())
        
        # Only redraw if we're not showing a full layout
        if not room_placements:
            layout_canvas.delete("all")
            
            canvas_width = layout_canvas.winfo_width()
            canvas_height = layout_canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                return
                
            scale = min(canvas_width / width, canvas_height / height) * 0.85
            offset_x = (canvas_width - width * scale) / 2
            offset_y = (canvas_height - height * scale) / 2
            
            # Draw grid outline
            layout_canvas.create_rectangle(
                offset_x, offset_y,
                offset_x + width * scale, offset_y + height * scale,
                outline=FG_COLOR, width=2
            )
            
            # Draw holes from current input
            for i, hole_entry_set in enumerate(hole_entries):
                try:
                    if all(entry.get() for entry in hole_entry_set):
                        x = int(hole_entry_set[0].get())
                        y = int(hole_entry_set[1].get())
                        w = int(hole_entry_set[2].get())
                        h = int(hole_entry_set[3].get())
                        
                        # Convert to screen coordinates
                        x1 = offset_x + x * scale
                        y1 = offset_y + (height - y - h) * scale
                        x2 = x1 + w * scale
                        y2 = y1 + h * scale
                        
                        # Draw hole as red rectangle
                        layout_canvas.create_rectangle(
                            x1, y1, x2, y2,
                            fill="#f9f8f8",
                            outline="#7a7a7a",
                            width=1
                        )
                except (ValueError, IndexError):
                    continue
                    
    except ValueError:
        pass

def generate_hole_fields():
    for widgets in hole_frame.winfo_children():
        widgets.destroy()

    try:
        num = int(entry_num_holes.get()) if entry_num_holes.get() else 0
        global hole_entries
        hole_entries = []

        for i in range(num):
            label = tk.Label(hole_frame, text=f"Hole #{i+1} (x y w h):", bg=BG_COLOR, fg=FG_COLOR)
            label.grid(row=i, column=0, padx=5, pady=3, sticky="e")

            x_entry = tk.Entry(hole_frame, width=5, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
            y_entry = tk.Entry(hole_frame, width=5, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
            w_entry = tk.Entry(hole_frame, width=5, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
            h_entry = tk.Entry(hole_frame, width=5, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)

            # Bind change events for dynamic preview
            for entry in [x_entry, y_entry, w_entry, h_entry]:
                entry.bind('<KeyRelease>', on_hole_entry_change)

            x_entry.grid(row=i, column=1, padx=2)
            y_entry.grid(row=i, column=2, padx=2)
            w_entry.grid(row=i, column=3, padx=2)
            h_entry.grid(row=i, column=4, padx=2)

            hole_entries.append((x_entry, y_entry, w_entry, h_entry))
            
        # Trigger initial preview
        draw_preview()

    except ValueError:
        pass

# GUI setup (rest of the code remains the same)
root = tk.Tk()
root.title("Room Layout Planner - Real Algorithm")
root.geometry("1400x800")
root.minsize(1200, 700)
root.configure(bg=BG_COLOR)

# Main container
main_container = tk.Frame(root, bg=BG_COLOR)
main_container.pack(fill="both", expand=True, padx=10, pady=10)

# Left panel for inputs
left_panel = tk.Frame(main_container, bg=BG_COLOR, width=400)
left_panel.pack(side="left", fill="y", padx=(0, 10))
left_panel.pack_propagate(False)

# Right panel for layout display  
right_panel = tk.Frame(main_container, bg=BG_COLOR)
right_panel.pack(side="right", fill="both", expand=True)

# Input form (left panel)
form_frame = tk.Frame(left_panel, bg=BG_COLOR)
form_frame.pack(fill="both", expand=True)

# Grid dimensions
dim_frame = tk.Frame(form_frame, bg=BG_COLOR)
dim_frame.pack(fill="x", pady=5)

tk.Label(dim_frame, text="Width:", bg=BG_COLOR, fg=FG_COLOR).pack(side="left")
entry_width = tk.Entry(dim_frame, width=8, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
entry_width.pack(side="left", padx=5)
entry_width.bind('<KeyRelease>', on_hole_entry_change)

tk.Label(dim_frame, text="Height:", bg=BG_COLOR, fg=FG_COLOR).pack(side="left")
entry_height = tk.Entry(dim_frame, width=8, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
entry_height.pack(side="left", padx=5)
entry_height.bind('<KeyRelease>', on_hole_entry_change)

# Holes
holes_frame = tk.Frame(form_frame, bg=BG_COLOR)
holes_frame.pack(fill="x", pady=5)

tk.Label(holes_frame, text="Holes:", bg=BG_COLOR, fg=FG_COLOR).pack(side="left")
entry_num_holes = tk.Entry(holes_frame, width=5, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
entry_num_holes.pack(side="left", padx=5)

set_holes_btn = tk.Button(holes_frame, text="Set", command=generate_hole_fields, 
                         bg=BUTTON_BG, fg=FG_COLOR, activebackground=BUTTON_ACTIVE)
set_holes_btn.pack(side="left", padx=5)

hole_frame = tk.Frame(form_frame, bg=BG_COLOR)
hole_frame.pack(fill="x", pady=5)

# Room inputs with labels
tk.Label(form_frame, text="Rooms (min_w min_h max_w max_h label):", 
         font=("Arial", 10, "bold"), bg=BG_COLOR, fg=FG_COLOR).pack(pady=5)

room_frame = tk.Frame(form_frame, bg=BG_COLOR)
room_frame.pack(fill="x")

room_entries = {}
for name in room_names:
    frame = tk.Frame(room_frame, bg=BG_COLOR)
    frame.pack(fill="x", pady=2)
    
    tk.Label(frame, text=f"{name}:", bg=BG_COLOR, fg=FG_COLOR, width=2).pack(side="left")
    
    w_entry = tk.Entry(frame, width=4, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
    w_entry.pack(side="left", padx=1)
    
    h_entry = tk.Entry(frame, width=4, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)  
    h_entry.pack(side="left", padx=1)
    
    max_w_entry = tk.Entry(frame, width=4, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
    max_w_entry.pack(side="left", padx=1)
    
    max_h_entry = tk.Entry(frame, width=4, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
    max_h_entry.pack(side="left", padx=1)
    
    label_entry = tk.Entry(frame, width=12, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
    label_entry.pack(side="left", padx=2)
    
    room_entries[name] = (w_entry, h_entry, max_w_entry, max_h_entry, label_entry)

# Adjacency edges
tk.Label(form_frame, text="Adjacency (A B):", font=("Arial", 10, "bold"), 
         bg=BG_COLOR, fg=FG_COLOR).pack(pady=5)

text_edges = tk.Text(form_frame, height=8, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
text_edges.pack(fill="x", pady=5)

# Buttons
button_frame = tk.Frame(form_frame, bg=BG_COLOR)
button_frame.pack(fill="x", pady=10)

submit_btn = tk.Button(button_frame, text="Generate Layout", command=submit_data,
                      bg=BUTTON_BG, fg=FG_COLOR, activebackground=BUTTON_ACTIVE)
submit_btn.pack(side="left", padx=5)

help_btn = tk.Button(button_frame, text="Help", command=show_instructions,
                    bg=BUTTON_BG, fg=FG_COLOR, activebackground=BUTTON_ACTIVE)
help_btn.pack(side="left", padx=5)

# Layout display (right panel)
tk.Label(right_panel, text="Floor Plan Layout", font=("Arial", 14, "bold"), 
         bg=BG_COLOR, fg=FG_COLOR).pack(pady=5)

layout_canvas = tk.Canvas(right_panel, bg=CANVAS_BG, highlightthickness=1, 
                         highlightbackground=FG_COLOR)
layout_canvas.pack(fill="both", expand=True, padx=5, pady=5)

# Initialize
hole_entries = []
entry_width.focus_set()
load_inputs()

root.mainloop()
