"""Common utilities for loading configuration values.

This module centralizes the logic for retrieving configuration parameters for
the memecoin sniping project.  Instead of reading environment variables
directly throughout the code, agents can call ``load_config`` once at
startup.  The configuration file can be stored locally or in S3.  When
executed in AWS Lambda, the function attempts to download the configuration
JSON from S3 (bucket/key defined by ``CONFIG_BUCKET`` and ``CONFIG_KEY``
environment variables).  If those variables are not set or boto3 is
unavailable, the function falls back to reading a ``agent_config.json``
file in the same directory.

Usage:

    from common.config import load_config

    config = load_config()
    sqs_queue_url = config["discoverer"]["sqs_queue_url"]

The returned object is a Python dict loaded from JSON.
"""

from __future__ import annotations

import json
import os
import logging
from typing import Any, Dict

try:
    import boto3  # type: ignore
except Exception:  # pragma: no cover
    boto3 = None  # type: ignore

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _load_local_config(path: str) -> Dict[str, Any]:
    """Load configuration from a local JSON file.

    Args:
        path: Path to a JSON configuration file.

    Returns:
        Parsed configuration as a dict.  If the file does not exist or
        cannot be parsed, an empty dict is returned and a warning is
        logged.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        logger.warning("Configuration file %s not found; using defaults", path)
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to load config from %s: %s", path, exc)
    return {}


def _load_s3_config(bucket: str, key: str) -> Dict[str, Any]:
    """Load configuration from an S3 object.

    Args:
        bucket: Name of the S3 bucket.
        key: Key of the object containing the JSON configuration.

    Returns:
        Parsed configuration dict.  If boto3 is unavailable or any error
        occurs, an empty dict is returned.
    """
    if boto3 is None:
        logger.info("boto3 unavailable; cannot load config from S3")
        return {}
    s3 = boto3.client("s3")  # type: ignore
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        body = response["Body"].read().decode("utf-8")
        return json.loads(body)
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to load config from s3://%s/%s: %s", bucket, key, exc)
        return {}


def load_config() -> Dict[str, Any]:
    """Return the merged configuration.

    The function first checks whether ``CONFIG_BUCKET`` and ``CONFIG_KEY``
    environment variables are set.  If so, it attempts to load the JSON
    config from S3.  Then it loads a local ``agent_config.json`` file from
    the current directory and merges the two dictionaries (local values
    override remote values).  If neither source yields data, an empty
    dict is returned.

    Returns:
        Configuration dictionary.
    """
    config: Dict[str, Any] = {}
    bucket = os.environ.get("CONFIG_BUCKET")
    key = os.environ.get("CONFIG_KEY")
    if bucket and key:
        config.update(_load_s3_config(bucket, key))
    # local override
    # configuration file lives at the repository root
    config_path = os.path.join(
        os.path.dirname(__file__), os.pardir, os.pardir, "agent_config.json"
    )
    config.update(_load_local_config(os.path.abspath(config_path)))
    return config
