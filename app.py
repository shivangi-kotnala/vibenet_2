import json, random
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
import plotly.express as px, plotly.graph_objects as go, plotly.io as pio, streamlit as st
from scipy.spatial import ConvexHull

st.set_page_config("VibeNet", layout="wide")
HERE = Path(__file__).parent
COLS = ["id", "country", "tribe", "comm", "friends", "pagerank", "betweenness", "cross", "taste", "liked", "x", "y"]
TRIBES = [f"Tribe {i}" for i in range(1, 9)] + ["Other"]
# Look: charcoal background, clear categorical colors (8 tribes + grey Other)
PAL = ["#F25F5C", "#F5A524", "#A3D94F", "#2FBF71", "#3CC8D8", "#4C8DF6", "#A06CF0", "#E054A8", "#6B7280"]
APAL = px.colors.sample_colorscale("Turbo", [0.04 + 0.92 * i / 17 for i in range(18)])
HEAT = ["#0D1117", "#12476B", "#1FA2A6", "#F2C14E", "#FFF1B8"]
GRID = "rgba(139,148,158,.18)"
_t = go.layout.Template(pio.templates["plotly_dark"])
_t.layout.update(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#E6EDF3"), colorway=PAL, legend=dict(bgcolor="rgba(0,0,0,0)"))
_t.layout.xaxis.update(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
_t.layout.yaxis.update(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
_t.layout.modebar.update(bgcolor="rgba(48,54,61,.95)", color="#FFFFFF", activecolor="#F5A524")   # zoom/pan toolbar is clearly visible
pio.templates["vibe"] = _t

def show(fig, **kw):  # always show the zoom/pan toolbar; the mouse wheel keeps scrolling the page
    show(fig, width="stretch", config={"displayModeBar": True, "displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"], **kw})

@st.cache_data
def spread(xy, r, it=40):  # nudge overlapping dots apart so dense groups are readable (display only)
    xy = xy.astype(np.float32).copy(); eye = np.eye(len(xy), dtype=bool)
    for _ in range(it):
        d = xy[:, None, :] - xy[None, :, :]; dist = np.sqrt((d ** 2).sum(2)) + eye
        w = np.where((dist < r) & ~eye, (r - dist) / dist, 0).astype(np.float32)
        step = (w[:, :, None] * d).sum(1) * .5
        if not step.any(): break
        xy += step
    return xy
def rgba(c, a):  # accepts "#RRGGBB" or "rgb(r, g, b)" colors
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5)) if c.startswith("#") else (int(x) for x in c[c.index("(") + 1:-1].split(",")[:3])
    return f"rgba({r},{g},{b},{a})"

def find(name):
    for p in (HERE / "data" / name, HERE / name):
        if p.exists(): return p

def names(file, k, v):  # optional mapping CSVs; empty if the file is absent
    p = find(file)
    if not p: return {}
    t = pd.read_csv(p); return dict(zip(t[k].astype(int), t[v]))

@st.cache_data
def load():
    p = find("vibenet.json")
    if p is None: return None
    D = json.loads(p.read_text(encoding="utf-8")); df = pd.DataFrame(D["nodes"], columns=COLS)
    df["tribe"] = df.tribe.map(lambda i: TRIBES[i]); adj = {}
    for a, b in D["edges_all"]: adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    return D, df, adj, names("country_names.csv", "code", "name"), names("artist_names.csv", "artist_id", "name")

R = load()
if R is None:
    st.error("Data file vibenet.json not found. Put it in a data/ folder next to app.py (or directly next to app.py)."); st.stop()
D, df, adj, CN, AN = R; P = D["props"]
cname = lambda c: CN.get(int(c), f"Country {int(c):02d}"); aname = lambda a: AN.get(int(a), f"Artist #{int(a)}")
df["country_name"] = df.country.map(cname)
TCOL = dict(zip(TRIBES, PAL)); CCOL = {n: APAL[i % len(APAL)] for i, n in enumerate(sorted(df.country_name.unique()))}
IDS = set(df.id)

