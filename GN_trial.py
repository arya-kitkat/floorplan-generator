import tkinter as tk
import json
import os
import sys
from tkinter import messagebox

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from GN_assignment import find_valid_solution, compute_stretch

# Color constants
BG_COLOR, FG_COLOR = "#2d2d2d", "#ffffff"
ENTRY_BG, ENTRY_FG = "#3d3d3d", "#ffffff"
CANVAS_BG, GRID_COLOR = "#1e1e1e", "#4d4d4d"
BUTTON_BG, BUTTON_ACTIVE = "#4a4a4a", "#5a5a5a"
ROOM_COLORS = {
    "A": "#90EE90", "B": "#FFB366", "C": "#87CEEB", "D": "#4682B4",
    "E": "#D3D3D3", "F": "#FFFF99", "G": "#D8BFD8", "H": "#9370DB",
    "I": "#F0E68C", "J": "#DDA0DD"
}

SAVE_FILE = "last_input.json"
room_names = list(ROOM_COLORS)
user_inputs, room_placements, actual_edges_satisfied = {}, {}, []

def show_instructions():
    messagebox.showinfo("Application Instructions", """
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
""".strip())

def save_inputs():
    with open(SAVE_FILE, "w") as f:
        json.dump(user_inputs, f)

def insert_entry_values(entries, values):
    for entry, value in zip(entries, values):
        entry.insert(0, str(value))

def load_inputs():
    if not os.path.exists(SAVE_FILE): return
    with open(SAVE_FILE, "r") as f:
        data = json.load(f)
    entry_width.insert(0, str(data.get("outer_width", "")))
    entry_height.insert(0, str(data.get("outer_height", "")))
    entry_num_holes.insert(0, str(len(data.get("holes", []))))
    text_edges.delete("1.0", "end")
    text_edges.insert("1.0", data.get("edges_text", ""))
    generate_hole_fields()
    for i, hole in enumerate(data.get("holes", [])):
        insert_entry_values(hole_entries[i], hole)
    room_labels_saved = data.get("room_labels", {})
    for name, room_data in data.get("rooms", {}).items():
        if name in room_entries:
            if isinstance(room_data, (tuple, list)):
                dims, label = room_data, name
            elif isinstance(room_data, dict):
                dims = room_data.get("dims", (0,0,0,0))
                label = room_data.get("label", name)
            else:
                dims, label = (0,0,0,0), name
            if room_labels_saved.get(name): label = room_labels_saved[name]
            dims = list(dims) + [0]*(4-len(dims))
            insert_entry_values(room_entries[name][:4], dims)
            room_entries[name][4].insert(0, label)

def submit_data(event=None):
    try:
        if not entry_width.get() or not entry_height.get():
            messagebox.showerror("Input Error", "Outer grid dimensions must be specified")
            return
        outer_width, outer_height = int(entry_width.get()), int(entry_height.get())
        num_holes = int(entry_num_holes.get() or 0)
        holes = []
        for i in range(num_holes):
            if not all(hole_entries[i][j].get() for j in range(4)):
                continue
            try:
                holes.append(tuple(int(hole_entries[i][j].get()) for j in range(4)))
            except ValueError:
                messagebox.showerror("Input Error", f"Invalid hole #{i+1} dimensions")
                return
        rooms = {}
        for name in room_names:
            entries = room_entries[name]
            if not entries[0].get() or not entries[1].get() or entries[0].get() == "0" or entries[1].get() == "0":
                continue
            try:
                min_width, min_height = int(entries[0].get()), int(entries[1].get())
                max_width = int(entries[2].get() or outer_width)
                max_height = int(entries[3].get() or outer_height)
                label = entries[4].get() or name
                rooms[name] = (min_width, min_height, max_width, max_height)
            except ValueError:
                messagebox.showerror("Input Error", f"Invalid dimensions for room {name}")
                return
        edges_raw = text_edges.get("1.0", "end").strip()
        edges_list = [
            tuple(line.split())
            for line in edges_raw.splitlines()
            if len(line.split()) == 2 and all(x in room_names for x in line.split())
        ]
        user_inputs.update({
            "outer_width": outer_width,
            "outer_height": outer_height,
            "holes": holes,
            "rooms": rooms,
            "edges": edges_list,
            "edges_text": edges_raw,
            "room_labels": {name: room_entries[name][4].get() or name for name in room_names}
        })
        save_inputs()
        generate_layout()
    except Exception as e:
        messagebox.showerror("Input Error", str(e))

