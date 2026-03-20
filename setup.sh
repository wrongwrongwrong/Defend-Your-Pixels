#!/bin/bash

# 1. Create a virtual environment folder named 'venv'
python3 -m venv venv

# 2. Activate it
source venv/bin/activate

# 3. Upgrade pip and install your list
pip install --upgrade pip
pip install -r requirements.txt

echo "Environment is ready! Run 'source venv/bin/activate' to start."