if "who" not in st.session_state: st.session_state.who = ""
def go_to(i): st.session_state.who = str(int(i))
st.sidebar.header("Find a listener")
st.sidebar.text_input(f"Listener ID (0 to {len(df) - 1})", key="who")
b1, b2 = st.sidebar.columns(2)
b1.button("Random", on_click=lambda: go_to(random.choice(df.id.tolist())))
b2.button("Top bridge", on_click=lambda: go_to(df.nlargest(1, "betweenness").id.iloc[0]))
who = st.session_state.who.strip(); sel = int(who) if who.isdigit() and int(who) in IDS else None
if who and sel is None: st.sidebar.error(f"No listener with ID '{who}'. Valid IDs are 0 to {len(df) - 1}.")
st.sidebar.header("Graph controls")
color_by = st.sidebar.radio("Color by", ["tribe", "country"])
size_by = st.sidebar.radio("Size by", ["pagerank", "friends", "betweenness"])
top_n = st.sidebar.slider("Listeners shown (most central first)", 100, 1500, 300, 100)
min_f = st.sidebar.slider("Min friends", 0, 50, 0)
cset = st.sidebar.multiselect("Countries", sorted(CCOL), default=sorted(CCOL))
outlines = st.sidebar.checkbox("Show group outlines", True)
lines = st.sidebar.checkbox("Show friendship lines", True)

st.markdown("""<style>
h1 {background: linear-gradient(90deg, #FF6B9D, #FFB347, #FFE066); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800;}
[data-testid="stMetricValue"] {color: #F5C542;}
[data-testid="stMetricLabel"] {color: #8B949E;}
.stTabs [data-baseweb="tab"] {font-weight: 600;}
</style>""", unsafe_allow_html=True)
st.title("VibeNet")
st.caption("Built by Shivangi Kotnala")
st.caption("Do friends listen to the same music? Listeners are vertices; a mutual follow on Last.fm is an edge.")
for col, (k, v) in zip(st.columns(6), [("Listeners", f"{P['vertices']:,}"), ("Friendships", f"{P['edges']:,}"), ("Density", P["density"]),
        ("Components", P["components"]), ("Communities", P["communities"]), ("Modularity", P["modularity"])]): col.metric(k, v)
tabs = st.tabs(["About", "Network", "Listener", "Tribes", "Taste", "Analytics", "Design", "Insights"])

with tabs[0]:
    st.markdown(f"""**Purpose:** find out whether friends share music taste, which friend groups ("tribes") exist, and who connects them.

**Dataset:** LastFM Asia social network (Rozemberczki & Sarkar, 2020; SNAP). Each vertex is a Last.fm user from Asia, each edge a mutual follow. Each user has a list of liked artists ({P['artists']:,} artists in total) and a country code. Collected in March 2020.

**Names:** the dataset anonymizes countries and artists, so the app shows "Country 10" and "Artist #1234". If you add `data/country_names.csv` (code,name) or `data/artist_names.csv` (artist_id,name), real names appear automatically.

**Start here:** use the sidebar to search any listener ID, then open the Network and Listener tabs.""")
    st.caption("Source: snap.stanford.edu/data/feather-lastfm-social.html (CC BY 4.0 on UCI)")

