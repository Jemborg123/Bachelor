import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Data.utils import AdjacencyList,savePointsDataToFile
from Data.BuildGraph import buildAdjacencyList, visualize_graph,mergePoints
from Data.Database_access.loadFromDb import fetch_points
from Data.merging_techniques.dbscan_merge import merge_points_simpleDbscan

from Data.merging_techniques.merge_types import MergeType

import matplotlib.pyplot as plt
from matplotlib.widgets import Button

import random


import os
import json

def _atomic_save(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    tmp = filepath + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, filepath)   # atomic swap; never leaves a partial file


def DBparameteranalysis(points):
    out_path = "Data/geoserver_layer_analysis/EmpiricalDBSCANParameterAnalysis.json"

    # Resume: pick up whatever was already computed
    graphs = {}
    if os.path.exists(out_path):
        with open(out_path, "r") as f:
            graphs = json.load(f)
        print(f"Resuming — {len(graphs)} passes already saved")

    for eps_i in range(1, 20, 1):
        eps = float(eps_i) / 2
        for min_samples in range(1, 3, 1):
            key = f"{eps},{min_samples}"
            if key in graphs:
                continue                     # already done, skip it
            merged = merge_points_simpleDbscan(points, eps, min_samples)
            merged = [[float(p[0]), float(p[1])] for p in merged]
            graphs[key] = merged
            _atomic_save(graphs, out_path)   # <-- save after every pass

    return graphs

def reviewMergedGraphs(
    analysis_path="Data/geoserver_layer_analysis/EmpiricalDBSCANParameterAnalysis.json",
    best_path="Data/geoserver_layer_analysis/BestDBSCANParameters.json",
    raw_points=None,
):
    # Load the saved parameter sweep: {"eps,min_samples": [[x, y], ...], ...}
    with open(analysis_path, "r") as f:
        graphs = json.load(f)

    # Unprocessed points (fetch if not handed in)
    if raw_points is None:
        raw_points, _ = fetch_points()
    raw_points = [tuple(p) for p in raw_points]
    raw_xs = [p[0] for p in raw_points]
    raw_ys = [p[1] for p in raw_points]

    # Resume an earlier review session if one exists
    best = {}
    if os.path.exists(best_path):
        with open(best_path, "r") as f:
            best = json.load(f)
        print(f"Resuming — {len(best)} already marked as best")

    def _save_best():
        os.makedirs(os.path.dirname(best_path), exist_ok=True)
        tmp = best_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(best, f)
        os.replace(tmp, best_path)          # atomic, never leaves a partial file

    keys = list(graphs.keys())
    total = len(keys)

    for idx, key in enumerate(keys):
        merged = graphs[key]
        merged_xs = [p[0] for p in merged]
        merged_ys = [p[1] for p in merged]

        eps_str, ms_str = key.split(",")
        label = f"eps={float(eps_str):.1f}, min_samples={int(ms_str)}"
        already = key in best

        state = {"action": "skip"}           # default if the window is just closed

        fig, (ax_raw, ax_merged) = plt.subplots(
            1, 2, figsize=(14, 7), sharex=True, sharey=True
        )
        fig.suptitle(f"[{idx + 1}/{total}]  {label}"
                     f"{'   (currently KEPT)' if already else ''}")

        ax_raw.scatter(raw_xs, raw_ys, s=0.5, c="gray",
                       label=f"raw  ({len(raw_points)} pts)")
        ax_raw.set_title("Unprocessed points")
        ax_raw.set_aspect("equal")
        ax_raw.legend(loc="upper right")

        ax_merged.scatter(merged_xs, merged_ys, s=0.5, c="blue",
                          label=f"{label}  ({len(merged)} pts)")
        ax_merged.set_title("Merged points")
        ax_merged.set_aspect("equal")
        ax_merged.legend(loc="upper right")     # legend carries the (eps, min) key

        plt.subplots_adjust(bottom=0.15)

        def _keep(_=None): state["action"] = "keep"; plt.close(fig)
        def _skip(_=None): state["action"] = "skip"; plt.close(fig)
        def _stop(_=None): state["action"] = "stop"; plt.close(fig)

        # Buttons
        b_keep = Button(fig.add_axes([0.30, 0.02, 0.12, 0.06]), "Keep")
        b_skip = Button(fig.add_axes([0.45, 0.02, 0.12, 0.06]), "Skip")
        b_stop = Button(fig.add_axes([0.60, 0.02, 0.14, 0.06]), "Stop + Save")
        b_keep.on_clicked(_keep)
        b_skip.on_clicked(_skip)
        b_stop.on_clicked(_stop)

        # Keyboard shortcuts: k/Enter = keep, s/Space = skip, q/Esc = stop
        def _on_key(event):
            if event.key in ("k", "enter", "right"):   _keep()
            elif event.key in ("s", " ", "left"):      _skip()
            elif event.key in ("q", "escape"):         _stop()
        fig.canvas.mpl_connect("key_press_event", _on_key)

        plt.show()                            # blocks until this figure is closed

        if state["action"] == "keep":
            best[key] = merged                # store the chosen merge result
            _save_best()                      # save immediately, per pick
            print(f"Kept {label}  ({len(best)} total)")
        elif state["action"] == "stop":
            print("Stopping review.")
            break
        # "skip" falls through and moves to the next figure

    _save_best()
    print(f"Saved {len(best)} chosen parameter sets to {best_path}")
    return best
