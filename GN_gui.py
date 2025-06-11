import tkinter as tk
import json
import os
import time
from tkinter import messagebox
from GN_assignment import main as original_main

# Dark mode color scheme
BG_COLOR = "#2d2d2d"
FG_COLOR = "#ffffff"
ENTRY_BG = "#3d3d3d"
ENTRY_FG = "#ffffff"
CANVAS_BG = "#1e1e1e"
GRID_COLOR = "#4d4d4d"
BUTTON_BG = "#4a4a4a"
BUTTON_ACTIVE = "#5a5a5a"
HOLE_COLORS = {
    "normal": "#d63031",      # Red for valid holes
    "out_of_bounds": "#fdcb6e",  # Yellow for out-of-bounds
    "overlap": "#e17055",     # Orange for overlapping
    "both": "#6c5ce7"        # Purple for both issues
}

user_inputs = {}
SAVE_FILE = "last_input.json"
last_draw_time = 0

def show_instructions():
    instructions = """
    ROOM LAYOUT PLANNER - INSTRUCTIONS

    GENERAL USAGE:
    1. Enter outer grid dimensions (width and height)
    2. Specify number of holes and their dimensions
    3. Set room sizes for each room (A-J)
    4. Add adjacency requirements (e.g., "A B" means rooms A and B must be adjacent)
    5. Click Submit to generate the layout

    KEYBOARD SHORTCUTS:
    - Tab: Move to next input field
    - Shift+Tab: Move to previous input field
    - Enter: 
      * In dimension fields: Move to next field
      * In hole count field: Generate hole input fields
      * In room size fields: Move to next room
    - Escape: Close the application

    HOLE VALIDATION COLORS:
    - Red: Valid hole
    - Yellow: Hole extends outside grid
    - Orange: Overlapping with another hole
    - Purple: Both outside grid AND overlapping

    TIPS:
    - The preview updates automatically as you type
    - Empty room dimensions will exclude that room
    - Empty hole dimensions will exclude that hole
    - Your inputs are saved automatically and will load next time

    NAVIGATION:
    - Use mouse wheel to scroll through the form
    - Click on any field to edit it
    """
    messagebox.showinfo("Application Instructions", instructions.strip())

def save_inputs():
    with open(SAVE_FILE, "w") as f:
        json.dump(user_inputs, f)

def load_inputs():
    if not os.path.exists(SAVE_FILE):
        return

    with open(SAVE_FILE, "r") as f:
        data = json.load(f)

    entry_width.insert(0, str(data.get("outer_width", "")))
    entry_height.insert(0, str(data.get("outer_height", "")))
    entry_num_holes.insert(0, str(len(data.get("holes", []))))
    generate_hole_fields()

    for i, hole in enumerate(data.get("holes", [])):
        for j in range(4):
            hole_entries[i][j].insert(0, str(hole[j]))

    for name, dims in data.get("rooms", {}).items():
        if name in room_entries:
            room_entries[name][0].insert(0, str(dims[0]))
            room_entries[name][1].insert(0, str(dims[1]))

    text_edges.insert("1.0", "\n".join(f"{a} {b}" for a, b in data.get("edges", [])))

room_names = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]

def validate_number(input_str, field_name, min_val=1):
    if not input_str:
        return True
    try:
        value = int(input_str)
        if value < min_val:
            raise ValueError(f"{field_name} must be at least {min_val}")
        return True
    except ValueError:
        messagebox.showerror("Input Error", f"Please enter a valid integer for {field_name}")
        return False

