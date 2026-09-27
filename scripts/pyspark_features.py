"""
PySpark feature engineering on PaySim dataset.
Run once: python scripts/pyspark_features.py
Output: data/processed/features.parquet
"""
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pathlib import Path

ROOT = Path(__file__).parent.parent
PAYSIM_PATH = str(ROOT / "data" / "paysim" / "PS_20174392719_1491204439457_log.csv")
KYC_PATH = str(ROOT / "data" / "synthetic" / "kyc_profiles.csv")
OUT_PATH = str(ROOT / "data" / "processed" / "features.parquet")


def main():
    spark = SparkSession.builder \
        .appName("FraudAgentFeatures") \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.shuffle.partitions", "8") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")
    print("Spark session started")

    # ── Load PaySim ──────────────────────────────────────────────────
    print("Loading PaySim...")
    df = spark.read.csv(PAYSIM_PATH, header=True, inferSchema=True)
    df = df.filter(F.col("nameOrig").startswith("C"))
    print(f"Rows: {df.count()}")

    # ── Load KYC ─────────────────────────────────────────────────────
    print("Loading KYC profiles...")
    kyc = spark.read.csv(KYC_PATH, header=True, inferSchema=True)
    kyc = kyc.select("account_id", "days_since_open", "risk_tier")

    # ── Feature engineering ──────────────────────────────────────────
    print("Computing features...")

    # Night ratio: step % 24 between 22 and 8
    df = df.withColumn(
        "is_night",
        F.when(
            (F.col("step") % 24 >= 22) | (F.col("step") % 24 <= 8),
            1
        ).otherwise(0)
    )

    # Per-account aggregations
    agg = df.groupBy("nameOrig").agg(
        F.count("*").alias("tx_count"),
        F.mean("amount").alias("avg_amount"),
        F.stddev("amount").alias("std_amount"),
        F.max("amount").alias("max_amount"),
        F.mean("is_night").alias("night_ratio"),
        F.sum(F.when(F.col("type") == "TRANSFER", 1).otherwise(0)).alias("transfer_count"),
        F.sum(F.when(F.col("type") == "CASH_OUT", 1).otherwise(0)).alias("cashout_count"),
        F.max("step").alias("last_step"),
        F.min("step").alias("first_step"),
    )

    # Derived features
    agg = agg.withColumn(
        "cross_ratio",
        (F.col("transfer_count") + F.col("cashout_count")) / F.col("tx_count")
    )

    # 7-day frequency (last 168 steps)
    recent = df.filter(F.col("step") >= (F.lit(744) - 168))
    freq_7d = recent.groupBy("nameOrig").agg(
        F.count("*").alias("freq_7d")
    )

    # Join everything
    features = agg.join(freq_7d, on="nameOrig", how="left")
    features = features.join(kyc, agg["nameOrig"] == kyc["account_id"], how="left")

    # Final columns
    features = features.select(
        F.col("nameOrig").alias("account_id"),
        F.col("days_since_open").cast("int"),
        F.col("avg_amount").cast("double"),
        F.col("std_amount").cast("double"),
        F.col("max_amount").cast("double"),
        F.col("night_ratio").cast("double"),
        F.col("cross_ratio").cast("double"),
        F.col("freq_7d").cast("int"),
        F.col("tx_count").cast("int"),
        F.col("risk_tier"),
    ).fillna({
        "days_since_open": 365,
        "freq_7d": 0,
        "night_ratio": 0.0,
        "cross_ratio": 0.0,
        "std_amount": 0.0,
        "risk_tier": "Low"
    })

    print(f"Feature rows: {features.count()}")

    # Save ─────────────────────────────────────────────────────────
    print("Saving to parquet...")
    features.coalesce(1).write.mode("overwrite").parquet(OUT_PATH)
    print(f"Saved to {OUT_PATH}")

    spark.stop()
    print("Done.")


if __name__ == "__main__":
    main()