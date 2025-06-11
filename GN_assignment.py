from z3 import Int, Solver, Or, And, sat
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import time
from itertools import combinations

# start_time = time.time()
# Define the rooms
rooms = {}
edges = []
outer_width = 0
outer_height = 0
holes = []

def does_intersect(r1, r2):
    """Check if two rectangles (x1, y1, x2, y2) intersect."""
    (x1, y1, x2, y2) = r1
    (a1, b1, a2, b2) = r2
    return not (x2 <= a1 or a2 <= x1 or y2 <= b1 or b2 <= y1)

def get_user_boundary():
    return outer_width, outer_height, holes, rooms, edges

def visualize_boundary(ax, outer_width, outer_height, holes):
    outer_rect = patches.Rectangle(
        (0, 0),
        outer_width,
        outer_height,
        linewidth=2,
        edgecolor="blue",
        facecolor="none",
        linestyle="-",
        alpha=0.7,
    )
    ax.add_patch(outer_rect)

    for i, (x, y, width, height) in enumerate(holes):
        hole_rect = patches.Rectangle(
            (x, y),
            width,
            height,
            linewidth=2,
            edgecolor="red",
            facecolor="red",
            alpha=0.3,
        )
        ax.add_patch(hole_rect)

def compute_stretch(initial_layout, rooms, edges, outer_width, outer_height, holes):
    """
    Iteratively expands all rooms simultaneously with priority given to expansions
    that increase contact with adjacent rooms.
    Returns a dictionary of stretched rectangles: {room_name: (x, y, width, height)}.
    """
    current_rects = {}
    for name, (init_x, init_y) in initial_layout.items():
        min_w, min_h, max_w, max_h = rooms[name]
        current_rects[name] = [init_x, init_y, min_w, min_h, max_w, max_h]


    all_room_names = list(rooms.keys())

    def get_forbidden(current_state, expanding_room=None):
        forbidden = []
        for name, rect in current_state.items():
            if name == expanding_room:
                continue
            forbidden.append((rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3]))
        for hx, hy, hw, hh in holes:
            forbidden.append((hx, hy, hx + hw, hy + hh))
        return forbidden

    def is_free(rect, forbidden_rects):
        cx, cy, cw, ch = rect
        if cx < 0 or cy < 0 or cx + cw > outer_width or cy + ch > outer_height:
            return False
        candidate_rect = (cx, cy, cx + cw, cy + ch)
        for forb in forbidden_rects:
            if does_intersect(candidate_rect, forb):
                return False
        return True

    def get_adjacent_rooms(room_name):
        adjacent = []
        for r1, r2 in edges:
            if r1 == room_name:
                adjacent.append(r2)
            elif r2 == room_name:
                adjacent.append(r1)
        return adjacent

    def does_increase_adjacency(r1_new, r1_old, r2_rect):
        """Check if r1_new has more overlap with r2_rect than r1_old."""
        x1_new, y1_new, w1_new, h1_new = r1_new[:4]
        x1_old, y1_old, w1_old, h1_old = r1_old[:4]
        

        def get_overlap(rect1, rect2):
            x_overlap = max(0, min(rect1[0] + rect1[2], rect2[0] + rect2[2]) - max(rect1[0], rect2[0]))
            y_overlap = max(0, min(rect1[1] + rect1[3], rect2[1] + rect2[3]) - max(rect1[1], rect2[1]))
            return x_overlap * y_overlap

        overlap_new = get_overlap((x1_new, y1_new, w1_new, h1_new), r2_rect)
        overlap_old = get_overlap((x1_old, y1_old, w1_old, h1_old), r2_rect)

        return overlap_new > overlap_old

    while True:
        expanded_any = False
        next_rects = current_rects.copy()

        for name in all_room_names:
            x, y, w, h, max_w, max_h = current_rects[name]
            forbidden = get_forbidden(current_rects, name)
            adjacent_rooms = get_adjacent_rooms(name)
            adjacent_rects = {adj: current_rects[adj] for adj in adjacent_rooms if adj in current_rects}

            # Try expanding in each direction in priority order
            possible_expansions = {}

            candidate_left = [x - 1, y, w + 1, h, max_w, max_h]
            if w + 1 <= max_w and is_free(candidate_left[:4], forbidden):
                if adjacent_rooms:
                    priority = sum(
                        does_increase_adjacency(candidate_left, [x, y, w, h], adjacent_rects.get(adj, [0, 0, 0, 0]))
                        for adj in adjacent_rooms
                    )
                else:
                    priority = 1
                possible_expansions["left"] = (candidate_left, priority)

            candidate_right = [x, y, w + 1, h, max_w, max_h]
            if w + 1 <= max_w and is_free(candidate_right[:4], forbidden):
                if adjacent_rooms:
                    priority = sum(
                        does_increase_adjacency(candidate_right, [x, y, w, h], adjacent_rects.get(adj, [0, 0, 0, 0]))
                        for adj in adjacent_rooms
                    )
                else:
                    priority = 1
                possible_expansions["right"] = (candidate_right, priority)

            candidate_down = [x, y - 1, w, h + 1, max_w, max_h]
            if h + 1 <= max_h and is_free(candidate_down[:4], forbidden):
                if adjacent_rooms:
                    priority = sum(
                        does_increase_adjacency(candidate_down, [x, y, w, h], adjacent_rects.get(adj, [0, 0, 0, 0]))
                        for adj in adjacent_rooms
                    )
                else:
                    priority = 1
                possible_expansions["down"] = (candidate_down, priority)

            candidate_up = [x, y, w, h + 1, max_w, max_h]
            if h + 1 <= max_h and is_free(candidate_up[:4], forbidden):
                if adjacent_rooms:
                    priority = sum(
                        does_increase_adjacency(candidate_up, [x, y, w, h], adjacent_rects.get(adj, [0, 0, 0, 0]))
                        for adj in adjacent_rooms
                    )
                else:
                    priority = 1
                possible_expansions["up"] = (candidate_up, priority)

            best_expansion = None
            max_priority = -1
            for direction, (candidate, priority) in possible_expansions.items():
                if priority > max_priority:
                    max_priority = priority
                    best_expansion = candidate
                elif priority == max_priority and best_expansion is None:
                    best_expansion = candidate # just pick the first in case of ties

            if best_expansion and max_priority >= 0:
                next_rects[name] = best_expansion
                expanded_any = True
            else:
                next_rects[name] = [x, y, w, h, max_w, max_h] # no expansion

        if not expanded_any:
            break  # no room could be expanded
        current_rects = next_rects

    return {name: (x, y, w, h) for name, (x, y, w, h, _, _) in current_rects.items()}



