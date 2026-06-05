# Graph vs Relational Database Demo

Movie recommendation system built on Neo4j and the MovieLens 100K dataset.

## Structure

```
bdnv-graph-vs-relational-db-demo/
├── .env.example          # Environment variable template
├── requirements.txt      # Python dependencies
├── db.py                 # Neo4j driver singleton + run_query helper
├── data_prep.py          # Download or generate MovieLens data into DataFrames
├── ingest.py             # Batch-load nodes and relationships into Neo4j
├── queries.py            # All Cypher queries (traversals, pattern matching, recommendations)
├── relational.py         # SQLite equivalents for benchmarking
├── benchmark.py          # Side-by-side performance comparison (9 queries)
├── cli.py                # Interactive terminal explorer
├── api.py                # Flask REST API
├── dump.py               # Export Neo4j graph as Cypher statements
├── frontend/
│   └── index.html        # Browser UI — calls the API, shows results as live tables
├── data/                 # Generated dataset + SQLite DB + dump file
└── reports/
    └── report.md         # Full project report
```

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env          # fill in Neo4j credentials (see note below)
python ingest.py              # generate data and populate graph (~2 min)
python benchmark.py           # run all 9 queries and print comparison table
python cli.py                 # interactive terminal explorer
python api.py                 # start REST API on :5000, then open frontend/index.html
python dump.py                # export Cypher dump to data/movielens_dump.cypher
```

## Neo4j connection

AuraDB (free cloud tier at console.neo4j.io) is the recommended setup. Use `neo4j+s://` as the URI scheme:

```
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=yourpassword
```

For local Docker: `NEO4J_URI=bolt://localhost:7687`

## Dataset

The real MovieLens 100K dataset can be downloaded manually from
https://files.grouplens.org/datasets/movielens/ml-latest-small.zip and placed at
`data/ml-latest-small.zip`. If absent, `data_prep.py` automatically generates a
synthetic dataset of identical structure (500 movies, 943 users, 100 000 ratings).

## Graph model

```
(User)-[:RATED {rating, timestamp}]->(Movie)-[:IN_GENRE]->(Genre)
```

| Label   | Key properties                            |
|---------|-------------------------------------------|
| Movie   | movie_id, title, year, avg_rating         |
| User    | user_id, age, gender, occupation          |
| Genre   | name                                      |

## Queries

| # | Name | Function | vs SQL |
|---|------|----------|--------|
| Q1 | Movies rated by user | `movies_rated_by_user` | — |
| Q2 | Top movies by genre | `top_movies_by_genre` | ✅ benchmarked |
| Q3 | Collaborative filter recs | `collaborative_filter_recommendations` | ✅ benchmarked |
| Q4 | Similar-taste users | `similar_taste_users` | — |
| Q5 | Shortest path between users | `shortest_path_between_users` | — |
| Q6 | Friends-of-friends genre overlap | `friends_of_friends_genre_overlap` | — |
| Q7 | Genre-based recommendations | `genre_based_recommendations` | — |
| Q8 | Multi-hop co-rating chain (depth 3) | `multi_hop_corating_chain` | ✅ benchmarked — Neo4j ~84ms vs SQL ~20s |
| Q9 | Pairwise user overlap | `triangle_detection` | ✅ benchmarked — SQL wins (bulk scan) |

## API endpoints

All responses include `rows`, `count`, and `elapsed_ms`.

| Endpoint | Description |
|----------|-------------|
| GET `/stats` | Node and edge counts |
| GET `/user/<uid>/ratings` | All ratings for a user |
| GET `/user/<uid>/recommendations/collaborative` | Collaborative filter recs |
| GET `/user/<uid>/recommendations/genre` | Genre-affinity recs |
| GET `/user/<uid>/similar-users` | Users with similar taste |
| GET `/user/<uid>/peers` | Users who rated same movies |
| GET `/user/<uid>/fof-genre/<genre>` | Friends-of-friends genre overlap |
| GET `/genre/<name>/top` | Top-rated movies in a genre |
| GET `/path?uid1=&uid2=` | Shortest path between two users |

## Frontend

Open `frontend/index.html` in a browser while `python api.py` is running. Select a query type, enter a user ID or genre, and results appear as a live table with row count and elapsed milliseconds.