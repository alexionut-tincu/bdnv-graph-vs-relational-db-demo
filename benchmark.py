from tabulate import tabulate
import queries as gq
import relational as rq

USER_ID   = 1
GENRE     = "Action"
MIN_VOTES = 20
TOP_N     = 10


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def run():
    section("GRAPH DATABASE STATS")
    stats = gq.graph_stats()
    print(tabulate(stats, headers="keys", tablefmt="rounded_outline"))

    section("Q1 — Movies rated by user (graph)")
    rows, ms = gq.movies_rated_by_user(USER_ID)
    print(f"  Returned {len(rows)} rows in {ms:.1f} ms")
    print(tabulate(rows[:5], headers="keys", tablefmt="simple"))

    section("Q2 — Top movies in genre: graph vs SQL")
    g_rows, g_ms = gq.top_movies_by_genre(GENRE, MIN_VOTES, TOP_N)
    s_rows, s_ms = rq.top_movies_genre_sql(GENRE, MIN_VOTES, TOP_N)
    print(f"  Neo4j  : {len(g_rows)} rows, {g_ms:.1f} ms")
    print(f"  SQLite : {len(s_rows)} rows, {s_ms:.1f} ms")
    print("\n  Neo4j results:")
    print(tabulate(g_rows, headers="keys", tablefmt="simple"))

    section("Q3 — Collaborative filter: graph vs SQL")
    g_rows, g_ms = gq.collaborative_filter_recommendations(USER_ID, TOP_N)
    s_rows, s_ms = rq.collab_filter_sql(USER_ID, TOP_N)
    print(f"  Neo4j  : {len(g_rows)} rows, {g_ms:.1f} ms")
    print(f"  SQLite : {len(s_rows)} rows, {s_ms:.1f} ms")
    print("\n  Neo4j recommendations for user", USER_ID, ":")
    print(tabulate(g_rows[:5], headers="keys", tablefmt="simple"))

    section("Q4 — Similar taste users (graph only)")
    rows, ms = gq.similar_taste_users(USER_ID)
    print(f"  {len(rows)} similar users found in {ms:.1f} ms")
    print(tabulate(rows, headers="keys", tablefmt="simple"))

    section("Q5 — Shortest path between users 1 and 50")
    rows, ms = gq.shortest_path_between_users(1, 50)
    print(f"  Found in {ms:.1f} ms")
    if rows:
        print(f"  Hops   : {rows[0]['hops']}")
        print(f"  Path   : {' → '.join(rows[0]['path_nodes'])}")
    else:
        print("  No path found.")

    section("Q6 — Friends-of-friends genre overlap (graph only)")
    rows, ms = gq.friends_of_friends_genre_overlap(USER_ID, GENRE)
    print(f"  {len(rows)} candidate films in {ms:.1f} ms")
    print(tabulate(rows[:5], headers="keys", tablefmt="simple"))

    section("Q7 — Genre-based recommendations (graph only)")
    rows, ms = gq.genre_based_recommendations(USER_ID, TOP_N)
    print(f"  {len(rows)} films in {ms:.1f} ms")
    print(tabulate(rows[:5], headers="keys", tablefmt="simple"))

    section("Q8 — Multi-hop co-rating chain (depth 3): graph vs SQL")
    g_rows, g_ms3 = gq.multi_hop_corating_chain(USER_ID, depth=3)
    s_rows, s_ms3 = rq.multi_hop_corating_sql(USER_ID, depth=3)
    print(f"  Neo4j  : {len(g_rows)} rows, {g_ms3:.1f} ms")
    print(f"  SQLite : {len(s_rows)} rows, {s_ms3:.1f} ms")

    section("Q9 — Triangle detection: graph vs SQL")
    g_rows, g_ms4 = gq.triangle_detection()
    s_rows, s_ms4 = rq.triangle_detection_sql()
    print(f"  Neo4j  : {len(g_rows)} rows, {g_ms4:.1f} ms")
    print(f"  SQLite : {len(s_rows)} rows, {s_ms4:.1f} ms")


    section("BENCHMARK SUMMARY")
    summary = [
        ["Top movies by genre",   f"{g_ms:.1f} ms", f"{s_ms:.1f} ms"],
    ]
    g2, g_ms2 = gq.collaborative_filter_recommendations(USER_ID, TOP_N)
    s2, s_ms2 = rq.collab_filter_sql(USER_ID, TOP_N)
    summary.append(["Collab filter recs", f"{g_ms2:.1f} ms", f"{s_ms2:.1f} ms"])
    summary.append(["Multi-hop chain (depth 3)", f"{g_ms3:.1f} ms", f"{s_ms3:.1f} ms"])
    summary.append(["Triangle detection",        f"{g_ms4:.1f} ms", f"{s_ms4:.1f} ms"])
    print(tabulate(summary, headers=["Query", "Neo4j", "SQLite"], tablefmt="rounded_outline"))



if __name__ == "__main__":
    rq.build_sqlite()
    run()
