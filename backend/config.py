import yaml
from pathlib import Path
from functools import lru_cache

ROOT = Path(__file__).parent.parent

@lru_cache()
def get_config() -> dict:
    with open(ROOT / "config.yaml", "r") as f:
        return yaml.safe_load(f)

config = get_config()

rules  = config["rules_engine"]
score  = config["scoring"]
graph  = config["graph"]
llm    = config["llm"]
redis  = config["redis"]
neo4j  = config["neo4j"]
pg     = config["postgres"]
demo   = config["demo"]
cc     = config["champion_challenger"]