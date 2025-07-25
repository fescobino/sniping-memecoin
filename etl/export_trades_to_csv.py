"""
Utility script to export historical trades from DynamoDB to a CSV file.

This script can be executed as a standalone module. It reads trades
from the DynamoDB table defined by the ``TRADER_TABLE_NAME`` environment
variable (defaults to ``MemecoinSnipingTraderTable``), filters them by a
``days_back`` window and writes the results to a CSV file. Decimals are
converted to floats for better compatibility with pandas and other
analytics tools.

Example usage:

    python export_trades_to_csv.py --days 60 --output trades_60d.csv

In a Lambda context, this script can be imported and the
``export_trades`` function called directly to produce a CSV in the /tmp
directory, then uploaded to S3 if desired.
"""
from __future__ import annotations

import csv
import argparse
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any

try:
    import boto3  # type: ignore
    from boto3.dynamodb.conditions import Attr  # type: ignore
except Exception:
    boto3 = None  # type: ignore
    Attr = None  # type: ignore


def scan_trades(days_back: int = 30) -> List[Dict[str, Any]]:
    """Retrieve trades from DynamoDB newer than ``days_back`` days.

    Args:
        days_back: Number of days of history to retrieve.

    Returns:
        A list of trade dictionaries.
    """
    if boto3 is None or Attr is None:
        raise RuntimeError("boto3 is required for DynamoDB operations")

    table_name = os.environ.get("TRADER_TABLE_NAME", "MemecoinSnipingTraderTable")
    dynamodb = boto3.resource("dynamodb")  # type: ignore
    table = dynamodb.Table(table_name)
    start_date = (datetime.utcnow() - timedelta(days=days_back)).isoformat()

    # Filter expression: entry_time >= :start_date
    filter_expr = Attr("entry_time").gte(start_date)
    resp = table.scan(FilterExpression=filter_expr)
    trades = resp.get("Items", [])
    # Convert Decimal values to float
    for trade in trades:
        for key, value in list(trade.items()):
            if isinstance(value, Decimal):
                trade[key] = float(value)
    return trades


def write_csv(trades: List[Dict[str, Any]], output_path: str) -> None:
    """Write a list of trade dicts to a CSV file.

    Args:
        trades: List of trade dictionaries.
        output_path: Destination path for the CSV file.
    """
    if not trades:
        print("No trades to export")
        return
    # Determine all keys
    keys = sorted({key for trade in trades for key in trade.keys()})
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        for trade in trades:
            writer.writerow(trade)
    print(f"Exported {len(trades)} trades to {output_path}")


def export_trades(days_back: int = 30, output_path: str = "trades_export.csv") -> str:
    """High-level function to export trades to CSV.

    Returns the path to the CSV file.
    """
    trades = scan_trades(days_back)
    write_csv(trades, output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export trades from DynamoDB to CSV")
    parser.add_argument("--days", type=int, default=30, help="Number of days of history to export")
    parser.add_argument("--output", type=str, default="trades_export.csv", help="Output CSV filename")
    args = parser.parse_args()
    export_trades(args.days, args.output)


if __name__ == "__main__":
    main()