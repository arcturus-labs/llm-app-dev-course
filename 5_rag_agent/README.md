# Install requirements
`pip install -r requirements.txt`

# Download and run elasticsearch in a docker container
Export credentials (silly elasticsearch requirement) and run elasticsearch. _Must be sourced._
`source scripts/start.sh`

# Index docs
This deletes the existing index and reindexes it from products.csv. This is from the WANDS dataset: https://github.com/wayfair/WANDS
`python index_docs.py`

# Make sure search works
`python search_docs.py`
This file implements the search functionality used by rag_bot.py

# Make sure chat works
Runs generic chat bot that has tools. This file implements the class used by rag_bot.by
`python chat_bot.py`

# Run the RAG bot
Interactively talk with the WANDS sales assistant. Try to exercise all the search arguments, get it to make parallel searches, and searches in series.
`python rag_bot.py`

# Shut down elasticsearch
`scripts/stop.sh`