def submit_data(event=None):
    try:
        # Validate main dimensions (must be specified)
        if not entry_width.get() or not entry_height.get():
            messagebox.showerror("Input Error", "Outer grid dimensions must be specified")
            return
            
        outer_width = int(entry_width.get())
        outer_height = int(entry_height.get())
        
        # Number of holes can be zero
        num_holes = int(entry_num_holes.get()) if entry_num_holes.get() else 0

        holes = []
        for i in range(num_holes):
            # Skip hole if any dimension is blank
            if (not hole_entries[i][0].get() or not hole_entries[i][1].get() or 
                not hole_entries[i][2].get() or not hole_entries[i][3].get()):
                continue
                
            try:
                x = int(hole_entries[i][0].get())
                y = int(hole_entries[i][1].get())
                w = int(hole_entries[i][2].get())
                h = int(hole_entries[i][3].get())
                holes.append((x, y, w, h))
            except ValueError:
                messagebox.showerror("Input Error", f"Invalid hole #{i+1} dimensions")
                return

        rooms = {}
        for name in room_names:
            # Skip room if either dimension is blank or zero
            if (not room_entries[name][0].get() or not room_entries[name][1].get() or
                room_entries[name][0].get() == "0" or room_entries[name][1].get() == "0"):
                continue
                
            try:
                width = int(room_entries[name][0].get())
                height = int(room_entries[name][1].get())
                max_width_str = room_entries[name][2].get()
                max_height_str = room_entries[name][3].get()

                max_width = int(max_width_str) if max_width_str else max(outer_width, outer_height)
                max_height = int(max_height_str) if max_height_str else max(outer_width, outer_height)

                if max_width < width or max_height < height:
                    raise ValueError(f"Max dimensions for room {name} must be >= min dimensions")

                rooms[name] = (width, height, max_width, max_height)

            except ValueError as e:
                messagebox.showerror("Input Error", f"Invalid dimensions for room {name}")
                return

        edges_raw = text_edges.get("1.0", "end").strip().splitlines()
        edges = []
        for line in edges_raw:
            if not line.strip():
                continue
            parts = line.strip().split()
            if len(parts) == 2 and parts[0] in room_names and parts[1] in room_names:
                # Only add edge if both rooms exist
                if parts[0] in rooms and parts[1] in rooms:
                    edges.append((parts[0], parts[1]))
            else:
                raise ValueError(f"Invalid edge format: '{line}'")

        user_inputs["outer_width"] = outer_width
        user_inputs["outer_height"] = outer_height
        user_inputs["holes"] = holes
        user_inputs["rooms"] = rooms
        user_inputs["edges"] = edges

        save_inputs()
        root.destroy()

    except Exception as e:
        messagebox.showerror("Input Error", str(e))

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
            
            x_entry.grid(row=i, column=1, padx=2)
            y_entry.grid(row=i, column=2, padx=2)
            w_entry.grid(row=i, column=3, padx=2)
            h_entry.grid(row=i, column=4, padx=2)
            hole_entries.append((x_entry, y_entry, w_entry, h_entry))
        
        if hole_entries:
            hole_entries[0][0].focus_set()
        
        setup_automatic_updates()
        draw_grid()
    except ValueError:
        pass

def draw_grid(event=None):
    global last_draw_time
    current_time = time.time()
    if current_time - last_draw_time < 0.1:
        return
    last_draw_time = current_time
    
    try:
        grid_canvas.delete("all")
        width = int(entry_width.get()) if entry_width.get() else 10
        height = int(entry_height.get()) if entry_height.get() else 10
        canvas_width = grid_canvas.winfo_width()
        canvas_height = grid_canvas.winfo_height()
        
        scale = min(canvas_width / width, canvas_height / height) * 0.9
        grid_width = width * scale
        grid_height = height * scale
        offset_x = (canvas_width - grid_width) / 2
        offset_y = (canvas_height - grid_height) / 2

        # Draw outline
        grid_canvas.create_rectangle(
            offset_x,
            offset_y,
            offset_x + grid_width,
            offset_y + grid_height,
            outline=FG_COLOR,
            width=2
        )

        # Draw grid lines
        for i in range(width + 1):
            x = offset_x + i * scale
            grid_canvas.create_line(x, offset_y, x, offset_y + grid_height, fill=GRID_COLOR)
        for j in range(height + 1):
            y = offset_y + j * scale
            grid_canvas.create_line(offset_x, y, offset_x + grid_width, y, fill=GRID_COLOR)

        # Process holes
        if 'hole_entries' in globals():
            num_holes = min(int(entry_num_holes.get()), len(hole_entries)) if entry_num_holes.get() else 0
            holes = []
            
            for i in range(num_holes):
                # Skip hole if any dimension is blank
                if (not hole_entries[i][0].get() or not hole_entries[i][1].get() or 
                    not hole_entries[i][2].get() or not hole_entries[i][3].get()):
                    continue
                    
                try:
                    x = int(hole_entries[i][0].get())
                    y = int(hole_entries[i][1].get())
                    w = int(hole_entries[i][2].get())
                    h = int(hole_entries[i][3].get())
                    holes.append((x, y, w, h))
                except ValueError:
                    continue

            # Validate holes
            overlap_indices = set()
            out_of_bounds_indices = set()
            
            for i in range(len(holes)):
                x1, y1, w1, h1 = holes[i]
                
                if (x1 < 0 or y1 < 0 or x1 + w1 > width or y1 + h1 > height):
                    out_of_bounds_indices.add(i)
                
                for j in range(i + 1, len(holes)):
                    x2, y2, w2, h2 = holes[j]
                    if not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1):
                        overlap_indices.add(i)
                        overlap_indices.add(j)

            # Draw holes with appropriate colors
            for i, (x, y, w, h) in enumerate(holes):
                x1 = offset_x + x * scale
                y1 = offset_y + (height - y - h) * scale
                x2 = x1 + w * scale
                y2 = y1 + h * scale
                
                if i in overlap_indices and i in out_of_bounds_indices:
                    color = HOLE_COLORS["both"]
                elif i in overlap_indices:
                    color = HOLE_COLORS["overlap"]
                elif i in out_of_bounds_indices:
                    color = HOLE_COLORS["out_of_bounds"]
                else:
                    color = HOLE_COLORS["normal"]
                
                grid_canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=color,
                    stipple="gray50",
                    outline="white"
                )

    except Exception as e:
        pass