def find_valid_solution(rooms, edges, outer_width, outer_height, holes, max_removals=None):
    s = Solver()
    positions = {}
    for name in rooms:
        x_coordinate = Int(f"x_{name}")
        y_coordinate = Int(f"y_{name}")
        positions[name] = (x_coordinate, y_coordinate)

    # Basic constraints (always apply)
    for name, (x, y) in positions.items():
        s.add(x >= 0, y >= 0)
        min_w, min_h, _, _ = rooms[name]
        w, h = min_w, min_h
        s.add(x + w <= outer_width)
        s.add(y + h <= outer_height)
        for hole_x, hole_y, hole_width, hole_height in holes:
            s.add(
                Or(
                    x + w <= hole_x,
                    x >= hole_x + hole_width,
                    y + h <= hole_y,
                    y >= hole_y + hole_height,
                )
            )

    # Non-overlapping constraint (always apply)
    for name1, name2 in combinations(rooms.keys(), 2):
        x1, y1 = positions[name1]
        x2, y2 = positions[name2]
        min_w1, min_h1, _, _ = rooms[name1]
        min_w2, min_h2, _, _ = rooms[name2]
        w1, h1 = min_w1, min_h1
        w2, h2 = min_w2, min_h2


        s.add(
            Or(
                x1 + w1 <= x2,
                x2 + w2 <= x1,
                y1 + h1 <= y2,
                y2 + h2 <= y1,
            )
        )

    # Try with all adjacencies first
    adjacency_constraints = []
    for name1, name2 in edges:
        x1, y1 = positions[name1]
        x2, y2 = positions[name2]
        min_w1, min_h1, _, _ = rooms[name1]
        min_w2, min_h2, _, _ = rooms[name2]
        w1, h1 = min_w1, min_h1
        w2, h2 = min_w2, min_h2


        left_of = And(
            x1 + w1 == x2,
            Or(
                And(y1 <= y2, y1 + h1 > y2),
                And(y2 <= y1, y2 + h2 > y1),
            ),
        )

        right_of = And(
            x2 + w2 == x1,
            Or(
                And(y1 <= y2, y1 + h1 > y2),
                And(y2 <= y1, y2 + h2 > y1),
            ),
        )

        above = And(
            y1 + h1 == y2,
            Or(
                And(x1 <= x2, x1 + w1 > x2),
                And(x2 <= x1, x2 + w2 > x1),
            ),
        )

        below = And(
            y2 + h2 == y1,
            Or(
                And(x1 <= x2, x1 + w1 > x2),
                And(x2 <= x1, x2 + w2 > x1),
            ),
        )

        adj_constraint = Or(left_of, right_of, above, below)
        adjacency_constraints.append((name1, name2, adj_constraint))
        s.add(adj_constraint)

    solution_start = time.time()
    if s.check() == sat:
        model = s.model()
        initial_layout = {
            name: (model[x].as_long(), model[y].as_long())
            for name, (x, y) in positions.items()
        }
        solution_end = time.time()
        print("Solution found with all adjacencies in", solution_end - solution_start, "seconds")
        return initial_layout, edges  # Return both layout and edges used

    # If no solution with all adjacencies, try removing some
    print("No solution with all adjacencies, trying to remove some...")
    
    if max_removals is None:
        max_removals = len(edges)  # Try removing up to all adjacencies if needed
    
    for num_to_remove in range(1, max_removals + 1):
        print(f"Trying to remove {num_to_remove} adjacency constraints...")
        
        # Try all combinations of removing 'num_to_remove' edges
        for edges_to_remove in combinations(edges, num_to_remove):
            s = Solver()
            
            # Re-add basic constraints
            for name, (x, y) in positions.items():
                s.add(x >= 0, y >= 0)
                min_w, min_h, _, _ = rooms[name]
                w, h = min_w, min_h
                s.add(x + w <= outer_width)
                s.add(y + h <= outer_height)
                for hole_x, hole_y, hole_width, hole_height in holes:
                    s.add(
                        Or(
                            x + w <= hole_x,
                            x >= hole_x + hole_width,
                            y + h <= hole_y,
                            y >= hole_y + hole_height,
                        )
                    )

            # Re-add non-overlapping constraints
            for name1, name2 in combinations(rooms.keys(), 2):
                x1, y1 = positions[name1]
                x2, y2 = positions[name2]
                min_w1, min_h1, _, _ = rooms[name1]
                min_w2, min_h2, _, _ = rooms[name2]
                w1, h1 = min_w1, min_h1
                w2, h2 = min_w2, min_h2


                s.add(
                    Or(
                        x1 + w1 <= x2,
                        x2 + w2 <= x1,
                        y1 + h1 <= y2,
                        y2 + h2 <= y1,
                    )
                )

            # Add adjacency constraints except for the ones we're removing
            remaining_edges = [edge for edge in edges if edge not in edges_to_remove]
            for name1, name2 in remaining_edges:
                x1, y1 = positions[name1]
                x2, y2 = positions[name2]
                min_w1, min_h1, _, _ = rooms[name1]
                min_w2, min_h2, _, _ = rooms[name2]
                w1, h1 = min_w1, min_h1
                w2, h2 = min_w2, min_h2


                left_of = And(
                    x1 + w1 == x2,
                    Or(
                        And(y1 <= y2, y1 + h1 > y2),
                        And(y2 <= y1, y2 + h2 > y1),
                    ),
                )

                right_of = And(
                    x2 + w2 == x1,
                    Or(
                        And(y1 <= y2, y1 + h1 > y2),
                        And(y2 <= y1, y2 + h2 > y1),
                    ),
                )

                above = And(
                    y1 + h1 == y2,
                    Or(
                        And(x1 <= x2, x1 + w1 > x2),
                        And(x2 <= x1, x2 + w2 > x1),
                    ),
                )

                below = And(
                    y2 + h2 == y1,
                    Or(
                        And(x1 <= x2, x1 + w1 > x2),
                        And(x2 <= x1, x2 + w2 > x1),
                    ),
                )

                s.add(Or(left_of, right_of, above, below))

            if s.check() == sat:
                model = s.model()
                initial_layout = {
                    name: (model[x].as_long(), model[y].as_long())
                    for name, (x, y) in positions.items()
                }
                solution_end = time.time()
                print(f"Solution found by removing {num_to_remove} adjacencies in", 
                      solution_end - solution_start, "seconds")
                print("Removed adjacencies:", edges_to_remove)
                return initial_layout, remaining_edges

    # If we get here, no solution was found even after removing all possible adjacencies
    print("No valid layout found even after removing all adjacency constraints")
    return None, None

