import os
import zipfile
import random
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ML_URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
ZIP_PATH = os.path.join(DATA_DIR, "ml-latest-small.zip")
ML_DIR = os.path.join(DATA_DIR, "ml-latest-small")

GENRE_NAMES = [
    "Action","Adventure","Animation","Children","Comedy","Crime",
    "Documentary","Drama","Fantasy","Film-Noir","Horror","Musical","Mystery",
    "Romance","Sci-Fi","Thriller","War","Western",
]

OCCUPATIONS = [
    "administrator","artist","doctor","educator","engineer","entertainment",
    "executive","healthcare","homemaker","lawyer","librarian","marketing",
    "none","other","programmer","retired","salesman","scientist","student",
    "technician","writer",
]

SAMPLE_TITLES = [
    "Star Wars","The Godfather","Pulp Fiction","Schindler's List","The Matrix",
    "Forrest Gump","The Shawshank Redemption","Silence of the Lambs","Titanic",
    "Jurassic Park","The Lion King","Toy Story","Braveheart","Se7en","Heat",
    "Casino","GoodFellas","Fight Club","American Beauty","The Usual Suspects",
    "Fargo","L.A. Confidential","Boogie Nights","Trainspotting","Magnolia",
    "Blade Runner","Alien","The Thing","Terminator","RoboCop",
    "Back to the Future","Indiana Jones","Die Hard","Lethal Weapon","Speed",
    "True Lies","Total Recall","Predator","Commando","Rambo",
    "Pretty Woman","Ghost","Sleepless in Seattle","You've Got Mail","Notting Hill",
    "Four Weddings","Bridget Jones","As Good as It Gets","Jerry Maguire","Rain Man",
]


def _synthetic_movies(n=500):
    random.seed(42)
    rows = []
    for i in range(1, n + 1):
        base = SAMPLE_TITLES[(i - 1) % len(SAMPLE_TITLES)]
        title = base if i <= len(SAMPLE_TITLES) else f"{base} {i}"
        year = random.randint(1970, 2000)
        ng = random.randint(1, 3)
        genres = random.sample(GENRE_NAMES, ng)
        rows.append({"movie_id": i, "title": title, "year": year, "genres": genres})
    return pd.DataFrame(rows)


def _synthetic_users(n=943):
    random.seed(7)
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "user_id": i,
            "age": random.randint(15, 70),
            "gender": random.choice(["M", "F"]),
            "occupation": random.choice(OCCUPATIONS),
            "zip": f"{random.randint(10000,99999)}",
        })
    return pd.DataFrame(rows)


def _synthetic_ratings(users, movies, n=100000):
    random.seed(99)
    uid_list = users["user_id"].tolist()
    mid_list = movies["movie_id"].tolist()
    seen = set()
    rows = []
    ts = 880000000
    while len(rows) < n:
        uid = random.choice(uid_list)
        mid = random.choice(mid_list)
        if (uid, mid) in seen:
            continue
        seen.add((uid, mid))
        rows.append({
            "user_id": uid,
            "movie_id": mid,
            "rating": random.randint(1, 5),
            "timestamp": ts + len(rows) * 100,
        })
    return pd.DataFrame(rows)


def download():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(ML_DIR, exist_ok=True)
    item_path = os.path.join(ML_DIR, "u.item")
    user_path = os.path.join(ML_DIR, "u.user")
    data_path = os.path.join(ML_DIR, "u.data")

    if os.path.exists(item_path):
        print("Data already present.")
        return

    if os.path.exists(ZIP_PATH):
        print("Extracting existing zip...")
        with zipfile.ZipFile(ZIP_PATH, "r") as z:
            z.extractall(DATA_DIR)
        if os.path.exists(item_path):
            print("Extracted real MovieLens data.")
            return

    print(f"Real dataset unavailable (download manually from {ML_URL}).")
    print("Generating synthetic MovieLens-shaped dataset (500 movies, 943 users, 100K ratings)...")
    movies = _synthetic_movies(500)
    users  = _synthetic_users(943)
    ratings = _synthetic_ratings(users, movies, 100000)

    genre_cols = {g: 0 for g in GENRE_NAMES}
    item_rows = []
    for _, row in movies.iterrows():
        gc = {g: (1 if g in row["genres"] else 0) for g in GENRE_NAMES}
        item_rows.append({
            "movie_id": row["movie_id"],
            "title": row["title"],
            "release_date": f"01-Jan-{row['year']}",
            "video_release_date": "",
            "imdb_url": "",
            **gc,
        })
    item_df = pd.DataFrame(item_rows)
    cols = ["movie_id","title","release_date","video_release_date","imdb_url"] + GENRE_NAMES
    item_df[cols].to_csv(item_path, sep="|", index=False, header=False)

    users[["user_id","age","gender","occupation","zip"]].to_csv(
        user_path, sep="|", index=False, header=False)

    ratings[["user_id","movie_id","rating","timestamp"]].to_csv(
        data_path, sep="\t", index=False, header=False)

    print("Synthetic data written.")


def load_movies():
    path = os.path.join(ML_DIR, "u.item")
    cols = ["movie_id","title","release_date","video_release_date","imdb_url"] + GENRE_NAMES
    df = pd.read_csv(path, sep="|", names=cols, encoding="latin-1")
    df["year"] = df["release_date"].str.extract(r"(\d{4})").fillna("0").astype(int)
    df["genres"] = df[GENRE_NAMES].apply(
        lambda row: [g for g, v in zip(GENRE_NAMES, row) if v == 1], axis=1
    )
    return df[["movie_id", "title", "year", "genres"]]


def load_users():
    path = os.path.join(ML_DIR, "u.user")
    df = pd.read_csv(path, sep="|", names=["user_id","age","gender","occupation","zip"])
    return df


def load_ratings():
    path = os.path.join(ML_DIR, "u.data")
    df = pd.read_csv(path, sep="\t", names=["user_id","movie_id","rating","timestamp"])
    return df


if __name__ == "__main__":
    download()
    movies = load_movies()
    users = load_users()
    ratings = load_ratings()
    print(f"Movies: {len(movies)}, Users: {len(users)}, Ratings: {len(ratings)}")
    print(movies.head(3).to_string())
    print(users.head(3).to_string())
    print(ratings.head(3).to_string())
