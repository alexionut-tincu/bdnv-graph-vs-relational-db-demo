# Graph vs Relational Database Demo - Project Report

## 1. Overview

This project builds a Neo4j property graph over the **MovieLens 100K** dataset
(943 users, 500–1682 movies, 100 000 ratings) and demonstrates that graph databases
express multi-hop recommendation logic more naturally and, for certain traversals,
more efficiently than a relational equivalent. Nine queries are implemented and
timed; four are benchmarked directly against SQLite equivalents.

---

## 2. Setup Used
Laptop model: Lenovo ThinkPad T490s
CPU: Intel(R) Core(TM) i5-8565U (8) @ 3.90GHz
GPU: Integrated Intel UHD Graphics 620 @ 1.10GHz
Memory: 8 GiB
OS: Arch Linux x86_64
Kernel: Linux 6.18.18-1-lts
Python: 3.14.3
Neo4j: 6.2.0
Pandas: 3.0.3
Flask: 3.1.3
Tabulate: 0.10.0s

---

## 3. Graph Model

![Model](docs/screenshots/model.png)

### Node labels and key properties

| Label   | Properties                                          |
|---------|-----------------------------------------------------|
| `Movie` | `movie_id`, `title`, `year`, `avg_rating`           |
| `User`  | `user_id`, `age`, `gender`, `occupation`            |
| `Genre` | `name`                                              |

### Relationship types

| Relationship | Direction          | Properties                  |
|--------------|--------------------|-----------------------------|
| `RATED`      | `(User)→(Movie)`   | `rating` (1–5), `timestamp` |
| `IN_GENRE`   | `(Movie)→(Genre)`  | —                           |

### Design rationale

A three-label model keeps the schema minimal while enabling every query pattern
needed: user→movie traversal for ratings, movie→genre for content filtering, and
cross-user multi-hop paths for collaborative filtering. Adding `Genre` as a
first-class node (rather than a property list on `Movie`) turns genre affinity
into a graph reachability problem that Cypher expresses in one line.

---

## 4. Queries

### Q1 — Movies rated by a user

Fetches all movies a specific user has rated, ordered by rating descending.
Establishes what a user has already seen before making recommendations.

```cypher
MATCH (u:User {user_id: 1})-[r:RATED]->(m:Movie)
RETURN m.title AS title, m.year AS year, r.rating AS rating
ORDER BY r.rating DESC
```

---

### Q2 — Top movies by genre

Finds the highest-rated movies within a genre, filtered by a minimum vote
threshold to prevent low-sample outliers from dominating.

```cypher
MATCH (m:Movie)-[:IN_GENRE]->(g:Genre {name: 'Action'})
MATCH (m)<-[r:RATED]-(:User)
WITH m, count(r) AS votes, avg(r.rating) AS avg_r
WHERE votes >= 20
RETURN m.title, m.year, round(avg_r, 2) AS avg_rating, votes
ORDER BY avg_r DESC LIMIT 10
```

---

### Q3 — Collaborative filter recommendations

Two-hop traversal: find the 20 users who share the most rated movies with the
target user, then surface movies those neighbours rated ≥ 4 that the target
user hasn't seen yet.

```cypher
MATCH (u1:User {user_id: 1})-[:RATED]->(m:Movie)<-[r2:RATED]-(u2:User)
WHERE u2 <> u1
WITH u2, count(m) AS common ORDER BY common DESC LIMIT 20
MATCH (u2)-[r:RATED]->(rec:Movie)
WHERE NOT EXISTS { MATCH (u1)-[:RATED]->(rec) } AND r.rating >= 4
RETURN rec.title, avg(r.rating) AS avg_score, count(*) AS votes
ORDER BY votes DESC, avg_score DESC LIMIT 10
```

---

### Q4 — Similar-taste users

Pattern matching: finds users who rated the same movies *similarly* (rating
difference ≤ 1) across at least 10 shared films. Returns agreement count and
average disagreement — a more nuanced similarity measure than co-rating alone.