with tabs[1]:
    with st.expander("How to read this graph"):
        st.markdown("- **Dot** = one listener. **Line** = a mutual follow (friendship).\n- **Color** = tribe or country (sidebar). **Outline** = shaded area around dots of one color.\n"
                    "- **Dot size** = the measure chosen in the sidebar. **White ring** = the searched listener; their friendships are drawn in white.\n"
                    "- Closeness comes from the layout algorithm, so it hints at groups but is not a measured distance.")
    gcol = "tribe" if color_by == "tribe" else "country_name"; CMAP = TCOL if color_by == "tribe" else CCOL
    sub = df[df.x.notna() & (df.friends >= min_f) & df.country_name.isin(cset)].nlargest(top_n, "pagerank")
    if sub.empty: st.warning("No listeners match these filters. Loosen a filter in the sidebar.")
    else:
        ext = max(np.ptp(sub.x), np.ptp(sub.y)); sub = sub.copy(); sub[["x", "y"]] = spread(sub[["x", "y"]].to_numpy(float), float(ext) * .022)
        vis = set(sub.id); pos = dict(zip(sub.id, zip(sub.x, sub.y)))
        allE = [(a, b) for a, b in D["edges"] if a in vis and b in vis]; E = allE
        if len(E) > 2500: random.seed(1); E = random.sample(allE, 2500)
        if not lines: E = []
        ego = [(a, b) for a, b in allE if sel in (a, b)] if sel in vis else []
        focus = ({sel} | set(adj.get(sel, []))) if sel in vis else None
        fig = go.Figure()
        if outlines:                                  # closure cue: translucent outline around each color group
            for g, s in sub.groupby(gcol):
                if len(s) < 8 or g == "Other": continue
                xy = s[["x", "y"]].to_numpy(); d = np.linalg.norm(xy - np.median(xy, 0), axis=1); xy = xy[d <= np.percentile(d, 75)]
                try: h = ConvexHull(xy); ring = xy[np.append(h.vertices, h.vertices[0])]
                except Exception: continue
                fig.add_trace(go.Scatter(x=ring[:, 0], y=ring[:, 1], mode="lines", fill="toself", hoverinfo="skip",
                    fillcolor=rgba(CMAP[g], .07), line=dict(width=1.2, color=rgba(CMAP[g], .5), dash="dot")))
        ex, ey = [], []
        for a, b in E: ex += [pos[a][0], pos[b][0], None]; ey += [pos[a][1], pos[b][1], None]
        fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", line=dict(width=.4, color="#8B949E"), opacity=.22, hoverinfo="none"))
        if ego:
            fx, fy = [], []
            for a, b in ego: fx += [pos[a][0], pos[b][0], None]; fy += [pos[a][1], pos[b][1], None]
            fig.add_trace(go.Scatter(x=fx, y=fy, mode="lines", line=dict(width=1.6, color="white"), hoverinfo="none"))
        v = sub[size_by].astype(float)
        fig.add_trace(go.Scatter(x=sub.x, y=sub.y, mode="markers", hoverinfo="text",
            text=[f"Listener {r.id}<br>{r.tribe} | {r.country_name}<br>Friends: {r.friends}<br>PageRank: {r.pagerank:.2f}<br>Taste match with friends: {r.taste:.2f}" for r in sub.itertuples()],
            marker=dict(size=5 + 15 * np.sqrt(v / v.max()), color=[CMAP[k] for k in sub[gcol]], line=dict(width=.6, color="#0D1117"),
                        opacity=[.95 if focus is None or i in focus else .12 for i in sub.id])))
        if sel in vis:
            fig.add_trace(go.Scatter(x=[pos[sel][0]], y=[pos[sel][1]], mode="markers+text", text=[f"Listener {sel}"], textposition="top center",
                hoverinfo="skip", marker=dict(size=26, symbol="circle-open", line=dict(color="white", width=3))))
        pad = ext * .05
        fig.update_layout(template="vibe", height=650, showlegend=False, dragmode="pan", margin=dict(l=0, r=0, t=0, b=0), uirevision=f"{top_n}-{min_f}-{len(cset)}",
                          xaxis=dict(visible=False, range=[sub.x.min() - pad, sub.x.max() + pad]), yaxis=dict(visible=False, range=[sub.y.min() - pad, sub.y.max() + pad]))
        show(fig)
        cnt = sub[gcol].value_counts(); order = [t for t in TRIBES if t in cnt] if gcol == "tribe" else list(cnt.index)
        st.markdown("  ".join(f"<span style='color:{CMAP[k]}'>●</span> {k} ({cnt[k]})" for k in order), unsafe_allow_html=True)
        what = {"pagerank": "PageRank (linked to well-connected listeners)", "friends": "number of friends", "betweenness": "betweenness (sits on many shortest paths)"}[size_by]
        st.caption(f"Showing {len(sub):,} of {len(df):,} listeners and {len(E):,} of {len(allE):,} friendships among them. Dot size = {what}.")
        if sel is not None and sel not in vis: st.info(f"Listener {sel} is not in this view (only the most central listeners have a position here). Open the Listener tab to see their friends.")
        elif sel is not None: st.info(f"Listener {sel} is highlighted. Open the Listener tab for the full profile.")

