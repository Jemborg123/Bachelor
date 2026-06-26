"""
Comparative analysis of four shortest-path algorithms on a single graph.

Algorithms (baseline first):
    - Dijkstra                  (Dijkstra.dijk_s_to_t)
    - A* (Euclidean h)          (AStar.new_astar + Euclidean heuristic)
    - Bidirectional A*          (bidirectionals.bi_astar_new + Euclidean heuristic)
    - ALT (A* + landmarks)      (AStar.new_astar + landmark heuristic)

Experiment:
    * N random source/target pairs (default 100), shared by every algorithm.
    * Per query we record: time, vertices visited, edges relaxed, and the
      straight-line query distance (for the distance-bucket analysis).
    * Memory and a CPU-work proxy are measured once per algorithm.
    * Optional landmark sweep over {1,2,4,8,16,32} landmarks.

Outputs (in --outdir):
    * tables.tex   -- LaTeX tables filling the report skeletons
    * *_raw.csv    -- one row per (algorithm, query)
    * *_summary.csv
    * optional PNG visualisations of one query (visited / frontier / path)

Metrics & how they are obtained WITHOUT editing the algorithm files:
    The algorithms touch the graph only through nodes()/neighbors()/
    neighborCost()/getX()/getY(). `TracingGraph` wraps a real graph and counts
        - every node it is asked to expand        -> "vertices visited"/frontier
        - every neighborCost() call               -> "edges relaxed"
    (the inner relaxation loop calls neighborCost exactly once per edge).
    Vertices-visited also cross-checks the algorithm's own returned count.

    "CPU cycles": Python has no portable hardware cycle counter. We report the
    deterministic cProfile primitive-call count as a work proxy (and CPU time
    in the CSV). See the note printed at the end.

Run from the PROJECT ROOT, e.g.:
    python Algorithms/Comparison.py --graph adj --queries 100 --landmark-sweep
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import io
import csv
import math
import time
import random
import cProfile
import pstats
import tracemalloc
import traceback
from collections import namedtuple, defaultdict

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    HAVE_MPL = True
except Exception:
    HAVE_MPL = False

# path_to_target is recursive (one frame per node on the path); give it room.
sys.setrecursionlimit(1_000_000)

INF = float("inf")

# name + run(graph, s, t) -> (cost, path, vertices_visited)
AlgoSpec = namedtuple("AlgoSpec", ["name", "run"])

# Distance buckets for the by-distance analysis (metres). (lo, hi, label)
DEFAULT_BUCKETS = [
    (100, 500, "100--500"),
    (500, 1000, "500--1000"),
    (1000, 1500, "1000--1500"),
    (1500, 2000, "1500--2000"),
    (2000, INF, "$>$2000"),
]
LANDMARK_COUNTS = [1,2,4,8,16,32,64,128]


# =============================================================================
# Non-invasive instrumentation
# =============================================================================
class TracingGraph:
    """Counts expanded vertices and edge relaxations; delegates everything else."""

    def __init__(self, graph):
        self._g = graph
        self.expanded = set()
        self.discovered = set()
        self.relaxations = 0

    def neighbors(self, node):
        self.expanded.add(node)
        nbrs = list(self._g.neighbors(node))
        self.discovered.update(nbrs)
        return nbrs

    def neighborCost(self, node, neighbor):
        self.relaxations += 1            # one call == one edge relaxation
        return self._g.neighborCost(node, neighbor)

    def nodes(self):
        return self._g.nodes()           # init only -- not a discovery

    def __getattr__(self, name):
        return getattr(self._g, name)


# =============================================================================
# Single-run measurement primitives  (call := lambda g: spec.run(g, s, t))
# =============================================================================
def trace_run(call, graph):
    tg = TracingGraph(graph)
    cost, path, nvisited = call(tg)
    expanded = set(tg.expanded)
    frontier = set(tg.discovered) - expanded
    if not isinstance(nvisited, int):
        try:
            nvisited = len(nvisited)
        except TypeError:
            nvisited = len(expanded)
    found = (isinstance(cost, (int, float)) and cost != INF
             and isinstance(path, list) and len(path) > 0)
    return {
        "found": found,
        "cost": cost if isinstance(cost, (int, float)) else INF,
        "path": path if found else [],
        "vertices": nvisited,
        "edges_relaxed": tg.relaxations,
        "expanded": expanded,
        "frontier": frontier,
    }


def time_run(call, graph, repeats=3):
    best = INF
    for _ in range(repeats):
        t0 = time.perf_counter()
        call(graph)
        best = min(best, time.perf_counter() - t0)
    return best  # seconds


def cpu_time_run(call, graph, repeats=3):
    best = INF
    for _ in range(repeats):
        c0 = time.process_time()
        call(graph)
        best = min(best, time.process_time() - c0)
    return best


def mem_run(call, graph):
    tracemalloc.start()
    try:
        call(graph)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return peak  # bytes


def profile_calls(call, graph):
    pr = cProfile.Profile()
    pr.enable()
    call(graph)
    pr.disable()
    ps = pstats.Stats(pr, stream=io.StringIO())
    return getattr(ps, "prim_calls", 0)


def measure_block(fn):
    tracemalloc.start()
    w0, c0 = time.perf_counter(), time.process_time()
    out = fn()
    wall, cpu = time.perf_counter() - w0, time.process_time() - c0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return out, {"wall": wall, "cpu": cpu, "peak_bytes": peak}


# =============================================================================
# Benchmark over many queries
# =============================================================================
def euclid(graph, a, b):
    return math.hypot(graph.getX(a) - graph.getX(b), graph.getY(a) - graph.getY(b))


def run_benchmark(graph, algos, queries, repeats=3, progress=True):
    """Returns (records, per_algo) where records is one dict per (algo, query)."""
    qdist = [euclid(graph, s, t) for (s, t) in queries]
    records = []
    per_algo = {}

    for spec in algos:
        if progress:
            print(f"  · {spec.name}: {len(queries)} queries")
        first_found = None
        for qi, (s, t) in enumerate(queries):
            call = (lambda g, s=s, t=t, spec=spec: spec.run(g, s, t))
            tr = trace_run(call, graph)
            rec = {
                "algo": spec.name, "qi": qi, "distance": qdist[qi],
                "found": tr["found"], "cost": tr["cost"],
                "vertices": tr["vertices"], "edges_relaxed": tr["edges_relaxed"],
                "time_ms": INF,
            }
            if tr["found"]:
                rec["time_ms"] = time_run(call, graph, repeats) * 1000.0
                if first_found is None:
                    first_found = (s, t)
            records.append(rec)

        # Memory + CPU proxy: once per algorithm (query-independent in practice).
        s, t = first_found if first_found else queries[0]
        call = (lambda g, s=s, t=t, spec=spec: spec.run(g, s, t))
        per_algo[spec.name] = {
            "memory_bytes": mem_run(call, graph),
            "cpu_ms": cpu_time_run(call, graph, repeats) * 1000.0,
            "prim_calls": profile_calls(call, graph),
        }
    return records, per_algo, qdist


def _mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float)) and x != INF]
    return sum(xs) / len(xs) if xs else float("nan")


def summarize(records, per_algo, algo_order):
    summary = {}
    for name in algo_order:
        rs = [r for r in records if r["algo"] == name and r["found"]]
        summary[name] = {
            "time_ms": _mean([r["time_ms"] for r in rs]),
            "vertices": _mean([r["vertices"] for r in rs]),
            "edges_relaxed": _mean([r["edges_relaxed"] for r in rs]),
            "memory_kb": per_algo[name]["memory_bytes"] / 1024.0,
            "cpu_ms": per_algo[name]["cpu_ms"],
            "prim_calls": per_algo[name]["prim_calls"],
            "n_found": len(rs),
        }
    return summary


def bucket_analysis(records, algo_order, buckets):
    """mean vertices visited per (bucket, algorithm)."""
    table = {lab: {} for (_, _, lab) in buckets}
    for (lo, hi, lab) in buckets:
        for name in algo_order:
            vals = [r["vertices"] for r in records
                    if r["algo"] == name and r["found"]
                    and lo <= r["distance"] < hi]
            table[lab][name] = _mean(vals) if vals else float("nan")
    return table


# =============================================================================
# LaTeX emission (fills the report's table skeletons)
# =============================================================================
def _f(x, d=2):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "--"
    return f"{x:.{d}f}"


def latex_summary(summary, algo_order, n_queries):
    lines = [
        r"\begin{table}[h]", r"\centering",
        rf"\caption{{Performance summary of all four algorithms. Values are means across {n_queries} queries.}}",
        r"\label{tab:algorithm-summary}",
        r"\begin{tabular}{|l|r|r|r|r|}", r"\hline",
        r"\textbf{Algorithm} & \textbf{Time (ms)} & \textbf{Vertices Visited} & "
        r"\textbf{Edges Relaxed} & \textbf{Memory (KB)} \\", r"\hline",
    ]
    for name in algo_order:
        s = summary[name]
        lines.append(f"{name} & {_f(s['time_ms'],3)} & {_f(s['vertices'],1)} & "
                     f"{_f(s['edges_relaxed'],1)} & {_f(s['memory_kb'],1)} \\\\")
    lines += [r"\hline", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines)


def latex_relative(summary, algo_order):
    base = summary[algo_order[0]]
    lines = [
        r"\begin{table}[h]", r"\centering",
        r"\caption{Relative performance compared to Dijkstra (Dijkstra = 1.00). Lower is better.}",
        r"\label{tab:algorithm-relative}",
        r"\begin{tabular}{|l|r|r|r|r|}", r"\hline",
        r"\textbf{Algorithm} & \textbf{Time} & \textbf{Vertices Visited} & "
        r"\textbf{Edges Relaxed} & \textbf{Memory} \\", r"\hline",
    ]

    def ratio(a, b):
        return a / b if (b and not math.isnan(a) and not math.isnan(b)) else float("nan")

    for name in algo_order:
        s = summary[name]
        lines.append(
            f"{name} & {_f(ratio(s['time_ms'], base['time_ms']))} & "
            f"{_f(ratio(s['vertices'], base['vertices']))} & "
            f"{_f(ratio(s['edges_relaxed'], base['edges_relaxed']))} & "
            f"{_f(ratio(s['memory_kb'], base['memory_kb']))} \\\\")
    lines += [r"\hline", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines)


def latex_buckets(table, algo_order, buckets):
    lines = [
        r"\begin{table}[h]", r"\centering",
        r"\caption{Nodes visited by distance bucket. Values are means.}",
        r"\label{tab:query-distance-analysis}",
        r"\begin{tabular}{|l|r|r|r|r|}", r"\hline",
        r"\textbf{Distance (m)} & \textbf{Dijkstra} & \textbf{A*} & "
        r"\textbf{Bidirectional A*} & \textbf{ALT} \\", r"\hline",
    ]
    for (_, _, lab) in buckets:
        row = table[lab]
        cells = " & ".join(_f(row[name], 1) for name in algo_order)
        lines.append(f"{lab} & {cells} \\\\")
    lines += [r"\hline", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines)


def latex_landmark(rows, n_queries):
    lines = [
        r"\begin{table}[h]", r"\centering",
        rf"\caption{{ALT performance as a function of landmark count. Query-time "
        rf"values are means across {n_queries} queries; preprocessing time and "
        rf"memory are the one-off cost of building the landmark distance tables.}}",
        r"\label{tab:landmark-sensitivity}",
        r"\begin{tabular}{|r|r|r|r|r|r|r|}", r"\hline",
        r"\textbf{Landmarks} & \textbf{Prep Time (s)} & \textbf{Prep Memory (KB)} & "
        r"\textbf{Time (ms)} & \textbf{Nodes Visited} & "
        r"\textbf{Edges Relaxed} & \textbf{Memory (KB)} \\", r"\hline",
    ]
    for r in rows:
        lines.append(f"{r['landmarks']} & {_f(r['prep_wall_s'],2)} & "
                     f"{_f(r['prep_mem_kb'],1)} & {_f(r['time_ms'],3)} & "
                     f"{_f(r['vertices'],1)} & "
                     f"{_f(r['edges_relaxed'],1)} & {_f(r['memory_kb'],1)} \\\\")
    lines += [r"\hline", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines)


# =============================================================================
# CSV output
# =============================================================================
def write_raw_csv(records, path):
    fields = ["algo", "qi", "distance", "found", "cost",
              "vertices", "edges_relaxed", "time_ms"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            w.writerow({k: r[k] for k in fields})


def write_summary_csv(summary, algo_order, path):
    fields = ["algo", "n_found", "time_ms", "vertices", "edges_relaxed",
              "memory_kb", "cpu_ms", "prim_calls"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for name in algo_order:
            s = summary[name]
            w.writerow({"algo": name, "n_found": s["n_found"],
                        "time_ms": round(s["time_ms"], 4),
                        "vertices": round(s["vertices"], 2),
                        "edges_relaxed": round(s["edges_relaxed"], 2),
                        "memory_kb": round(s["memory_kb"], 2),
                        "cpu_ms": round(s["cpu_ms"], 4),
                        "prim_calls": s["prim_calls"]})


def print_console_summary(summary, algo_order, n_queries):
    print("\n" + "=" * 96)
    print(f"SUMMARY (means over {n_queries} queries)")
    print("=" * 96)
    print(f"{'Algorithm':<20}{'Time ms':>10}{'Vertices':>11}{'Edges rlx':>12}"
          f"{'Mem KB':>10}{'CPU ms':>9}{'calls':>12}")
    print("-" * 96)
    for name in algo_order:
        s = summary[name]
        print(f"{name:<20}{_f(s['time_ms'],3):>10}{_f(s['vertices'],1):>11}"
              f"{_f(s['edges_relaxed'],1):>12}{_f(s['memory_kb'],1):>10}"
              f"{_f(s['cpu_ms'],3):>9}{s['prim_calls']:>12}")
    print("-" * 96)


# =============================================================================
# Visualisation of a single query (visited / frontier / path)
# =============================================================================
def build_positions(graph):
    return {n: (graph.getX(n), graph.getY(n)) for n in graph.nodes()}


def build_edge_segments(graph, positions):
    seen, segs = set(), []
    for n in graph.nodes():
        p1 = positions[n]
        for nb in graph.neighbors(n):
            if nb not in positions:
                continue
            key = frozenset((n, nb))
            if len(key) < 2 or key in seen:
                continue
            seen.add(key)
            segs.append((p1, positions[nb]))
    return segs


def _xy(positions, nodes):
    xs, ys = [], []
    for n in nodes:
        if n in positions:
            xs.append(positions[n][0]); ys.append(positions[n][1])
    return xs, ys


def draw_search(ax, positions, edge_segments, res, s, t, title, equal_aspect=True):
    ax.add_collection(LineCollection(edge_segments, colors="0.86",
                                     linewidths=0.4, zorder=1))
    fx, fy = _xy(positions, res["frontier"])
    ax.scatter(fx, fy, s=7, c="#f5a623", linewidths=0, zorder=2,
               label=f"frontier ({len(res['frontier'])})")
    ex, ey = _xy(positions, res["expanded"])
    ax.scatter(ex, ey, s=7, c="#2f6fd0", linewidths=0, zorder=3,
               label=f"visited ({len(res['expanded'])})")
    if res["found"] and len(res["path"]) > 1:
        px, py = _xy(positions, res["path"])
        ax.plot(px, py, c="#d0021b", lw=2.0, zorder=4, label="path")
    sx, sy = _xy(positions, [s]); tx, ty = _xy(positions, [t])
    ax.scatter(sx, sy, marker="*", s=220, c="#2ecc71", edgecolors="black",
               linewidths=0.6, zorder=5, label="source")
    ax.scatter(tx, ty, marker="*", s=220, c="#9b59b6", edgecolors="black",
               linewidths=0.6, zorder=5, label="target")
    ax.set_title(title, fontsize=10)
    if equal_aspect:
        ax.set_aspect("equal", adjustable="datalim")
    ax.axis("off")
    ax.legend(loc="upper right", fontsize=7, framealpha=0.85)


def _slug(name):
    return "".join(c if c.isalnum() else "_" for c in name).strip("_")


def visualize_query(graph, algos, s, t, outdir, gname, equal_aspect=True):
    if not HAVE_MPL:
        print("  (matplotlib unavailable -- skipping visualisation)")
        return []
    positions = build_positions(graph)
    edges = build_edge_segments(graph, positions)
    reslist = []
    for spec in algos:
        call = lambda g: spec.run(g, s, t)
        tr = trace_run(call, graph)
        tr["name"] = spec.name
        reslist.append(tr)

    out = []
    for tr in reslist:
        fig, ax = plt.subplots(figsize=(8, 8))
        title = (f"{tr['name']}\nvisited={len(tr['expanded'])}  "
                 f"frontier={len(tr['frontier'])}  cost={_f(tr['cost'],1)}")
        draw_search(ax, positions, edges, tr, s, t, title, equal_aspect)
        p = os.path.join(outdir, f"{gname}_{_slug(tr['name'])}.png")
        fig.savefig(p, dpi=130, bbox_inches="tight"); plt.close(fig); out.append(p)

    n = len(reslist); ncols = min(2, n); nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(8 * ncols, 7.5 * nrows),
                             squeeze=False)
    flat = axes.flatten()
    for ax, tr in zip(flat, reslist):
        title = (f"{tr['name']}\nvisited={len(tr['expanded'])}  "
                 f"frontier={len(tr['frontier'])}  cost={_f(tr['cost'],1)}")
        draw_search(ax, positions, edges, tr, s, t, title, equal_aspect)
    for ax in flat[n:]:
        ax.axis("off")
    fig.suptitle(f"Search comparison ({gname}) s={s} t={t}", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    p = os.path.join(outdir, f"{gname}_search_grid.png")
    fig.savefig(p, dpi=120, bbox_inches="tight"); plt.close(fig); out.append(p)
    return out


# =============================================================================
# Scenario construction (imports the real modules + data lazily)
# =============================================================================
def load_graph(which, adjacency_path, graph_file):
    """Returns (graph, modules, queries_fn, euclid_h_factory)."""
    from Algorithms import Dijkstra, AStar, ALT, bidirectionals
    mods = (Dijkstra, AStar, ALT, bidirectionals)

    if which == "adj":
        from Data.utils import load_adjacency_list
        adjacency_list, ok = load_adjacency_list(adjacency_path)
        if not ok:
            raise FileNotFoundError(f"could not load adjacency list: {adjacency_path}")
        graph = Dijkstra.adjGraph(adjacency_list)
        queries_fn = lambda n: Dijkstra.select_random_nodes_adj(adjacency_list, n)
        euclid_h = lambda: AStar.adj_euclidean
        return graph, mods, queries_fn, euclid_h
    else:
        import pickle
        with open(graph_file, "rb") as f:
            G = pickle.load(f)
        graph = Dijkstra.nxGraph(G)
        queries_fn = lambda n: Dijkstra.select_random_nodes_nx(G, n)
        euclid_h = lambda: (lambda p1, p2: AStar.nx_euclidean(p1, p2, G))
        return graph, mods, queries_fn, euclid_h


def _bbox(graph):
    nodes = list(graph.nodes())
    xs = [graph.getX(n) for n in nodes]
    ys = [graph.getY(n) for n in nodes]
    return min(xs), min(ys), max(xs), max(ys)


def _perimeter_points(graph, k):
    """k points spread evenly around the graph's bounding-box perimeter.

    Works for any k >= 1 (the project's new_select_landmarks divides by
    num_landmarks//4 and therefore breaks for k < 4)."""
    min_x, min_y, max_x, max_y = _bbox(graph)
    w, h = max_x - min_x, max_y - min_y
    perim = 2 * (w + h)
    if perim == 0 or k <= 0:
        return [(min_x, max_y)] * max(k, 1)

    def at(d):
        d %= perim
        if d <= w:               # top edge,    left -> right
            return (min_x + d, max_y)
        d -= w
        if d <= h:               # right edge,  top -> bottom
            return (max_x, max_y - d)
        d -= h
        if d <= w:               # bottom edge, right -> left
            return (max_x - d, min_y)
        d -= w
        return (min_x, min_y + d)  # left edge,  bottom -> top

    return [at(i * perim / k) for i in range(k)]


def _fallback_landmarks(graph, k):
    """Snap perimeter points to nearest nodes, mirroring new_select_landmarks
    but valid for any landmark count."""
    import Data.KDtree as KDtree
    tree = KDtree.buildKDtree(graph.getPoints())
    landmarks = []
    for p in _perimeter_points(graph, k):
        c = graph.closest(tree, p)
        if c not in landmarks:
            landmarks.append(c)
    return landmarks


def _farthest_point_fill(graph, current, k):
    """Greedily add the node farthest (Euclidean) from the current set until
    there are k landmarks. Guarantees k distinct, well-spread landmarks."""
    nodes = list(graph.nodes())
    coords = {n: (graph.getX(n), graph.getY(n)) for n in nodes}
    current = list(current)
    chosen = set(current)
    if not current:
        current.append(nodes[0])
        chosen.add(nodes[0])
    INF = float("inf")
    mind = {}
    for n in nodes:
        nx, ny = coords[n]
        m = INF
        for c in current:
            cx, cy = coords[c]
            d = (nx - cx) ** 2 + (ny - cy) ** 2
            if d < m:
                m = d
        mind[n] = m
    while len(chosen) < k and len(chosen) < len(nodes):
        best, bestd = None, -1.0
        for n in nodes:
            if n in chosen:
                continue
            if mind[n] > bestd:
                bestd, best = mind[n], n
        chosen.add(best)
        current.append(best)
        bx, by = coords[best]
        for n in nodes:
            if n in chosen:
                continue
            nx, ny = coords[n]
            d = (nx - bx) ** 2 + (ny - by) ** 2
            if d < mind[n]:
                mind[n] = d
    return current


def select_k_landmarks(ALT, graph, k):
    """Return exactly k distinct landmarks (or |V| if k > |V|).

    Seeds from the project's new_select_landmarks when it can handle k (>=4);
    falls back to a perimeter sampler for k<4. Either way, if the snap-and-dedup
    step yields fewer than k unique nodes, top up with farthest-point sampling
    so the requested count is actually reached."""
    try:
        base = ALT.new_select_landmarks(graph, k) or []
    except ZeroDivisionError:
        base = _fallback_landmarks(graph, k)
    seen, uniq = set(), []
    for n in base:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    if len(uniq) >= k:
        return uniq[:k]
    return _farthest_point_fill(graph, uniq, k)


def build_landmark_h(ALT, graph, num_landmarks):
    landmarks = select_k_landmarks(ALT, graph, num_landmarks)
    pp = ALT.landmark_distances(graph, landmarks)
    h = lambda p1, p2: ALT.landmark_h(p1, p2, pp, len(landmarks))
    return h, len(landmarks)


def make_algos(mods, h_euclid, h_landmark):
    Dijkstra, AStar, ALT, bidirectionals = mods
    return [
        AlgoSpec("Dijkstra",
                 lambda g, s, t: Dijkstra.dijk_s_to_t(g, s, t)),
        AlgoSpec("A*",
                 lambda g, s, t: AStar.new_astar(g, s, t, h_euclid)),
        AlgoSpec("Bidirectional A*",
                 lambda g, s, t: bidirectionals.bi_astar_new(g, s, t, h_euclid)),
        AlgoSpec("ALT",
                 lambda g, s, t: AStar.new_astar(g, s, t, h_landmark)),
    ]


# =============================================================================
# Landmark sweep
# =============================================================================
def run_landmark_sweep(mods, graph, queries, counts, repeats=3):
    Dijkstra, AStar, ALT, bidirectionals = mods
    rows = []
    for k in counts:
        print(f"\n[sweep] {k} landmark(s): preprocessing ...")
        try:
            (h_landmark, kk), prep = measure_block(
                lambda: build_landmark_h(ALT, graph, k))
            spec = AlgoSpec(f"ALT-{kk}",
                            lambda g, s, t, h=h_landmark: AStar.new_astar(g, s, t, h))
            recs, per_algo, _ = run_benchmark(graph, [spec], queries, repeats,
                                              progress=False)
            s = summarize(recs, per_algo, [spec.name])[spec.name]
        except Exception:
            print(f"[sweep] {k} landmarks FAILED:")
            traceback.print_exc()
            continue
        rows.append({
            "landmarks": kk,
            "time_ms": s["time_ms"], "vertices": s["vertices"],
            "edges_relaxed": s["edges_relaxed"], "memory_kb": s["memory_kb"],
            "prep_wall_s": prep["wall"], "prep_mem_kb": prep["peak_bytes"] / 1024.0,
        })
        print(f"[sweep] {kk} landmarks: time {s['time_ms']:.3f} ms, "
              f"vertices {s['vertices']:.0f}, prep {prep['wall']:.2f}s, "
              f"prep mem {prep['peak_bytes']/1024:.0f} KB")
    return rows


# =============================================================================
# Entry point
# =============================================================================
def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--graph", choices=["adj", "nx"], default="adj")
    p.add_argument("--queries", type=int, default=100)
    p.add_argument("--repeats", type=int, default=3,
                   help="timing repeats per query (best is kept)")
    p.add_argument("--landmarks", type=int, default=16,
                   help="landmarks for the main ALT row")
    p.add_argument("--landmark-sweep", action="store_true",
                   help="run ONLY the landmark sensitivity sweep "
                        "(skips the Dijkstra/A*/Bidirectional/ALT baseline benchmark)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--outdir", default="Comparison_output")
    p.add_argument("--adjacency-path", default="Data/ObbyMap32_pruned.json")
    p.add_argument("--graph-file", default="Data/Old_Graph_data/walkability_graph.pkl")
    p.add_argument("--viz-query", type=int, default=0,
                   help="index of the query to visualise (-1 to disable)")
    p.add_argument("--no-equal-aspect", action="store_true")
    args = p.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    graph, mods, queries_fn, euclid_h_factory = load_graph(
        args.graph, args.adjacency_path, args.graph_file)
    Dijkstra, AStar, ALT, bidirectionals = mods

    random.seed(args.seed)
    queries = queries_fn(args.queries)
    print(f"Selected {len(queries)} query pairs on the {args.graph} graph.")

    tex_path = os.path.join(args.outdir, f"{args.graph}_tables.tex")

    if args.landmark_sweep:
        # Sweep-only mode: skip the four-algorithm baseline benchmark
        # (Dijkstra / A* / Bidirectional A* / ALT) and its CSVs/summary tables;
        # produce only the landmark sensitivity table.
        rows = run_landmark_sweep(mods, graph, queries, LANDMARK_COUNTS, args.repeats)
        if rows:
            lm_tex = latex_landmark(rows, args.queries)
            # standalone file + the combined tables file (only the sweep table)
            with open(os.path.join(args.outdir, f"{args.graph}_landmark_table.tex"),
                      "w") as f:
                f.write(lm_tex + "\n")
            with open(tex_path, "w") as f:
                f.write(lm_tex + "\n")
            print("\nLaTeX table written to:", tex_path)
            print("\n" + lm_tex)
        else:
            print("\n[sweep] produced no rows -- landmark table skipped.")
    else:
        h_euclid = euclid_h_factory()
        print(f"ALT preprocessing ({args.landmarks} landmarks) ...")
        (h_landmark, n_lm), prep = measure_block(
            lambda: build_landmark_h(ALT, graph, args.landmarks))
        print(f"  done in {prep['wall']:.2f}s, peak {prep['peak_bytes']/1024:.0f} KB")

        algos = make_algos(mods, h_euclid, h_landmark)
        algo_order = [a.name for a in algos]

        print("\nRunning benchmark ...")
        records, per_algo, qdist = run_benchmark(graph, algos, queries, args.repeats)
        summary = summarize(records, per_algo, algo_order)
        buckets = bucket_analysis(records, algo_order, DEFAULT_BUCKETS)

        print_console_summary(summary, algo_order, args.queries)
        write_raw_csv(records, os.path.join(args.outdir, f"{args.graph}_raw.csv"))
        write_summary_csv(summary, algo_order,
                          os.path.join(args.outdir, f"{args.graph}_summary.csv"))

        tex = [latex_summary(summary, algo_order, args.queries), "",
               latex_relative(summary, algo_order), "",
               latex_buckets(buckets, algo_order, DEFAULT_BUCKETS)]

        with open(tex_path, "w") as f:
            f.write("\n".join(tex) + "\n")
        print("\nLaTeX tables written to:", tex_path)
        print("\n" + "\n\n".join(tex))

        if args.viz_query is not None and args.viz_query >= 0 and len(queries):
            qi = min(args.viz_query, len(queries) - 1)
            s, t = queries[qi]
            print(f"\nVisualising query {qi}: s={s} t={t}")
            visualize_query(graph, algos, s, t, args.outdir, args.graph,
                            equal_aspect=not args.no_equal_aspect)

    print("\nNote: 'CPU cycles' has no portable counter in Python. The CSV's")
    print("prim_calls (cProfile primitive calls) and cpu_ms columns are the")
    print("deterministic work proxies; edges_relaxed/vertices are the")
    print("machine-independent complexity measures you can cite directly.")
    print(f"\nAll outputs in: {os.path.abspath(args.outdir)}")


if __name__ == "__main__":
    main()