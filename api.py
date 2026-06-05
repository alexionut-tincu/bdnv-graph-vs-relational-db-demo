from flask import Flask, jsonify, request, abort
from flask_cors import CORS
import queries as gq

app = Flask(__name__)
CORS(app)


def _ok(rows, ms, label=None):
    payload = {"rows": rows, "count": len(rows), "elapsed_ms": round(ms, 2)}
    if label:
        payload["label"] = label
    return jsonify(payload)


@app.get("/stats")
def stats():
    data = gq.graph_stats()
    return jsonify(data)


@app.get("/user/<int:uid>/ratings")
def user_ratings(uid):
    rows, ms = gq.movies_rated_by_user(uid)
    return _ok(rows, ms)


@app.get("/user/<int:uid>/similar-users")
def similar_users(uid):
    rows, ms = gq.similar_taste_users(uid)
    return _ok(rows, ms)


@app.get("/user/<int:uid>/recommendations/collaborative")
def collab_recs(uid):
    top_n = request.args.get("top_n", 10, type=int)
    rows, ms = gq.collaborative_filter_recommendations(uid, top_n)
    return _ok(rows, ms, label="collaborative")


@app.get("/user/<int:uid>/recommendations/genre")
def genre_recs(uid):
    top_n = request.args.get("top_n", 10, type=int)
    rows, ms = gq.genre_based_recommendations(uid, top_n)
    return _ok(rows, ms, label="genre")


@app.get("/user/<int:uid>/peers")
def peers(uid):
    min_common = request.args.get("min_common", 5, type=int)
    rows, ms = gq.users_who_rated_same_movies(uid, min_common)
    return _ok(rows, ms)


@app.get("/genre/<name>/top")
def top_genre(name):
    min_votes = request.args.get("min_votes", 20, type=int)
    top_n     = request.args.get("top_n",     10, type=int)
    rows, ms  = gq.top_movies_by_genre(name, min_votes, top_n)
    return _ok(rows, ms)


@app.get("/path")
def path():
    uid1 = request.args.get("uid1", type=int)
    uid2 = request.args.get("uid2", type=int)
    if uid1 is None or uid2 is None:
        abort(400, "uid1 and uid2 required")
    rows, ms = gq.shortest_path_between_users(uid1, uid2)
    return _ok(rows, ms)


@app.get("/user/<int:uid>/fof-genre/<genre>")
def fof_genre(uid, genre):
    rows, ms = gq.friends_of_friends_genre_overlap(uid, genre)
    return _ok(rows, ms)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
