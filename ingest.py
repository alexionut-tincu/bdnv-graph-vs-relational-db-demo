import time
from db import run_query, verify
from data_prep import download, load_movies, load_users, load_ratings

BATCH = 500


def clear_db():
    run_query("MATCH (n) DETACH DELETE n")
    print("Database cleared.")


def create_constraints():
    run_query("CREATE CONSTRAINT movie_id IF NOT EXISTS FOR (m:Movie) REQUIRE m.movie_id IS UNIQUE")
    run_query("CREATE CONSTRAINT user_id  IF NOT EXISTS FOR (u:User)  REQUIRE u.user_id  IS UNIQUE")
    run_query("CREATE CONSTRAINT genre_name IF NOT EXISTS FOR (g:Genre) REQUIRE g.name IS UNIQUE")
    print("Constraints ready.")


def ingest_movies(movies):
    records = movies.to_dict("records")
    for i in range(0, len(records), BATCH):
        batch = records[i:i+BATCH]
        run_query(
            """
            UNWIND $rows AS row
            MERGE (m:Movie {movie_id: row.movie_id})
            SET m.title = row.title, m.year = row.year
            WITH m, row
            UNWIND row.genres AS gname
            MERGE (g:Genre {name: gname})
            MERGE (m)-[:IN_GENRE]->(g)
            """,
            {"rows": batch},
        )
    print(f"Ingested {len(records)} movies.")


def ingest_users(users):
    records = users.to_dict("records")
    for i in range(0, len(records), BATCH):
        batch = records[i:i+BATCH]
        run_query(
            """
            UNWIND $rows AS row
            MERGE (u:User {user_id: row.user_id})
            SET u.age = row.age, u.gender = row.gender, u.occupation = row.occupation
            """,
            {"rows": batch},
        )
    print(f"Ingested {len(records)} users.")


def ingest_ratings(ratings):
    records = ratings.to_dict("records")
    total = len(records)
    for i in range(0, total, BATCH):
        batch = records[i:i+BATCH]
        run_query(
            """
            UNWIND $rows AS row
            MATCH (u:User  {user_id:  row.user_id})
            MATCH (m:Movie {movie_id: row.movie_id})
            MERGE (u)-[r:RATED]->(m)
            SET r.rating = row.rating, r.timestamp = row.timestamp
            """,
            {"rows": batch},
        )
    print(f"Ingested {total} ratings.")


def build_cosine_similarity():
    run_query(
        """
        MATCH (u:User)-[r:RATED]->(m:Movie)
        WITH m, avg(r.rating) AS avg_rating
        SET m.avg_rating = avg_rating
        """
    )
    print("Average ratings set on Movie nodes.")


def run_ingestion():
    verify()
    download()
    movies  = load_movies()
    users   = load_users()
    ratings = load_ratings()

    clear_db()
    create_constraints()

    t0 = time.time()
    ingest_movies(movies)
    ingest_users(users)
    ingest_ratings(ratings)
    build_cosine_similarity()
    print(f"Total ingestion time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    run_ingestion()
