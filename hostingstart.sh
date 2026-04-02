#!/bin/bash
# Install dependencies (Azure does this, but this is a safety net)
pip install -r requirements.txt

# Run your market service
python AngelOne.py
