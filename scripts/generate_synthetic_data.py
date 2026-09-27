"""
Generate synthetic device/IP/KYC/blacklist data to complement PaySim.
Run once: python scripts/generate_synthetic_data.py
"""
import pandas as pd
import numpy as np
import random
import string
from pathlib import Path

ROOT = Path(__file__).parent.parent
PAYSIM_PATH = ROOT / "data" / "paysim" / "PS_20174392719_1491204439457_log.csv"
OUT_DIR = ROOT / "data" / "synthetic"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

HIGH_RISK_COUNTRIES = ["NG", "KE", "GH", "CM", "SN"]
NORMAL_COUNTRIES = ["NL", "DE", "FR", "BE", "GB", "US", "SE", "DK"]


def random_device_id():
    return "device_" + "".join(random.choices(string.digits, k=6))


def random_ip(country):
    return f"{random.randint(1,254)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def main():
    print("Loading PaySim accounts...")
    df = pd.read_csv(PAYSIM_PATH, usecols=["nameOrig", "isFraud"])

    # Only customer accounts (C prefix)
    accounts = df[df["nameOrig"].str.startswith("C")].drop_duplicates("nameOrig")
    fraud_accounts = set(
        accounts[accounts["isFraud"] == 1]["nameOrig"].tolist()
    )
    normal_accounts = set(
        accounts[accounts["isFraud"] == 0]["nameOrig"].tolist()
    )

    print(f"Fraud accounts: {len(fraud_accounts)}")
    print(f"Normal accounts: {len(normal_accounts)}")

    # ── Device / IP mapping ──────────────────────────────────────────
    print("Generating device/IP mapping...")
    records = []

    # Fraud accounts: share devices in rings of 3-8
    fraud_list = list(fraud_accounts)
    random.shuffle(fraud_list)
    i = 0
    while i < len(fraud_list):
        ring_size = random.randint(3, 8)
        ring = fraud_list[i:i + ring_size]
        shared_device = random_device_id()
        country = random.choice(HIGH_RISK_COUNTRIES)
        for acc in ring:
            # 70% chance to share device, 30% own device
            device = shared_device if random.random() < 0.70 else random_device_id()
            records.append({
                "account_id": acc,
                "device_id": device,
                "ip_address": random_ip(country),
                "country": country
            })
        i += ring_size

    # Normal accounts: unique device each
    for acc in normal_accounts:
        records.append({
            "account_id": acc,
            "device_id": random_device_id(),
            "ip_address": random_ip(random.choice(NORMAL_COUNTRIES)),
            "country": random.choice(NORMAL_COUNTRIES)
        })

    device_df = pd.DataFrame(records)
    device_df.to_csv(OUT_DIR / "account_device_ip.csv", index=False)
    print(f"Saved account_device_ip.csv: {len(device_df)} rows")

    # ── KYC profiles ─────────────────────────────────────────────────
    print("Generating KYC profiles...")
    kyc_records = []

    for acc in fraud_accounts:
        kyc_records.append({
            "account_id": acc,
            "days_since_open": random.randint(1, 30),
            "nationality": random.choice(HIGH_RISK_COUNTRIES),
            "risk_tier": "High"
        })

    for acc in normal_accounts:
        kyc_records.append({
            "account_id": acc,
            "days_since_open": random.randint(30, 2000),
            "nationality": random.choice(NORMAL_COUNTRIES),
            "risk_tier": random.choice(["Low", "Low", "Low", "Medium"])
        })

    kyc_df = pd.DataFrame(kyc_records)
    kyc_df.to_csv(OUT_DIR / "kyc_profiles.csv", index=False)
    print(f"Saved kyc_profiles.csv: {len(kyc_df)} rows")

    # ── Blacklist ─────────────────────────────────────────────────────
    print("Generating blacklist...")
    blacklist_df = pd.DataFrame({"account_id": list(fraud_accounts)})
    blacklist_df.to_csv(OUT_DIR / "blacklist.csv", index=False, header=False)
    print(f"Saved blacklist.csv: {len(blacklist_df)} accounts")

    print("Done.")


if __name__ == "__main__":
    main()