```cypher
MATCH (u:User {user_id: 1})-[r1:RATED]->(m:Movie)<-[r2:RATED]-(other:User)
WHERE abs(r1.rating - r2.rating) <= 1
WITH other, count(m) AS agreement, avg(abs(r1.rating - r2.rating)) AS avg_diff
WHERE agreement >= 10
RETURN other.user_id, other.occupation, agreement, round(avg_diff, 2) AS avg_diff
ORDER BY agreement DESC, avg_diff ASC
```

---

### Q5 — Shortest path between two users

Uses Neo4j's built-in `shortestPath()` to find the minimum hop count connecting
two users through shared movies. A user→movie→user chain is 2 hops. Bounded at
6 hops to prevent full graph traversal. No clean SQL equivalent without
recursive CTEs.

```cypher
MATCH path = shortestPath(
    (u1:User {user_id: 1})-[:RATED*..6]-(u2:User {user_id: 50})
)
RETURN [n IN nodes(path) | CASE WHEN n:User THEN 'User:'+toString(n.user_id)
                                  ELSE 'Movie:'+n.title END] AS path_nodes,
       length(path) AS hops
```

---

### Q6 — Friends-of-friends genre overlap

Three-hop traversal: find peers of the target user, then surface movies those
peers rated in a given genre that the target user hasn't seen. Demonstrates
depth of traversal expressiveness — equivalent to three nested subqueries in SQL.

```cypher
MATCH (u:User {user_id: 1})-[:RATED]->(m:Movie)<-[:RATED]-(peer:User)
WHERE peer <> u
WITH DISTINCT peer
MATCH (peer)-[:RATED]->(m2:Movie)-[:IN_GENRE]->(g:Genre {name: 'Action'})
WHERE NOT EXISTS { MATCH (u)-[:RATED]->(m2) }
RETURN m2.title, count(peer) AS peer_votes
ORDER BY peer_votes DESC LIMIT 10
```

---

### Q7 — Genre-based recommendations

Content filtering rather than collaborative. Identifies the user's top 3
preferred genres (by highly-rated films), then surfaces unseen movies from
those genres ranked by average rating. No user-to-user traversal required.

---

### Q8 — Multi-hop co-rating chain, depth 3

Finds all users reachable from the target user within 3 hops through shared
movies, returning minimum distance. The headline benchmark query.

```cypher
MATCH path = (u:User {user_id: 1})-[:RATED*..3]-(other:User)
WHERE u <> other
WITH other, min(length(path)) AS dist
RETURN other.user_id AS user_id, dist
ORDER BY dist LIMIT 20
```

The SQL equivalent requires three explicit self-joins and cannot generalise to
depth 4 without rewriting the query entirely.

---

### Q9 — Pairwise user overlap

Finds all pairs of users sharing at least 10 rated movies, ranked by overlap
count. A full pairwise scan with no selective entry point — neither engine has
a traversal advantage here.

```cypher
MATCH (u1:User)-[:RATED]->(m:Movie)<-[:RATED]-(u2:User)
WHERE u1.user_id < u2.user_id
WITH u1, u2, count(DISTINCT m) AS shared
WHERE shared >= 10
RETURN u1.user_id AS user1, u2.user_id AS user2, shared
ORDER BY shared DESC LIMIT 10
```

---

## 5. Relational Equivalent

The SQLite model uses three flat tables (`movies`, `users`, `ratings`) with
indexes on `ratings(user_id)` and `ratings(movie_id)`.

### Readability comparison

| Concern                  | Cypher                           | SQL                               |
|--------------------------|----------------------------------|-----------------------------------|
| 2-hop friend discovery   | One `MATCH` pattern              | Two self-joins + subquery         |
| Shortest path            | Built-in `shortestPath()`        | Recursive CTE (complex)           |
| Variable-depth traversal | Change one integer in the query  | Rewrite with additional joins     |
| Pattern negation         | `NOT EXISTS { MATCH … }`         | `NOT IN (SELECT …)` subquery      |
| Schema evolution         | Add label/property, no migration | `ALTER TABLE` or new join table   |

---

## 6. Performance Results

