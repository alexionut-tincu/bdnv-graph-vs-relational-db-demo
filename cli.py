from tabulate import tabulate
import queries as gq
from db import verify


MENU = """
MovieLens Graph Explorer
  1  Movies rated by a user
  2  Collaborative filter recommendations
  3  Genre-based recommendations
  4  Similar-taste users
  5  Peers (users who rated same movies)
  6  Top movies in a genre
  7  Shortest path between two users
  8  Friends-of-friends genre overlap
  9  Graph statistics
  0  Exit
"""


def fmt(rows, ms):
    print(f"  ({len(rows)} rows, {ms:.1f} ms)\n")
    print(tabulate(rows[:15], headers="keys", tablefmt="simple"))


def main():
    verify()
    while True:
        print(MENU)
        choice = input("Choice: ").strip()
        try:
            if choice == "0":
                break
            elif choice == "1":
                uid = int(input("User ID: "))
                fmt(*gq.movies_rated_by_user(uid))
            elif choice == "2":
                uid   = int(input("User ID: "))
                top_n = int(input("Top N [10]: ") or 10)
                fmt(*gq.collaborative_filter_recommendations(uid, top_n))
            elif choice == "3":
                uid   = int(input("User ID: "))
                top_n = int(input("Top N [10]: ") or 10)
                fmt(*gq.genre_based_recommendations(uid, top_n))
            elif choice == "4":
                uid = int(input("User ID: "))
                fmt(*gq.similar_taste_users(uid))
            elif choice == "5":
                uid = int(input("User ID: "))
                mc  = int(input("Min common ratings [5]: ") or 5)
                fmt(*gq.users_who_rated_same_movies(uid, mc))
            elif choice == "6":
                genre = input("Genre (e.g. Action, Drama): ").strip()
                top_n = int(input("Top N [10]: ") or 10)
                fmt(*gq.top_movies_by_genre(genre, top_n=top_n))
            elif choice == "7":
                u1 = int(input("User ID 1: "))
                u2 = int(input("User ID 2: "))
                rows, ms = gq.shortest_path_between_users(u1, u2)
                print(f"  ({ms:.1f} ms)")
                if rows:
                    print("  Hops:", rows[0]["hops"])
                    print("  Path:", " → ".join(rows[0]["path_nodes"]))
                else:
                    print("  No path found.")
            elif choice == "8":
                uid   = int(input("User ID: "))
                genre = input("Genre: ").strip()
                fmt(*gq.friends_of_friends_genre_overlap(uid, genre))
            elif choice == "9":
                stats = gq.graph_stats()
                print(tabulate(stats, headers="keys", tablefmt="rounded_outline"))
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
