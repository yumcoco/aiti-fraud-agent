from typing import Optional
from neo4j import GraphDatabase
from backend.config import neo4j as neo4j_config
from backend.logger import get_logger

log = get_logger()

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            neo4j_config["uri"],
            auth=(neo4j_config["user"], neo4j_config["password"])
        )
    return _driver


def close_driver():
    global _driver
    if _driver:
        _driver.close()
        _driver = None


def query_account_network(account_id: str, hop_depth: int = 2) -> Optional[dict]:
    try:
        driver = get_driver()
        with driver.session() as session:

            # 查询1：两跳内关联账户
            related = session.run(f"""
                MATCH (a:Account {{id: $account_id}})-[*1..{hop_depth}]-(related:Account)
                WHERE related.id <> $account_id
                RETURN DISTINCT
                    related.id AS related_id,
                    related.community_id AS community_id,
                    related.pagerank AS centrality
                ORDER BY centrality DESC
                LIMIT $limit
            """, account_id=account_id, limit=20).data()

            # 查询2：共享设备
            devices = session.run("""
                MATCH (a:Account {id: $account_id})-[:USES_DEVICE]->(d:Device)
                      <-[:USES_DEVICE]-(other:Account)
                WHERE other.id <> $account_id
                RETURN
                    d.device_id AS device_id,
                    collect(other.id) AS accounts_sharing,
                    count(other) AS share_count
            """, account_id=account_id).data()

            # 查询3：节点自身属性
            node = session.run("""
                MATCH (a:Account {id: $account_id})
                RETURN a.community_id AS community_id, a.pagerank AS pagerank
            """, account_id=account_id).single()

            community_id = node["community_id"] if node else None
            pagerank = float(node["pagerank"]) if node and node["pagerank"] else 0.0
            high_centrality = sum(1 for r in related if r["centrality"] and r["centrality"] > 0.7)

            return {
                "community_id": community_id,
                "pagerank": pagerank,
                "network_size": len(related),
                "shared_device_count": sum(d["share_count"] for d in devices),
                "shared_devices": [
                    {
                        "device_id": d["device_id"],
                        "accounts_sharing": d["accounts_sharing"],
                        "share_count": d["share_count"]
                    }
                    for d in devices
                ],
                "high_centrality_neighbors": high_centrality,
                "related_accounts": [
                    {
                        "id": r["related_id"],
                        "community_id": r["community_id"],
                        "centrality": float(r["centrality"]) if r["centrality"] else 0.0
                    }
                    for r in related
                ]
            }

    except Exception as e:
        log.error("graph_service", status="failed", error=str(e), account_id=account_id)
        return None