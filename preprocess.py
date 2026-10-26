# LastFM Asia (SNAP / FEATHER) -> graph metrics, taste similarity, listener profiles -> data/vibenet.json
import json, os, random, urllib.request, numpy as np, pandas as pd, networkx as nx, scipy.sparse as sp
B = "https://raw.githubusercontent.com/benedekrozemberczki/FEATHER/master/new_node_level_dataset/"
FILES = {"edges": "lastfm_asia_edges.csv", "features": "lastfm_asia_features.json", "target": "lastfm_asia_target.csv"}
os.makedirs("data/raw", exist_ok=True)
for kind, f in FILES.items():
    if not os.path.exists(f"data/raw/{f}"): urllib.request.urlretrieve(B + f"{kind}/{f}", f"data/raw/{f}")
e = pd.read_csv("data/raw/lastfm_asia_edges.csv"); t = pd.read_csv("data/raw/lastfm_asia_target.csv")
likes = {int(k): set(v) for k, v in json.load(open("data/raw/lastfm_asia_features.json")).items()}
G = nx.Graph(); G.add_nodes_from(t.id); G.add_edges_from(e.itertuples(index=False, name=None)); n, m = len(G), G.number_of_edges()
country = dict(zip(t.id, t.target)); deg = dict(G.degree())
pr = nx.pagerank(G); bt = nx.betweenness_centrality(G)                    # exact betweenness
comms = sorted(nx.community.louvain_communities(G, seed=42), key=len, reverse=True); cid = {v: i for i, c in enumerate(comms) for v in c}
cross = {v: (sum(cid[u] != cid[v] for u in G[v]) / deg[v] if deg[v] else 0) for v in G}
jac = lambda a, b: len(likes[a] & likes[b]) / max(1, len(likes[a] | likes[b]))
fr = [jac(a, b) for a, b in G.edges()]; random.seed(1); ids = list(G); rp = [jac(*random.sample(ids, 2)) for _ in range(len(fr))]
taste = {v: float(np.mean([jac(v, u) for u in G[v]])) if deg[v] else 0 for v in G}
arts = np.array(sorted({a for s in likes.values() for a in s})); ai = {int(a): i for i, a in enumerate(arts)}
rows = [v for v in sorted(likes) for _ in likes[v]]; cols = [ai[a] for v in sorted(likes) for a in likes[v]]
X = sp.csr_matrix((np.ones(len(rows), dtype=np.int32), (rows, cols)), shape=(n, len(arts)))
pop = np.asarray(X.sum(0)).ravel(); overall = pop / n
comm_info = []
for i, c in enumerate(comms):                                             # signature artists for every community
    idx = sorted(c); cs = pd.Series([country[v] for v in c]).value_counts(); sig = []
    if len(c) >= 30:
        share = np.asarray(X[idx].mean(0)).ravel(); lift = share / np.maximum(overall, 1e-9)
        sig = [int(arts[j]) for j in np.argsort(-(lift * (share >= .25)))[:5] if share[j] >= .25]
    comm_info.append(dict(id=i, size=len(c), main_country=int(cs.index[0]), country_share=round(float(cs.iloc[0] / len(c)), 2), signature=sig,
                          avg_degree=round(float(np.mean([deg[v] for v in c])), 1)))
prof = {}
for v in sorted(G):                                                       # per-listener music profile
    fl = list(G[v]); liked = X[v].indices
    hits = len(set(comm_info[cid[v]]["signature"]) & likes[v])       # signature artists of own community this listener likes
    if not fl: prof[str(v)] = [[], [], hits]; continue
    cnt = np.asarray(X[fl].sum(0)).ravel()[liked]; o = np.argsort(-cnt)[:10]
    shared = [[int(arts[liked[j]]), int(cnt[j])] for j in o if cnt[j] > 0]
    sim = sorted(([u, round(jac(v, u), 3), len(likes[v] & likes[u])] for u in fl), key=lambda r: -r[1])[:5]
    prof[str(v)] = [shared, sim, hits]
K = 8; ctab = pd.crosstab(pd.Series({v: min(cid[v], K) for v in G}), pd.Series(country)).reindex(columns=range(18), fill_value=0)
topk = sorted(G, key=lambda v: -pr[v])[:1500]; H = G.subgraph(topk); pos = nx.spring_layout(H, seed=42, k=1.5 / np.sqrt(len(H)), iterations=80)
nodes = [[v, int(country[v]), min(cid[v], K), cid[v], deg[v], round(pr[v] * n, 3), round(bt[v], 6), round(cross[v], 3), round(taste[v], 3), len(likes[v]),
          round(float(pos[v][0]), 3) if v in pos else None, round(float(pos[v][1]), 3) if v in pos else None] for v in sorted(G)]
bins = np.linspace(0, .5, 26); hist = lambda a: np.histogram(np.clip(a, 0, .4999), bins)[0].tolist()
pure = sum(max(pd.Series([country[v] for v in c]).value_counts()) for c in comms) / n
P = dict(vertices=n, edges=m, density=round(nx.density(G), 5), components=nx.number_connected_components(G), isolated=sum(d == 0 for d in deg.values()),
         pendant=sum(d == 1 for d in deg.values()), avg_degree=round(2 * m / n, 2), median_degree=int(np.median(list(deg.values()))), max_degree=max(deg.values()),
         clustering=round(nx.average_clustering(G), 3), communities=len(comms), modularity=round(nx.community.modularity(G, comms), 3),
         artists=len(arts), friend_taste=round(float(np.mean(fr)), 4), stranger_taste=round(float(np.mean(rp)), 4), country_purity=round(pure, 3), betweenness="exact")
ins = [f"{n:,} listeners share {m:,} mutual follows; density {P['density']:.4f} means a sparse network.",
 f"Friends overlap more in taste: average artist overlap is {P['friend_taste']:.3f} for friends vs {P['stranger_taste']:.3f} for random pairs ({P['friend_taste']/P['stranger_taste']:.1f}x higher).",
 f"Louvain finds {len(comms)} communities (modularity {P['modularity']}); the 8 biggest are called tribes and the biggest has {len(comms[0]):,} listeners.",
 f"Friend groups follow geography: {P['country_purity']*100:.0f}% of listeners share their community's main country code.",
 f"Most listeners have few friends (median {P['median_degree']}), but the biggest hub has {P['max_degree']}."]
json.dump(dict(props=P, nodes=nodes, edges=[[a, b] for a, b in H.edges()], edges_all=[[a, b] for a, b in G.edges()], comm_info=comm_info,
    tribe_country=ctab.values.tolist(), deg=np.bincount(list(deg.values())).tolist()[:120],
    taste_hist=dict(bins=[round(x, 3) for x in bins[:-1]], friends=hist(fr), strangers=hist(rp)), prof=prof,
    art_pop={int(a): int(p) for a, p in zip(arts, pop)}, top_artists=[[int(arts[j]), int(pop[j])] for j in np.argsort(-pop)[:10]], insights=ins),
    open("data/vibenet.json", "w"), separators=(",", ":"))
print("DONE", P)