def generate_layout():
    global room_placements, actual_edges_satisfied
    try:
        import GN_assignment
        GN_assignment.rooms = user_inputs["rooms"]
        GN_assignment.edges = user_inputs["edges"]
        GN_assignment.outer_width = user_inputs["outer_width"]
        GN_assignment.outer_height = user_inputs["outer_height"]
        GN_assignment.holes = user_inputs["holes"]
        initial_layout, used_edges = find_valid_solution(
            user_inputs["rooms"], user_inputs["edges"],
            user_inputs["outer_width"], user_inputs["outer_height"], user_inputs["holes"]
        )
        if initial_layout is None:
            messagebox.showerror("Algorithm Error", "No valid layout found by the algorithm")
            return
        stretched_rectangles = compute_stretch(
            initial_layout, user_inputs["rooms"], used_edges,
            user_inputs["outer_width"], user_inputs["outer_height"], user_inputs["holes"]
        )
        room_placements = {
            name: {"pos": (x, y), "size": (w, h), "label": user_inputs["room_labels"].get(name, name)}
            for name, (x, y, w, h) in stretched_rectangles.items()
        }
        actual_edges_satisfied = used_edges
        draw_layout()
    except Exception as e:
        messagebox.showerror("Algorithm Error", f"Error running layout algorithm: {str(e)}")

def draw_rectangle(canvas, x1, y1, x2, y2, fill, outline, width):
    canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=width)

def draw_layout():
    layout_canvas.delete("all")
    try:
        width, height = user_inputs["outer_width"], user_inputs["outer_height"]
        canvas_width, canvas_height = layout_canvas.winfo_width(), layout_canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            layout_canvas.after(100, draw_layout)
            return
        scale = min(canvas_width / width, canvas_height / height) * 0.85
        offset_x = (canvas_width - width * scale) / 2
        offset_y = (canvas_height - height * scale) / 2
        draw_rectangle(layout_canvas, offset_x, offset_y, offset_x + width * scale, offset_y + height * scale, "", FG_COLOR, 2)
        draw_holes(offset_x, offset_y, scale, height)
        draw_adjacency_lines(offset_x, offset_y, scale, height)
        draw_unsatisfied_adjacency_lines(offset_x, offset_y, scale, height)
        for room_id, room_data in room_placements.items():
            x, y = room_data["pos"]
            w, h = room_data["size"]
            label = room_data["label"]
            user_w, user_h = user_inputs["rooms"][room_id][:2]
            x1 = offset_x + x * scale
            y1 = offset_y + (height - y - h) * scale
            x2, y2 = x1 + w * scale, y1 + h * scale
            draw_rectangle(layout_canvas, x1, y1, x2, y2, ROOM_COLORS.get(room_id, "#CCCCCC"), "black", 1)
            center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
            layout_canvas.create_text(center_x, center_y - 15, text=label, fill="black", font=("Arial", 9, "bold"), anchor="center")
            layout_canvas.create_text(center_x, center_y, text=f"{w}x{h}", fill="black", font=("Arial", 8), anchor="center")
            layout_canvas.create_text(center_x, center_y + 15, text=f"(from {user_w}x{user_h})", fill="black", font=("Arial", 7), anchor="center")
    except Exception as e:
        print(f"Error drawing layout: {e}")

def draw_holes(offset_x, offset_y, scale, grid_height):
    for hole in user_inputs.get("holes", []):
        x, y, w, h = hole
        x1 = offset_x + x * scale
        y1 = offset_y + (grid_height - y - h) * scale
        x2, y2 = x1 + w * scale, y1 + h * scale
        draw_rectangle(layout_canvas, x1, y1, x2, y2, "white", "gray", 1)

def draw_lines(edges, color, width, dash=None):
    for edge in edges:
        room1, room2 = edge
        if room1 in room_placements and room2 in room_placements:
            r1, r2 = room_placements[room1], room_placements[room2]
            r1_x = r1["pos"][0] + r1["size"][0] / 2
            r1_y = r1["pos"][1] + r1["size"][1] / 2
            r2_x = r2["pos"][0] + r2["size"][0] / 2
            r2_y = r2["pos"][1] + r2["size"][1] / 2
            x1 = offset_x + r1_x * scale
            y1 = offset_y + (grid_height - r1_y) * scale
            x2 = offset_x + r2_x * scale
            y2 = offset_y + (grid_height - r2_y) * scale
            layout_canvas.create_line(x1, y1, x2, y2, fill=color, width=width, dash=dash)

def draw_adjacency_lines(offset_x, offset_y, scale, grid_height):
    draw_lines(actual_edges_satisfied, "green", 4)

def draw_unsatisfied_adjacency_lines(offset_x, offset_y, scale, grid_height):
    all_edges = set(user_inputs.get("edges", []))
    unsatisfied_edges = all_edges - set(actual_edges_satisfied)
    draw_lines(unsatisfied_edges, "red", 3, dash=(8, 4))

def on_hole_entry_change(*args):
    layout_canvas.after(50, draw_preview)

def draw_preview():
    if not entry_width.get() or not entry_height.get(): return
    try:
        width, height = int(entry_width.get()), int(entry_height.get())
        if not room_placements:
            layout_canvas.delete("all")
            canvas_width, canvas_height = layout_canvas.winfo_width(), layout_canvas.winfo_height()
            if canvas_width <= 1 or canvas_height <= 1: return
            scale = min(canvas_width / width, canvas_height / height) * 0.85
            offset_x = (canvas_width - width * scale) / 2
            offset_y = (canvas_height - height * scale) / 2
            draw_rectangle(layout_canvas, offset_x, offset_y, offset_x + width * scale, offset_y + height * scale, "", FG_COLOR, 2)
            for hole_entry_set in hole_entries:
                try:
                    if all(entry.get() for entry in hole_entry_set):
                        x, y, w, h = (int(entry.get()) for entry in hole_entry_set)
                        x1 = offset_x + x * scale
                        y1 = offset_y + (height - y - h) * scale
                        x2, y2 = x1 + w * scale, y1 + h * scale
                        draw_rectangle(layout_canvas, x1, y1, x2, y2, "#f9f8f8", "#7a7a7a", 1)
                except (ValueError, IndexError):
                    continue
    except ValueError:
        pass

