import time
from db import run_query


def _timed(fn, *args, **kwargs):
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed = (time.perf_counter() - t0) * 1000
    return result, elapsed


def movies_rated_by_user(user_id):
    q = """
    MATCH (u:User {user_id: $uid})-[r:RATED]->(m:Movie)
    RETURN m.title AS title, m.year AS year, r.rating AS rating
    ORDER BY r.rating DESC
    """
    return _timed(run_query, q, {"uid": user_id})


def users_who_rated_same_movies(user_id, min_common=5):
    q = """
    MATCH (u1:User {user_id: $uid})-[:RATED]->(m:Movie)<-[:RATED]-(u2:User)
    WHERE u1 <> u2
    WITH u2, count(m) AS common
    WHERE common >= $min_common
    RETURN u2.user_id AS user_id, u2.occupation AS occupation, common
    ORDER BY common DESC
    LIMIT 10
    """
    return _timed(run_query, q, {"uid": user_id, "min_common": min_common})


def collaborative_filter_recommendations(user_id, top_n=10):
    q = """
    MATCH (u1:User {user_id: $uid})-[:RATED]->(m:Movie)<-[r2:RATED]-(u2:User)
    WHERE u2 <> u1
    WITH u2, count(m) AS common
    ORDER BY common DESC
    LIMIT 20
    MATCH (u2)-[r:RATED]->(rec:Movie)
    WHERE NOT EXISTS { MATCH (u1)-[:RATED]->(rec) }
      AND r.rating >= 4
    RETURN rec.title AS title, rec.year AS year,
           avg(r.rating) AS avg_score, count(*) AS votes
    ORDER BY votes DESC, avg_score DESC
    LIMIT $top_n
    """
    return _timed(run_query, q, {"uid": user_id, "top_n": top_n})


def genre_based_recommendations(user_id, top_n=10):
    q = """
    MATCH (u:User {user_id: $uid})-[r:RATED]->(m:Movie)-[:IN_GENRE]->(g:Genre)
    WHERE r.rating >= 4
    WITH g, count(*) AS pref ORDER BY pref DESC LIMIT 3
    MATCH (g)<-[:IN_GENRE]-(rec:Movie)
    WHERE NOT EXISTS { MATCH (:User {user_id: $uid})-[:RATED]->(rec) }
    RETURN rec.title AS title, rec.year AS year,
           collect(DISTINCT g.name) AS genres,
           rec.avg_rating AS avg_rating
    ORDER BY rec.avg_rating DESC
    LIMIT $top_n
    """
    return _timed(run_query, q, {"uid": user_id, "top_n": top_n})


def top_movies_by_genre(genre, min_votes=20, top_n=10):
    q = """
    MATCH (m:Movie)-[:IN_GENRE]->(g:Genre {name: $genre})
    MATCH (m)<-[r:RATED]-(:User)
    WITH m, count(r) AS votes, avg(r.rating) AS avg_r
    WHERE votes >= $min_votes
    RETURN m.title AS title, m.year AS year,
           round(avg_r, 2) AS avg_rating, votes
    ORDER BY avg_r DESC
    LIMIT $top_n
    """
    return _timed(run_query, q, {"genre": genre, "min_votes": min_votes, "top_n": top_n})


def shortest_path_between_users(uid1, uid2):
    q = """
    MATCH path = shortestPath(
        (u1:User {user_id: $uid1})-[:RATED*..6]-(u2:User {user_id: $uid2})
    )
    RETURN [n IN nodes(path) | CASE WHEN n:User THEN 'User:'+toString(n.user_id)
                                     ELSE 'Movie:'+n.title END] AS path_nodes,
           length(path) AS hops
    """
    return _timed(run_query, q, {"uid1": uid1, "uid2": uid2})


def friends_of_friends_genre_overlap(user_id, genre):
    q = """
    MATCH (u:User {user_id: $uid})-[:RATED]->(m:Movie)<-[:RATED]-(peer:User)
    WHERE peer <> u
    WITH DISTINCT peer
    MATCH (peer)-[:RATED]->(m2:Movie)-[:IN_GENRE]->(g:Genre {name: $genre})
    WHERE NOT EXISTS { MATCH (u)-[:RATED]->(m2) }
    RETURN m2.title AS title, count(peer) AS peer_votes,
           avg(m2.avg_rating) AS avg_rating
    ORDER BY peer_votes DESC
    LIMIT 10
    """
    return _timed(run_query, q, {"uid": user_id, "genre": genre})


def similar_taste_users(user_id):
    q = """
    MATCH (u:User {user_id: $uid})-[r1:RATED]->(m:Movie)<-[r2:RATED]-(other:User)
    WHERE abs(r1.rating - r2.rating) <= 1
    WITH other, count(m) AS agreement, avg(abs(r1.rating - r2.rating)) AS avg_diff
    WHERE agreement >= 10
    RETURN other.user_id AS user_id, other.occupation AS occupation,
           agreement, round(avg_diff, 2) AS avg_diff
    ORDER BY agreement DESC, avg_diff ASC
    LIMIT 10
    """
    return _timed(run_query, q, {"uid": user_id})


def graph_stats():
    q = """
    CALL {
        MATCH (n:Movie) RETURN 'Movie' AS label, count(n) AS count
        UNION ALL
        MATCH (n:User)  RETURN 'User'  AS label, count(n) AS count
        UNION ALL
        MATCH (n:Genre) RETURN 'Genre' AS label, count(n) AS count
        UNION ALL
        MATCH ()-[r:RATED]-()     RETURN 'RATED'     AS label, count(r) AS count
        UNION ALL
        MATCH ()-[r:IN_GENRE]-()  RETURN 'IN_GENRE'  AS label, count(r) AS count
    }
    RETURN label, count
    ORDER BY count DESC
    """
    return run_query(q)



def multi_hop_corating_chain(user_id, depth=3):
    q = f"""
    MATCH path = (u:User {{user_id: $uid}})-[:RATED*..{depth}]-(other:User)
    WHERE u <> other
    WITH other, min(length(path)) AS dist
    RETURN other.user_id AS user_id, dist
    ORDER BY dist
    LIMIT 20
    """
    return _timed(run_query, q, {"uid": user_id})


def triangle_detection():
    q = """
    MATCH (u1:User)-[:RATED]->(m:Movie)<-[:RATED]-(u2:User)
    WHERE u1.user_id < u2.user_id
    WITH u1, u2, count(DISTINCT m) AS shared
    WHERE shared >= 10
    RETURN u1.user_id AS user1, u2.user_id AS user2, shared
    ORDER BY shared DESC
    LIMIT 10
    """
    return _timed(run_query, q, {})