def setup_automatic_updates():
    entry_width.bind("<KeyRelease>", lambda e: draw_grid())
    entry_height.bind("<KeyRelease>", lambda e: draw_grid())
    entry_num_holes.bind("<KeyRelease>", lambda e: [generate_hole_fields(), draw_grid()])
    
    if 'hole_entries' in globals():
        for i in range(len(hole_entries)):
            for j in range(4):
                hole_entries[i][j].bind("<KeyRelease>", lambda e: draw_grid())
    
    grid_canvas.bind("<Configure>", lambda e: draw_grid())

def focus_next_widget(event):
    event.widget.tk_focusNext().focus()
    return "break"

def focus_prev_widget(event):
    event.widget.tk_focusPrev().focus()
    return "break"

# GUI setup with dark theme
root = tk.Tk()
root.title("Room Layout Input - Dark Mode")
root.geometry("900x700")
root.minsize(800, 600)
root.configure(bg=BG_COLOR)

# Configure root grid
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)

# Main container frame
main_container = tk.Frame(root, bg=BG_COLOR)
main_container.grid(row=0, column=0, sticky="nsew")
main_container.grid_rowconfigure(0, weight=1)
main_container.grid_columnconfigure(0, weight=1)

# Canvas and Scrollbar
canvas = tk.Canvas(main_container, bg=BG_COLOR, highlightthickness=0)
scrollbar = tk.Scrollbar(main_container, orient="vertical", command=canvas.yview, bg=BG_COLOR)
scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)

scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.grid(row=0, column=0, sticky="nsew")
scrollbar.grid(row=0, column=1, sticky="ns")

main_container.grid_columnconfigure(0, weight=1)
main_container.grid_rowconfigure(0, weight=1)

# Mousewheel scrolling
def _on_mousewheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

canvas.bind_all("<MouseWheel>", _on_mousewheel)
canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

# Main content frame
content_frame = tk.Frame(scrollable_frame, bg=BG_COLOR)
content_frame.pack(fill="both", expand=True, padx=10, pady=10)

# Left form frame
form_frame = tk.Frame(content_frame, bg=BG_COLOR)
form_frame.pack(side="left", fill="both", expand=True)

# Right preview frame
preview_frame = tk.Frame(content_frame, bg=BG_COLOR)
preview_frame.pack(side="right", fill="both", expand=True)

# Grid dimensions
dim_frame = tk.Frame(form_frame, bg=BG_COLOR)
dim_frame.pack(fill="x", pady=5)

