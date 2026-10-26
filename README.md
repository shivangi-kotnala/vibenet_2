# VibeNet: do friends listen to the same music?
DSE3150 Graph Visualization project.

Purpose: show whether friends share music taste, which friend groups ("tribes") exist, and who connects them.
Data: LastFM Asia social network (Rozemberczki & Sarkar, 2020, FEATHER paper), collected from the public Last.fm API in March 2020.
7,624 listeners, 27,806 mutual follows, 7,842 artists liked, 18 country codes. CC BY 4.0.
Source: snap.stanford.edu/data/feather-lastfm-social.html (files also in github.com/benedekrozemberczki/FEATHER).

Names: the dataset anonymizes countries and artists, and I found no mapping published with it, so the app shows "Country 10" and "Artist #1234".
To show real names, add data/country_names.csv (columns: code,name) and/or data/artist_names.csv (columns: artist_id,name). The app picks them up automatically.

Files: app.py (Streamlit app), preprocess.py (builds data/vibenet.json), DESIGN.md (design principles, pipeline, visual mapping; also shown on the Design tab), requirements.txt, data/vibenet.json.
Run: pip install -r requirements.txt, then streamlit run app.py
Rebuild data: python preprocess.py (downloads the raw files; exact betweenness takes a few minutes)
Deploy: push all files to GitHub and use share.streamlit.io with main file app.py. vibenet.json can sit in a data/ folder or next to app.py. DESIGN.md must be in the repo for the Design tab.

Tabs: About, Network, Listener (profile for any listener ID), Tribes, Taste, Analytics, Design, Insights.