def main():
    global rooms, edges
    outer_width, outer_height, holes, rooms_local, edges_local = get_user_boundary()
    rooms = rooms_local
    edges = edges_local

    initial_layout, used_edges = find_valid_solution(rooms, edges, outer_width, outer_height, holes)
    
    if initial_layout is None:
        print("No valid layout found.")
        return

    stretched_rectangles = compute_stretch(
        initial_layout, rooms, used_edges, outer_width, outer_height, holes
    )

    fig, ax = plt.subplots(figsize=(10, 8))

    colors = [
        "lightblue", "lightgreen", "lightcoral", "lightyellow", "lightpink",
        "lightgrey", "lightsalmon", "lightcyan", "lightseagreen", "lightsteelblue",
    ]

    visualize_boundary(ax, outer_width, outer_height, holes)

    for i, (name, (x, y, w, h)) in enumerate(stretched_rectangles.items()):
            rect = patches.Rectangle(
                (x, y),
                w,
                h,
                linewidth=2,
                edgecolor="black",
                facecolor=colors[i % len(colors)],
            )
            ax.add_patch(rect)
            # # Label at the center of the initial position
            # # for some reason labelling at current midpt doesn't work???
            # initial_x, initial_y = initial_layout[name]
            # initial_w, initial_h = rooms[name]
            # label_x = initial_x + initial_w / 2
            # label_y = initial_y + initial_h / 2

            # original_w, original_h = rooms[name]
            # dimension_text = f"{original_w}x{original_h}"
            # display_text = f"{name}\n{dimension_text}"

            # ax.text(
            #     label_x,
            #     label_y,
            #     display_text,
            #     ha="center",
            #     va="center",
            #     fontsize=10,
            #     fontweight="bold",
            # )
            
            # Calculate center of the STRETCHED rectangle
            stretched_center_x = x + w / 2
            stretched_center_y = y + h / 2

            # Create text using STRETCHED dimensions (w, h from loop)
            dimension_text = f"{w}x{h}"
            display_text = f"{name}\n{dimension_text}"

            ax.text(
                stretched_center_x, # Use stretched center X
                stretched_center_y, # Use stretched center Y
                display_text,       # Show name + stretched dimensions
                ha="center",
                va="center",
                fontsize=10,
                fontweight="bold",
            )

    ax.grid(True, linestyle="--", alpha=0.7)
    ax.set_aspect("equal")
    ax.set_xlim(-0.5, outer_width + 0.5)
    ax.set_ylim(-0.5, outer_height + 0.5)
    ax.set_title("Room Layout Solution")
    ax.set_xlabel("X-coordinate")
    ax.set_ylabel("Y-coordinate")

    for i in range(outer_width + 1):
        ax.text(i, -0.25, str(i), ha="center")
    for i in range(outer_height + 1):
        ax.text(-0.25, i, str(i), ha="center")

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()