| Query | Neo4j | SQLite | Winner |
|-------|-------|--------|--------|
| Q2 — Top movies by genre | ~138.0 ms | ~30.4 ms | SQLite |
| Q3 — Collaborative filter | ~328.6 ms | ~44.7 ms | SQLite |
| Q8 — Multi-hop chain (depth 3) | ~80.1 ms | ~23 271.0 ms | **Neo4j** |
| Q9 — Pairwise user overlap | ~26 514.0 ms | ~15 079.5 ms | SQLite |

**Key findings:**

**Neo4j wins on traversal.** Q8 is the defining result: ~80.1ms vs ~23 seconds.
The graph engine follows relationship pointers directly; SQL must materialise a
three-level Cartesian product. Increasing traversal depth from 3 to 4 costs
Neo4j one character change; SQL requires an entirely new join level.

**SQLite wins on bulk aggregation.** Q2 and Q9 involve no multi-hop traversal —
just counting and grouping over a large edge set. Relational engines are
optimised for this with columnar scans. Neo4j carries per-relationship pointer
overhead that adds up when no selective entry point exists.

**The honest conclusion** is that the choice of engine should match the dominant
query pattern: graph databases for traversal-heavy workloads, relational engines
for bulk aggregation. A recommendation system skews heavily toward traversal,
making Neo4j the better long-term fit despite the Q9 result.

---

## 7. API and Frontend

The Flask API (`api.py`) exposes all queries as GET endpoints. Every response
includes `rows`, `count`, and `elapsed_ms`.

| Endpoint | Description |
|----------|-------------|
| `/stats` | Node and edge counts |
| `/user/<uid>/ratings` | All ratings for a user |
| `/user/<uid>/recommendations/collaborative` | Collaborative filter recs |
| `/user/<uid>/recommendations/genre` | Genre-affinity recs |
| `/user/<uid>/similar-users` | Users with similar taste |
| `/user/<uid>/peers` | Users who rated same movies |
| `/user/<uid>/fof-genre/<genre>` | Friends-of-friends genre overlap |
| `/genre/<name>/top` | Top-rated movies in a genre |
| `/path?uid1=&uid2=` | Shortest path between two users |

`frontend/index.html` is a self-contained browser UI that calls the API live.
A dropdown selects the query type; input fields update dynamically based on the
selection; results render as a table with row count and elapsed milliseconds.
No build step — open directly in a browser while `python api.py` is running.

---

## 8. Running the Project

```bash
pip install -r requirements.txt
cp .env.example .env       # set NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
python ingest.py           # generate/download data, populate Neo4j
python benchmark.py        # run all 9 queries, print comparison table
python cli.py              # interactive terminal explorer
python api.py              # REST API on :5000 — open frontend/index.html
python dump.py             # export to data/movielens_dump.cypher
```

AuraDB URI format: `neo4j+s://xxxxxxxx.databases.neo4j.io`
Local Docker URI format: `bolt://localhost:7687`

---

## 9. Screenshots

### Graph Visualization

```cypher
MATCH (u:User)-[:RATED]->(m:Movie)-[:IN_GENRE]->(g:Genre) RETURN u,m,g LIMIT 30
```
![Graph](docs/screenshots/graph.png)

### Ingest
![Ingest](docs/screenshots/ingest.png)

### Benchmark
![Benchmark](docs/screenshots/benchmark.png)

### Frontend
![Frontend](docs/screenshots/frontend.png)

### Database dump
![Dump](docs/screenshots/dump.png)


## 10. Conclusions

Graph databases provide a natural fit for recommendation workloads that require
multi-hop traversals and pattern matching. The Q8 result (84ms vs 20 seconds at
depth 3, with SQL complexity growing with each additional hop) is the clearest
demonstration: this class of query is structurally difficult for relational
engines and trivial for a graph engine. Cypher's declarative pattern syntax
keeps complex traversals short and readable, and the property graph schema
evolves without migrations.

The relational model remains competitive — and faster — for simple aggregations
over dense edge sets. A well-designed system would recognise both strengths:
graph traversal for the recommendation and path logic, potentially a relational
store for reporting aggregations over the full dataset.