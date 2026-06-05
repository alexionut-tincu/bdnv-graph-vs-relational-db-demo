import sqlite3
import time
import os
import pandas as pd
from data_prep import load_movies, load_users, load_ratings, download

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "movielens.db")


def build_sqlite():
    download()
    movies  = load_movies()
    users   = load_users()
    ratings = load_ratings()

    conn = sqlite3.connect(DB_PATH)
    movies_flat = movies.copy()
    movies_flat["genres"] = movies_flat["genres"].apply("|".join)
    movies_flat.to_sql("movies",  conn, if_exists="replace", index=False)
    users.to_sql("users",   conn, if_exists="replace", index=False)
    ratings.to_sql("ratings", conn, if_exists="replace", index=False)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_r_user   ON ratings(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_r_movie  ON ratings(movie_id)")
    conn.commit()
    conn.close()
    print(f"SQLite DB built at {DB_PATH}")


def _timed_sql(conn, sql, params=()):
    t0 = time.perf_counter()
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    elapsed = (time.perf_counter() - t0) * 1000
    return rows, elapsed


def collab_filter_sql(user_id, top_n=10):
    conn = sqlite3.connect(DB_PATH)
    sql = """
    WITH peer_movies AS (
        SELECT r2.movie_id, COUNT(*) AS common
        FROM ratings r1
        JOIN ratings r2 ON r1.movie_id = r2.movie_id AND r1.user_id != r2.user_id
        WHERE r1.user_id = ?
        GROUP BY r2.user_id
        ORDER BY common DESC
        LIMIT 20
    ),
    candidates AS (
        SELECT r.movie_id, AVG(r.rating) AS avg_score, COUNT(*) AS votes
        FROM ratings r
        JOIN peer_movies pm ON r.movie_id = pm.movie_id
        WHERE r.rating >= 4
          AND r.movie_id NOT IN (SELECT movie_id FROM ratings WHERE user_id = ?)
        GROUP BY r.movie_id
    )
    SELECT m.title, m.year, c.avg_score, c.votes
    FROM candidates c JOIN movies m ON c.movie_id = m.movie_id
    ORDER BY c.votes DESC, c.avg_score DESC
    LIMIT ?
    """
    rows, elapsed = _timed_sql(conn, sql, (user_id, user_id, top_n))
    conn.close()
    return rows, elapsed


def top_movies_genre_sql(genre, min_votes=20, top_n=10):
    conn = sqlite3.connect(DB_PATH)
    sql = """
    SELECT m.title, m.year, ROUND(AVG(r.rating),2) AS avg_rating, COUNT(*) AS votes
    FROM movies m JOIN ratings r ON m.movie_id = r.movie_id
    WHERE m.genres LIKE ?
    GROUP BY m.movie_id
    HAVING votes >= ?
    ORDER BY avg_rating DESC
    LIMIT ?
    """
    rows, elapsed = _timed_sql(conn, sql, (f"%{genre}%", min_votes, top_n))
    conn.close()
    return rows, elapsed


def multi_hop_corating_sql(user_id, depth=3):
    conn = sqlite3.connect(DB_PATH)
    # SQL can only do this with repeated self-joins; depth=3 means 3 explicit joins
    sql = """
    WITH hop1 AS (
        SELECT DISTINCT r2.user_id AS peer
        FROM ratings r1
        JOIN ratings r2 ON r1.movie_id = r2.movie_id AND r2.user_id != r1.user_id
        WHERE r1.user_id = ?
    ),
    hop2 AS (
        SELECT DISTINCT r3.user_id AS peer
        FROM hop1
        JOIN ratings r2 ON r2.user_id = hop1.peer
        JOIN ratings r3 ON r2.movie_id = r3.movie_id AND r3.user_id != r2.user_id
        WHERE r3.user_id != ?
    ),
    hop3 AS (
        SELECT DISTINCT r4.user_id AS peer
        FROM hop2
        JOIN ratings r3 ON r3.user_id = hop2.peer
        JOIN ratings r4 ON r3.movie_id = r4.movie_id AND r4.user_id != r3.user_id
        WHERE r4.user_id != ?
    )
    SELECT peer, 3 AS dist FROM hop3
    UNION SELECT peer, 2 AS dist FROM hop2
    UNION SELECT peer, 1 AS dist FROM hop1
    ORDER BY dist LIMIT 20
    """
    rows, elapsed = _timed_sql(conn, sql, (user_id, user_id, user_id))
    conn.close()
    return rows, elapsed


def triangle_detection_sql():
    conn = sqlite3.connect(DB_PATH)
    sql = """
    SELECT r1.user_id AS user1, r2.user_id AS user2, COUNT(DISTINCT r1.movie_id) AS shared
    FROM ratings r1
    JOIN ratings r2 ON r1.movie_id = r2.movie_id AND r1.user_id < r2.user_id
    GROUP BY r1.user_id, r2.user_id
    HAVING shared >= 10
    ORDER BY shared DESC
    LIMIT 10
    """
    rows, elapsed = _timed_sql(conn, sql, ())
    conn.close()
    return rows, elapsed


if __name__ == "__main__":
    build_sqlite()
