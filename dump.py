import os
from db import run_query

OUT_DIR   = os.path.join(os.path.dirname(__file__), "data")
OUT_PATH  = os.path.join(OUT_DIR, "movielens_dump.cypher")
BATCH     = 500


def dump():
    os.makedirs(OUT_DIR, exist_ok=True)
    lines = []

    lines.append("// MovieLens 100K — Neo4j dump\n")
    lines.append("// Constraints\n")
    lines.append("CREATE CONSTRAINT movie_id IF NOT EXISTS FOR (m:Movie) REQUIRE m.movie_id IS UNIQUE;\n")
    lines.append("CREATE CONSTRAINT user_id  IF NOT EXISTS FOR (u:User)  REQUIRE u.user_id  IS UNIQUE;\n")
    lines.append("CREATE CONSTRAINT genre_name IF NOT EXISTS FOR (g:Genre) REQUIRE g.name IS UNIQUE;\n\n")

    genres = run_query("MATCH (g:Genre) RETURN g.name AS name ORDER BY g.name")
    lines.append("// Genre nodes\n")
    for g in genres:
        lines.append(f"MERGE (:Genre {{name: '{g['name']}'}});\n")
    lines.append("\n")

    skip = 0
    lines.append("// Movie nodes\n")
    while True:
        batch = run_query(
            "MATCH (m:Movie) RETURN m.movie_id AS id, m.title AS title, m.year AS year, m.avg_rating AS avg ORDER BY m.movie_id SKIP $s LIMIT $l",
            {"s": skip, "l": BATCH}
        )
        if not batch:
            break
        for m in batch:
            title = m['title'].replace("'", "\\'")
            avg   = m['avg'] or 0
            lines.append(f"MERGE (:Movie {{movie_id:{m['id']}, title:'{title}', year:{m['year']}, avg_rating:{round(avg,2)}}});\n")
        skip += BATCH
    lines.append("\n")

    skip = 0
    lines.append("// User nodes\n")
    while True:
        batch = run_query(
            "MATCH (u:User) RETURN u.user_id AS id, u.age AS age, u.gender AS gender, u.occupation AS occ ORDER BY u.user_id SKIP $s LIMIT $l",
            {"s": skip, "l": BATCH}
        )
        if not batch:
            break
        for u in batch:
            lines.append(f"MERGE (:User {{user_id:{u['id']}, age:{u['age']}, gender:'{u['gender']}', occupation:'{u['occ']}'}});\n")
        skip += BATCH
    lines.append("\n")

    skip = 0
    lines.append("// IN_GENRE relationships\n")
    while True:
        batch = run_query(
            "MATCH (m:Movie)-[:IN_GENRE]->(g:Genre) RETURN m.movie_id AS mid, g.name AS gname SKIP $s LIMIT $l",
            {"s": skip, "l": BATCH}
        )
        if not batch:
            break
        for r in batch:
            lines.append(f"MATCH (m:Movie {{movie_id:{r['mid']}}}),(g:Genre {{name:'{r['gname']}'}}) MERGE (m)-[:IN_GENRE]->(g);\n")
        skip += BATCH
    lines.append("\n")

    skip = 0
    lines.append("// RATED relationships\n")
    while True:
        batch = run_query(
            "MATCH (u:User)-[r:RATED]->(m:Movie) RETURN u.user_id AS uid, m.movie_id AS mid, r.rating AS rating SKIP $s LIMIT $l",
            {"s": skip, "l": BATCH}
        )
        if not batch:
            break
        for r in batch:
            lines.append(f"MATCH (u:User {{user_id:{r['uid']}}}),(m:Movie {{movie_id:{r['mid']}}}) MERGE (u)-[:RATED {{rating:{r['rating']}}}]->(m);\n")
        skip += BATCH

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"Dump written to {OUT_PATH} ({len(lines)} statements)")


if __name__ == "__main__":
    dump()
