#!/bin/sh
cd /opt/data/workspace/hermes-feegow-mcp
export PYTHONPATH=src
exec uv run python -m ana_feegow.mcp.server
