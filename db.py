import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "neo4j")
        _driver = GraphDatabase.driver(uri, auth=(user, password))
    return _driver


def run_query(cypher, params=None):
    driver = get_driver()
    with driver.session() as session:
        result = session.run(cypher, params or {})
        return [record.data() for record in result]


def close():
    global _driver
    if _driver:
        _driver.close()
        _driver = None


def verify():
    driver = get_driver()
    driver.verify_connectivity()
    print("Neo4j connection OK")