with tabs[2]:
    if sel is None: st.info("Enter a listener ID in the sidebar, or press Random or Top bridge.")
    else:
        r = df[df.id == sel].iloc[0]; fl = adj.get(sel, []); shared, sim, hits = D["prof"][str(sel)]; ci = D["comm_info"][int(r.comm)]
        rank = lambda c: int((df[c] > r[c]).sum()) + 1
        comm = f"{r.tribe} ({ci['size']:,} listeners)" if r.tribe != "Other" else f"Community {int(r.comm)} (small, {ci['size']} listeners)"
        st.subheader(f"Listener {sel}")
        for col, (k, val) in zip(st.columns(5), [("Country", r.country_name), ("Community", comm), ("Friends", int(r.friends)),
                ("PageRank", f"{r.pagerank:.2f}"), ("Betweenness", f"{r.betweenness:.4f}")]): col.metric(k, val)
        st.caption(f"PageRank rank #{rank('pagerank')} of {len(df):,} (1.00 = average). Betweenness rank #{rank('betweenness')} (exact). Friends: median listener has {P['median_degree']}. "
                   f"{r.cross * 100:.0f}% of their friends are in a different community.")
        c1, c2 = st.columns([1.1, 1])
        with c1:
            S = [sel] + fl; Ge = nx.Graph(); Ge.add_nodes_from(S)
            for a in S: Ge.add_edges_from((a, b) for b in adj.get(a, []) if b in set(S))
            pe = nx.spring_layout(Ge, seed=1, k=1.2 / np.sqrt(len(Ge))); lk = df.set_index("id")
            ex, ey = [], []
            for a, b in Ge.edges(): ex += [pe[a][0], pe[b][0], None]; ey += [pe[a][1], pe[b][1], None]
            f2 = go.Figure([go.Scatter(x=ex, y=ey, mode="lines", line=dict(width=.8, color="#8B949E"), opacity=.5, hoverinfo="none"),
                go.Scatter(x=[pe[n][0] for n in S], y=[pe[n][1] for n in S], mode="markers", hoverinfo="text",
                    text=[f"Listener {n}<br>{lk.at[n, 'tribe']} | {cname(lk.at[n, 'country'])}<br>Friends: {lk.at[n, 'friends']}" for n in S],
                    marker=dict(size=[22 if n == sel else 9 for n in S], color=["white" if n == sel else TCOL[lk.at[n, "tribe"]] for n in S],
                                line=dict(width=1.2, color="#0D1117")))])
            f2.update_layout(template="vibe", height=430, showlegend=False, xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(l=0, r=0, t=0, b=0))
            show(f2); st.caption("This listener (white) and their friends, colored by tribe; lines are friendships among them.")
            if fl:
                st.selectbox("Open a friend's profile", sorted(fl), index=None, key=f"jump_{sel}",
                             on_change=lambda k=f"jump_{sel}": go_to(st.session_state[k]) if st.session_state[k] is not None else None)
        with c2:
            st.markdown("**Similarity with friends**")
            pct = (df.taste < r.taste).mean() * 100
            st.write(f"Average artist overlap with friends: **{r.taste:.3f}** (random pairs: {P['stranger_taste']:.3f}). Higher than {pct:.0f}% of listeners. Overlap = artists in common divided by artists either person likes.")
            if sim: st.dataframe(pd.DataFrame(sim, columns=["friend", "overlap", "artists in common"]), hide_index=True)
            st.markdown("**Music preferences**")
            st.write(f"Likes **{int(r.liked)}** artists.")
            if shared:
                st.caption("Artists liked by the most of this listener's friends:")
                st.dataframe(pd.DataFrame([[aname(a), f"{c} of {len(fl)}", D["art_pop"][str(a)]] for a, c in shared],
                    columns=["artist", "friends who like it", "listeners overall"]), hide_index=True)
            if ci["signature"]: st.write(f"Signature artists of this community: {', '.join(aname(a) for a in ci['signature'])}. Likes **{hits} of {len(ci['signature'])}**.")