tk.Label(dim_frame, text="Outer Grid Width:", bg=BG_COLOR, fg=FG_COLOR).pack(side="left", padx=5)
entry_width = tk.Entry(dim_frame, width=10, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
entry_width.pack(side="left", padx=5)
entry_width.bind("<Return>", lambda e: entry_height.focus())

tk.Label(dim_frame, text="Outer Grid Height:", bg=BG_COLOR, fg=FG_COLOR).pack(side="left", padx=5)
entry_height = tk.Entry(dim_frame, width=10, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
entry_height.pack(side="left", padx=5)
entry_height.bind("<Return>", lambda e: entry_num_holes.focus())

# Holes
holes_frame = tk.Frame(form_frame, bg=BG_COLOR)
holes_frame.pack(fill="x", pady=5)

tk.Label(holes_frame, text="Number of Holes:", bg=BG_COLOR, fg=FG_COLOR).pack(side="left", padx=5)
entry_num_holes = tk.Entry(holes_frame, width=5, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
entry_num_holes.pack(side="left", padx=5)
entry_num_holes.bind("<Return>", lambda e: generate_hole_fields())

set_holes_btn = tk.Button(
    holes_frame, 
    text="Set Hole Fields", 
    command=lambda: [generate_hole_fields(), draw_grid()],
    bg=BUTTON_BG, 
    fg=FG_COLOR,
    activebackground=BUTTON_ACTIVE,
    activeforeground=FG_COLOR,
    relief=tk.FLAT,
    borderwidth=0,
    highlightthickness=0
)
set_holes_btn.pack(side="left", padx=10)

hole_frame = tk.Frame(form_frame, bg=BG_COLOR)
hole_frame.pack(fill="x", pady=5)

# Room sizes
tk.Label(
    form_frame, 
    text="Room Sizes (min_width min_height max_width max_height):", 
    font=("Helvetica", 10, "bold"), 
    bg=BG_COLOR, 
    fg=FG_COLOR
).pack(pady=5)

room_frame = tk.Frame(form_frame, bg=BG_COLOR)
room_frame.pack(fill="x")

room_entries = {}
for i, name in enumerate(room_names):
    frame = tk.Frame(room_frame, bg=BG_COLOR)
    frame.pack(fill="x", pady=2)
    tk.Label(frame, text=f"{name}:", bg=BG_COLOR, fg=FG_COLOR).pack(side="left", padx=5)
    width_entry = tk.Entry(frame, width=6, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
    width_entry.pack(side="left", padx=5)
    height_entry = tk.Entry(frame, width=6, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
    height_entry.pack(side="left", padx=5)
    max_width_entry = tk.Entry(frame, width=6, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
    max_width_entry.pack(side="left", padx=5)
    max_height_entry = tk.Entry(frame, width=6, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
    max_height_entry.pack(side="left", padx=5)

    room_entries[name] = (width_entry, height_entry, max_width_entry, max_height_entry)

    
    # Bind Enter key to move to next field
    width_entry.bind("<Return>", lambda e, n=name: room_entries[n][1].focus() if n in room_entries else None)
    height_entry.bind("<Return>", 
        lambda e, n=name, i=i: room_entries[room_names[i+1]][0].focus() 
        if i < len(room_names)-1 else text_edges.focus())

# Edges input
tk.Label(
    form_frame, 
    text="Adjacency Edges (e.g., A B):", 
    font=("Helvetica", 10, "bold"), 
    bg=BG_COLOR, 
    fg=FG_COLOR
).pack(pady=5)

text_edges = tk.Text(
    form_frame, 
    height=10, 
    width=30, 
    bg=ENTRY_BG, 
    fg=ENTRY_FG,
    insertbackground=FG_COLOR
)
text_edges.pack(fill="x", pady=5)

# Submit button
button_frame = tk.Frame(form_frame, bg=BG_COLOR)
button_frame.pack(fill="x", pady=10)

submit_btn = tk.Button(
    button_frame, 
    text="Submit", 
    command=submit_data,
    bg=BUTTON_BG,
    fg=FG_COLOR,
    activebackground=BUTTON_ACTIVE,
    activeforeground=FG_COLOR,
    relief=tk.FLAT,
    borderwidth=0,
    highlightthickness=0
)
submit_btn.pack(side="left", padx=5, ipadx=20)

# Add Help button next to Submit
help_btn = tk.Button(
    button_frame, 
    text="Help", 
    command=show_instructions,
    bg=BUTTON_BG,
    fg=FG_COLOR,
    activebackground=BUTTON_ACTIVE,
    activeforeground=FG_COLOR,
    relief=tk.FLAT,
    borderwidth=0,
    highlightthickness=0
)
help_btn.pack(side="left", padx=5, ipadx=20)

# Bind keyboard shortcuts
root.bind("<Escape>", lambda e: root.destroy())

# Configure tab navigation
for widget in [entry_width, entry_height, entry_num_holes, set_holes_btn]:
    widget.bind("<Tab>", focus_next_widget)
    widget.bind("<Shift-Tab>", focus_prev_widget)

# Canvas for Grid Preview
grid_canvas = tk.Canvas(preview_frame, bg=CANVAS_BG, highlightthickness=0)
grid_canvas.pack(fill="both", expand=True, padx=10, pady=10)

# Set initial focus
entry_width.focus_set()

# Set up automatic updates
setup_automatic_updates()
load_inputs()
root.mainloop()

# Patch the original logic
def patched_get_user_boundary():
    return (
        user_inputs["outer_width"],
        user_inputs["outer_height"],
        user_inputs["holes"],
        user_inputs["rooms"],
        user_inputs["edges"]
    )

# Modify original script interface
import GN_assignment
GN_assignment.get_user_boundary = patched_get_user_boundary

# Patch main() to use custom room and edge input
def patched_main():
    outer_width, outer_height, holes, rooms, edges = GN_assignment.get_user_boundary()

    GN_assignment.rooms = rooms
    GN_assignment.edges = edges

    GN_assignment.outer_width = outer_width
    GN_assignment.outer_height = outer_height
    GN_assignment.holes = holes

    GN_assignment.main()

patched_main()