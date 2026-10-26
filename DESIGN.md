# VibeNet design notes

## 1. Visualization Design Principles

### Gestalt principles
- **Proximity.** The layout algorithm (spring layout) places connected listeners closer together, so dots that sit near each other often look like a group. This is a visual cue only: layout distance does **not** prove a stronger relationship, because the positions come from the whole network's structure and are not a measured distance between two listeners.
- **Similarity.** Listeners with the same color belong to the same tribe (or the same country, when you color by country). The colors are fixed, so a tribe keeps its color when you change filters.
- **Connectedness.** Every line is an explicit mutual-follow (friendship). Lines, not nearness, are what tell you two listeners are friends. When you search a listener, their friendships are drawn in white.
- **Continuity.** Straight, thin lines let the eye follow a chain of friendships from one listener to another through the graph. This works best on a small view, such as a searched listener, and gets weaker when many lines overlap.
- **Closure.** Implemented as an optional cue. The "Show group outlines" checkbox (on by default) draws a translucent outline around the dots of each color group, so a scattered group reads as one shape. The outline is a convex hull of the central 85% of that group's displayed dots; it is a visual aid, not a precise boundary, outlines can overlap, and groups with fewer than 8 displayed dots get none. Closure is not used in the other tabs.

### How information overload is reduced
- **Filters.** Country selection, minimum number of friends, and a search for one listener, plus dimming everyone except the searched listener and their friends.
- **A limited number of nodes and edges.** The network view shows at most the 1,500 most central listeners (the slider starts at 500, ordered by PageRank), and at most 6,000 friendships are drawn at once. The statistics and the other tabs use the complete network of 7,624 listeners.
- **Aggregated summaries.** The summary cards, tribe table, tribe-by-country heatmap, degree distribution and taste-overlap histogram describe many listeners at once instead of drawing each one.
- **Details on demand.** Hover shows a listener's details, and the Listener tab shows the full profile for any listener, including ones that are not drawn in the main graph.

<!--DIAGRAM-->
## 2. Visualization pipeline

```
Raw dataset -> preprocessing -> graph and attribute tables -> visual mapping -> interactive views -> insights
```

| Stage | What happens |
|---|---|
| **Raw dataset** | Three files from the LastFM Asia dataset: friendships (edges CSV), the artists each listener likes (features JSON) and a country code per listener (target CSV). |
| **Preprocessing** (`preprocess.py`) | Builds the graph with NetworkX and computes PageRank, exact betweenness, Louvain communities, the share of friends outside a listener's community, taste overlap (artists in common divided by artists either likes) for friends and for random pairs, signature artists per community, a per-listener music profile, and a 2D layout for the 1,500 most central listeners. |
| **Graph and attribute tables** | Everything is written to one file, `data/vibenet.json`: one row per listener (country, community, friends, PageRank, betweenness, taste, position), the friendship list, community summaries, histograms and the profiles. |
| **Visual mapping** | `app.py` loads the JSON once (cached) into a pandas table and dictionaries, then maps columns to position, color, size, lines and heatmap intensity (section 3). |
| **Interactive views** | Streamlit widgets (search, filters, tabs) and Plotly charts: Network, Listener, Tribes, Taste, Analytics. Almost nothing is recomputed in the browser session; only the small friend graph for a searched listener is laid out on demand. |
| **Insights** | Findings such as "friends overlap more in taste than strangers" and "friend groups follow geography", computed in preprocessing and shown on the Insights tab. |

## 3. Visual mapping

| Visual channel | Data | Why it suits the data | What not to infer |
|---|---|---|---|
| **Position (x, y)** | Output of a spring layout of the friendship graph | Position is the most accurate channel for seeing groups; linked listeners end up near each other | Distance is not a similarity score. Two nearby dots are not necessarily friends, and the axes have no units. Positions exist only for the 1,500 most central listeners |
| **Color** | Tribe (8 biggest communities plus Other) or country code | Hue separates unordered categories well | Color shows membership only, not ranking. "Other" mixes many small communities. Country codes are anonymized, so a code is not a named country |
| **Size** | PageRank, number of friends, or betweenness (your choice) | Area suits a quantity: bigger means more | Size depends on the measure selected: a large dot under PageRank is not necessarily a listener with many friends. Size is not popularity outside this dataset |
| **Lines** | One mutual follow between two listeners | The direct way to show a relationship | Line count is not friendship strength, since all friendships are equal. A random sample of up to 6,000 lines is drawn, so a missing line does not mean no friendship |
| **Heatmap color intensity** | Number of listeners (or share of a tribe) per tribe-country cell | Intensity suits counts across a grid and shows the bright cells at a glance | It is not a rate or a causal link between tribe and country. Counts favor large tribes; use the share option to compare tribes fairly |

**Data notes.** Betweenness here is computed exactly on the complete graph. Country and artist IDs are anonymized in the dataset; names appear only if you add `data/country_names.csv` or `data/artist_names.csv`.