import os
import json
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.widgets import Button

def blindRegionTournament(
    best_path="Data/geoserver_layer_analysis/BestDBSCANParameters.json",
    votes_path="Data/geoserver_layer_analysis/RegionVotes.json",
    winner_path="Data/geoserver_layer_analysis/WinnerDBSCANParameters.json",
    raw_points=None,
    grid=4,                  # grid x grid zoom regions; 4 -> 16 regions
    zoom_regions=None,       # optional explicit [(xmin,xmax,ymin,ymax), ...]
):
    MERGED_SIZE = 0.5        # marker sizes — as tiny as matplotlib draws
    RAW_SIZE    = 0.3        # faint context layer

    with open(best_path, "r") as f:
        best = json.load(f)              # {"eps,min": [[x,y],...], ...}  (the 4 kept)
    cand_keys = list(best.keys())
    if len(cand_keys) < 2:
        print("Need at least 2 candidates to compare.")
        return None

    if raw_points is None:
        raw_points, _ = fetch_points()
    raw_points = [tuple(p) for p in raw_points]
    raw_xs = [p[0] for p in raw_points]
    raw_ys = [p[1] for p in raw_points]

    # Build >=16 zoom regions as a grid over the bounding box
    if zoom_regions is None:
        min_x, max_x = min(raw_xs), max(raw_xs)
        min_y, max_y = min(raw_ys), max(raw_ys)
        xs_edges = [min_x + (max_x - min_x) * i / grid for i in range(grid + 1)]
        ys_edges = [min_y + (max_y - min_y) * j / grid for j in range(grid + 1)]
        zoom_regions = []
        for j in range(grid):
            for i in range(grid):
                zoom_regions.append(
                    (xs_edges[i], xs_edges[i + 1], ys_edges[j], ys_edges[j + 1])
                )

    # Pre-split each candidate's points per region (clip once, reuse)
    def _clip(pts, box):
        x0, x1, y0, y1 = box
        return [(p[0], p[1]) for p in pts if x0 <= p[0] <= x1 and y0 <= p[1] <= y1]

    raw_by_region = [_clip(raw_points, b) for b in zoom_regions]
    cand_by_region = {k: [_clip(best[k], b) for b in zoom_regions] for k in cand_keys}

    # Resume: votes_path maps region index -> winning REAL key (kept hidden)
    votes = {}
    if os.path.exists(votes_path):
        with open(votes_path, "r") as f:
            votes = json.load(f)
        print(f"Resuming — {len(votes)} regions already voted")

    def _atomic(data, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, path)

    n_regions = len(zoom_regions)
    letters = ["A", "B", "C", "D", "E", "F"][:len(cand_keys)]

    for r_idx, box in enumerate(zoom_regions):
        if str(r_idx) in votes:           # already decided, skip on resume
            continue

        # Blind: shuffle which candidate sits under which letter, per region
        shuffled = cand_keys[:]
        random.shuffle(shuffled)
        label_to_key = dict(zip(letters, shuffled))

        x0, x1, y0, y1 = box
        ncols = len(cand_keys)
        fig, axes = plt.subplots(1, ncols, figsize=(4.5 * ncols, 5),
                                 sharex=True, sharey=True)
        if ncols == 1:
            axes = [axes]
        fig.suptitle(f"Region {r_idx + 1}/{n_regions} — pick the best "
                     f"(press {'/'.join(L.lower() for L in letters)}; s=skip, q=stop)")

        rxs = [p[0] for p in raw_by_region[r_idx]]
        rys = [p[1] for p in raw_by_region[r_idx]]
        for ax, letter in zip(axes, letters):
            key = label_to_key[letter]
            pts = cand_by_region[key][r_idx]
            mxs = [p[0] for p in pts]
            mys = [p[1] for p in pts]
            ax.scatter(rxs, rys, s=RAW_SIZE, c="lightgray",
                       linewidths=0, rasterized=True)
            ax.scatter(mxs, mys, s=MERGED_SIZE, c="blue",
                       linewidths=0, rasterized=True)
            ax.set_xlim(x0, x1)
            ax.set_ylim(y0, y1)
            ax.set_aspect("equal")
            ax.set_title(letter)          # blind label only — no eps/min shown

        state = {"action": "skip", "letter": None}

        def _pick(letter):
            state["action"] = "pick"; state["letter"] = letter; plt.close(fig)
        def _on_key(event):
            if not event.key:
                return
            k = event.key.lower()
            if k in [L.lower() for L in letters]:
                _pick(k.upper())
            elif k in ("s", " "):
                state["action"] = "skip"; plt.close(fig)
            elif k in ("q", "escape"):
                state["action"] = "stop"; plt.close(fig)
        fig.canvas.mpl_connect("key_press_event", _on_key)

        # Buttons, in case keys aren't convenient
        plt.subplots_adjust(bottom=0.15)
        btns = []
        for bi, letter in enumerate(letters):
            bax = fig.add_axes([0.10 + bi * 0.10, 0.03, 0.08, 0.06])
            b = Button(bax, letter)
            b.on_clicked((lambda L: (lambda _=None: _pick(L)))(letter))
            btns.append(b)
        b_stop = Button(fig.add_axes([0.82, 0.03, 0.12, 0.06]), "Stop+Save")
        b_stop.on_clicked(lambda _=None: (state.update(action="stop"), plt.close(fig)))

        plt.show()

        if state["action"] == "pick":
            votes[str(r_idx)] = label_to_key[state["letter"]]   # store REAL key
            _atomic(votes, votes_path)
            print(f"Region {r_idx + 1}: recorded (you picked {state['letter']})")
        elif state["action"] == "stop":
            print("Stopping.")
            break
        # skip -> no vote for this region

    _atomic(votes, votes_path)

    # ---- Reveal only now ----
    if not votes:
        print("No votes recorded.")
        return None

    tally = {k: 0 for k in cand_keys}
    for key in votes.values():
        tally[key] = tally.get(key, 0) + 1

    print("\n=== Results ===")
    for k, v in sorted(tally.items(), key=lambda kv: kv[1], reverse=True):
        eps_str, ms_str = k.split(",")
        print(f"  {v:3d} region wins   eps={float(eps_str):.1f}, "
              f"min_samples={int(ms_str)}")

    top = max(tally.values())
    winners = [k for k, v in tally.items() if v == top]
    if len(winners) > 1:
        print(f"\nTie at {top} wins: {winners} — taking the first.")
    winner_key = winners[0]
    _atomic({winner_key: best[winner_key]}, winner_path)
    eps_str, ms_str = winner_key.split(",")
    print(f"\nOverall winner ({top}/{len(votes)} regions): "
          f"eps={float(eps_str):.1f}, min_samples={int(ms_str)} "
          f"-> saved to {winner_path}")
    return winner_key


points,_ = fetch_points()
points = [tuple(p)for p in points]


#STAGE 1
# g = DBparameteranalysis(points)

# for _,merged_points in g.items():
#     merged_points = [tuple(p)for p in merged_points]
#     adj = AdjacencyList(merged_points)
#     visualize_graph(adj)

#STAGE 2
reviewMergedGraphs(raw_points=points)


#Stage 3
blindRegionTournament(raw_points=points)