def generate_hole_fields():
    for widgets in hole_frame.winfo_children():
        widgets.destroy()
    try:
        num = int(entry_num_holes.get() or 0)
        global hole_entries
        hole_entries = []
        for i in range(num):
            label = tk.Label(hole_frame, text=f"Hole #{i+1} (x y w h):", bg=BG_COLOR, fg=FG_COLOR)
            label.grid(row=i, column=0, padx=5, pady=3, sticky="e")
            entries = [tk.Entry(hole_frame, width=5, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR) for _ in range(4)]
            for j, entry in enumerate(entries):
                entry.bind('<KeyRelease>', on_hole_entry_change)
                entry.grid(row=i, column=j+1, padx=2)
            hole_entries.append(entries)
        draw_preview()
    except ValueError:
        pass

# GUI setup
root = tk.Tk()
root.title("Room Layout Planner - Real Algorithm")
root.geometry("1400x800")
root.minsize(1200, 700)
root.configure(bg=BG_COLOR)

main_container = tk.Frame(root, bg=BG_COLOR)
main_container.pack(fill="both", expand=True, padx=10, pady=10)
left_panel = tk.Frame(main_container, bg=BG_COLOR, width=400)
left_panel.pack(side="left", fill="y", padx=(0, 10))
left_panel.pack_propagate(False)
right_panel = tk.Frame(main_container, bg=BG_COLOR)
right_panel.pack(side="right", fill="both", expand=True)

form_frame = tk.Frame(left_panel, bg=BG_COLOR)
form_frame.pack(fill="both", expand=True)

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

holes_frame = tk.Frame(form_frame, bg=BG_COLOR)
holes_frame.pack(fill="x", pady=5)
tk.Label(holes_frame, text="Holes:", bg=BG_COLOR, fg=FG_COLOR).pack(side="left")
entry_num_holes = tk.Entry(holes_frame, width=5, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
entry_num_holes.pack(side="left", padx=5)
set_holes_btn = tk.Button(holes_frame, text="Set", command=generate_hole_fields, bg=BUTTON_BG, fg=FG_COLOR, activebackground=BUTTON_ACTIVE)
set_holes_btn.pack(side="left", padx=5)
hole_frame = tk.Frame(form_frame, bg=BG_COLOR)
hole_frame.pack(fill="x", pady=5)

tk.Label(form_frame, text="Rooms (min_w min_h max_w max_h label):", font=("Arial", 10, "bold"), bg=BG_COLOR, fg=FG_COLOR).pack(pady=5)
room_frame = tk.Frame(form_frame, bg=BG_COLOR)
room_frame.pack(fill="x")
room_entries = {}
for name in room_names:
    frame = tk.Frame(room_frame, bg=BG_COLOR)
    frame.pack(fill="x", pady=2)
    tk.Label(frame, text=f"{name}:", bg=BG_COLOR, fg=FG_COLOR, width=2).pack(side="left")
    entries = [tk.Entry(frame, width=4, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR) for _ in range(4)]
    for entry in entries:
        entry.pack(side="left", padx=1)
    label_entry = tk.Entry(frame, width=12, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
    label_entry.pack(side="left", padx=2)
    room_entries[name] = (*entries, label_entry)

tk.Label(form_frame, text="Adjacency (A B):", font=("Arial", 10, "bold"), bg=BG_COLOR, fg=FG_COLOR).pack(pady=5)
text_edges = tk.Text(form_frame, height=8, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
text_edges.pack(fill="x", pady=5)

button_frame = tk.Frame(form_frame, bg=BG_COLOR)
button_frame.pack(fill="x", pady=10)
submit_btn = tk.Button(button_frame, text="Generate Layout", command=submit_data, bg=BUTTON_BG, fg=FG_COLOR, activebackground=BUTTON_ACTIVE)
submit_btn.pack(side="left", padx=5)
help_btn = tk.Button(button_frame, text="Help", command=show_instructions, bg=BUTTON_BG, fg=FG_COLOR, activebackground=BUTTON_ACTIVE)
help_btn.pack(side="left", padx=5)

tk.Label(right_panel, text="Floor Plan Layout", font=("Arial", 14, "bold"), bg=BG_COLOR, fg=FG_COLOR).pack(pady=5)
layout_canvas = tk.Canvas(right_panel, bg=CANVAS_BG, highlightthickness=1, highlightbackground=FG_COLOR)
layout_canvas.pack(fill="both", expand=True, padx=5, pady=5)

hole_entries = []
entry_width.focus_set()
load_inputs()
root.mainloop()