with tabs[3]:
    st.caption("The 8 biggest tribes: size, main country, share of the tribe from that country, and signature artists.")
    T = pd.DataFrame([dict(tribe=f"Tribe {i + 1}", listeners=c["size"], main_country=cname(c["main_country"]), share_from_it=c["country_share"],
        avg_friends=c["avg_degree"], signature_artists=", ".join(aname(a) for a in c["signature"])) for i, c in enumerate(D["comm_info"][:8])])
    st.dataframe(T, hide_index=True)
    mode = st.radio("Heatmap shows", ["listener counts", "share of each tribe"], horizontal=True)
    M = np.array(D["tribe_country"], float); M = M / np.maximum(M.sum(1, keepdims=True), 1) if mode.startswith("share") else M
    st.caption("Bright cells mean many listeners (or a large share of a tribe) come from that country code, so friend groups follow geography.")
    show(px.imshow(M, x=[cname(i) for i in range(18)], y=TRIBES, template="vibe", color_continuous_scale=HEAT))

with tabs[4]:
    st.caption("Taste overlap: the share of liked artists two listeners have in common; friends sit higher than random pairs.")
    H = D["taste_hist"]; hd = pd.DataFrame({"overlap": H["bins"] * 2, "listener pairs": H["friends"] + H["strangers"], "pair type": ["friends"] * len(H["bins"]) + ["random strangers"] * len(H["bins"])})
    show(px.bar(hd, x="overlap", y="listener pairs", color="pair type", barmode="group", color_discrete_map={"friends": "#3CC8D8", "random strangers": "#F25F5C"}, template="vibe").update_layout(bargap=.15))
    st.caption("Each listener's average taste overlap with friends against how many friends they have.")
    show(px.scatter(df, x="friends", y="taste", color="tribe", color_discrete_map=TCOL, log_x=True, opacity=.6, template="vibe").update_traces(marker=dict(size=6, line=dict(width=0))))

with tabs[5]:
    st.caption("Degree distribution: most listeners have a few friends while a handful have over a hundred.")
    dd = pd.DataFrame({"friends": range(len(D["deg"])), "listeners": D["deg"]}).query("listeners > 0 and friends > 0")
    show(px.scatter(dd, x="friends", y="listeners", log_x=True, log_y=True, template="vibe").update_traces(marker=dict(size=9, color="#F5A524", line=dict(width=0))))
    st.caption("Most central listeners (PageRank).")
    st.dataframe(df.nlargest(10, "pagerank")[["id", "tribe", "country_name", "friends", "pagerank"]], hide_index=True)
    st.caption("Top bridges: listeners on many shortest paths between others (exact betweenness).")
    st.dataframe(df.nlargest(10, "betweenness")[["id", "tribe", "friends", "cross", "betweenness"]], hide_index=True)
    st.caption("Most-liked artists: how many listeners like them.")
    st.dataframe(pd.DataFrame([[aname(a), c] for a, c in D["top_artists"]], columns=["artist", "listeners"]), hide_index=True)

with tabs[6]:
    dm = find("DESIGN.md")
    if dm is None: st.warning("DESIGN.md not found.")
    else:
        t1, t2 = dm.read_text(encoding="utf-8").split("<!--DIAGRAM-->")
        st.markdown(t1)
        st.graphviz_chart('digraph { rankdir=LR; node [shape=box, style=rounded]; "Raw dataset" -> "Preprocessing" -> "Graph and attribute tables" -> "Visual mapping" -> "Interactive views" -> "Insights" }')
        st.markdown(t2)

with tabs[7]:
    st.caption("Plain-language findings computed from this network.")
    for line in D["insights"]: st.markdown(f"- {line}")
