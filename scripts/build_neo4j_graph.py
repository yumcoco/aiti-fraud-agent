"""
Build Neo4j fraud graph — initial load (last 30 days only).
Simulates historical data migration at system launch.
Run once: python scripts/build_neo4j_graph.py
"""
import pandas as pd
from neo4j import GraphDatabase
from pathlib import Path

ROOT = Path(__file__).parent.parent
PAYSIM_PATH = ROOT / "data" / "paysim" / "PS_20174392719_1491204439457_log.csv"
DEVICE_PATH = ROOT / "data" / "synthetic" / "account_device_ip.csv"

NEO4J_URI  = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "fraud2026"

BATCH_SIZE = 5000
RECENT_STEPS = 720


def batch_run(driver, query, rows, label=""):
    with driver.session() as s:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i:i + BATCH_SIZE]
            s.run(query, {"rows": batch})
            print(f"  {label}: {min(i+BATCH_SIZE, len(rows))}/{len(rows)}", end="\r")
    print()


def run_graph_algorithms(driver):
    print("Running graph algorithms...")
    with driver.session() as s:
        try:
            s.run("CALL gds.graph.drop('fraud_graph') YIELD graphName")
            print("  Dropped existing fraud_graph")
        except Exception:
            pass

        print("  Projecting graph...")
        result = s.run("""
            CALL gds.graph.project(
                'fraud_graph',
                'Account',
                {TRANSFERS_TO: {orientation: 'UNDIRECTED'}}
            )
            YIELD graphName, nodeCount, relationshipCount
        """).single()
        print(f"  Projected: {result['nodeCount']} nodes, {result['relationshipCount']} edges")

        print("  Louvain community detection...")
        result = s.run("""
            CALL gds.louvain.write('fraud_graph', {writeProperty: 'community_id'})
            YIELD communityCount, modularity
        """).single()
        print(f"  Communities: {result['communityCount']}, modularity: {result['modularity']:.4f}")

        print("  PageRank...")
        result = s.run("""
            CALL gds.pageRank.write('fraud_graph', {writeProperty: 'pagerank'})
            YIELD nodePropertiesWritten
        """).single()
        print(f"  PageRank written: {result['nodePropertiesWritten']}")

        s.run("CALL gds.graph.drop('fraud_graph') YIELD graphName")
    print("  Graph algorithms complete")


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    print("Connected to Neo4j")

    print("Creating constraints...")
    with driver.session() as s:
        s.run("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE")
        s.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Device) REQUIRE d.device_id IS UNIQUE")
        s.run("CREATE CONSTRAINT IF NOT EXISTS FOR (ip:IPAddress) REQUIRE ip.address IS UNIQUE")

    print("Loading PaySim (last 30 days)...")
    paysim = pd.read_csv(PAYSIM_PATH,
                         usecols=["step", "type", "nameOrig",
                                  "nameDest", "amount", "isFraud"])
    max_step = paysim["step"].max()
    recent = paysim[
        (paysim["step"] >= max_step - RECENT_STEPS) &
        (paysim["type"].isin(["TRANSFER", "CASH_OUT"])) &
        (paysim["nameOrig"].str.startswith("C"))
    ].copy()
    print(f"  Recent transactions: {len(recent)} (from {len(paysim)} total)")
    print(f"  Fraud in recent: {recent['isFraud'].sum()}")

    print("Loading device/IP data...")
    device_df = pd.read_csv(DEVICE_PATH)
    recent_accounts = set(recent["nameOrig"].tolist()) | set(recent["nameDest"].tolist())
    device_df = device_df[device_df["account_id"].isin(recent_accounts)]
    print(f"  Relevant accounts: {len(device_df)}")

    print("Creating Account + Device + IP nodes...")
    rows = device_df[["account_id", "device_id",
                       "ip_address", "country"]].to_dict("records")
    batch_run(driver, """
        UNWIND $rows AS row
        MERGE (a:Account {id: row.account_id})
        MERGE (d:Device {device_id: row.device_id})
        MERGE (ip:IPAddress {address: row.ip_address})
        ON CREATE SET ip.country = row.country
        MERGE (a)-[:USES_DEVICE]->(d)
        MERGE (a)-[:ORIGINATES_FROM]->(ip)
    """, rows, "nodes")

    print("Creating TRANSFERS_TO edges...")
    rows = recent.rename(columns={
        "nameOrig": "src",
        "nameDest": "dst",
    })[["src", "dst", "amount", "isFraud"]].to_dict("records")
    batch_run(driver, """
        UNWIND $rows AS row
        MERGE (a:Account {id: row.src})
        MERGE (b:Account {id: row.dst})
        MERGE (a)-[:TRANSFERS_TO {amount: row.amount, is_fraud: row.isFraud}]->(b)
    """, rows, "edges")

    run_graph_algorithms(driver)

    print("\nVerifying...")
    with driver.session() as s:
        accounts = s.run("MATCH (a:Account) RETURN count(a) AS n").single()["n"]
        with_community = s.run(
            "MATCH (a:Account) WHERE a.community_id IS NOT NULL RETURN count(a) AS n"
        ).single()["n"]
        devices = s.run("MATCH (d:Device) RETURN count(d) AS n").single()["n"]
        edges = s.run("MATCH ()-[r:TRANSFERS_TO]->() RETURN count(r) AS n").single()["n"]

    print(f"  Accounts:      {accounts:,}")
    print(f"  Devices:       {devices:,}")
    print(f"  Transfer edges:{edges:,}")
    print(f"  With community:{with_community:,}")

    driver.close()
    print("\nDone — initial graph loaded (30-day window)")


if __name__ == "__main__":
    main()