import json
import os
import time
import random
from pathlib import Path

from elasticsearch import Elasticsearch

# Create the client instance
api_key = os.getenv("ES_LOCAL_API_KEY")
es = Elasticsearch("http://localhost:9200", api_key=api_key)

# Define mapping for the index
mapping = {
    "mappings": {
        "properties": {
            "product_id": {"type": "keyword"},
            "product_name": {
                "type": "text",
                "analyzer": "english",
                "fields": {
                    "exact": {
                        "type": "text",
                        "analyzer": "standard"
                    }
                }
            },
            "product_class": {"type": "keyword"},
            "product_description": {
                "type": "text",
                "analyzer": "english",
                "fields": {
                    "exact": {
                        "type": "text",
                        "analyzer": "standard"
                    }
                }
            },
            "rating_count": {"type": "integer"},
            "average_rating": {"type": "float"},
            "availability": {"type": "keyword"},
        }
    }
}

# Create the index with mapping
index_name = "wands"

if es.indices.exists(index=index_name):
    es.indices.delete(index=index_name)
es.indices.create(index=index_name, body=mapping)

import pandas as pd
from elasticsearch.helpers import bulk

# Load product data
product_df = pd.read_csv("./product.csv", sep='\t')
product_df = product_df.rename(columns={"category hierarchy": "category_hierarchy"})

product_df["rating_count"] = product_df["rating_count"].fillna(0)
product_df["average_rating"] = product_df["average_rating"].fillna(0)
product_df["review_count"] = product_df["review_count"].fillna(0)

product_df["product_class"] = product_df["product_class"].fillna("")
product_df["product_description"] = product_df["product_description"].fillna("")
product_df["category_hierarchy"] = product_df["category_hierarchy"].fillna("")

states = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", 
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", 
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", 
    "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi", 
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", 
    "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", 
    "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", 
    "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", 
    "Washington", "West Virginia", "Wisconsin", "Wyoming"
]

# Prepare documents for bulk indexing
def doc_generator():
    for i, row in product_df.iterrows():
        doc = {
            "product_id": row["product_id"], # TODO: should I remove this or make an alias?
            "product_name": row["product_name"], 
            "product_class": row["product_class"].split("|"),
            "category_hierarchy": [row["category_hierarchy"]],
            "product_description": row["product_description"],
            "product_features": row["product_features"],
            "rating_count": row["rating_count"],
            "average_rating": row["average_rating"],
            "review_count": row["review_count"],
            "availability": random.sample(states, 45)
        }
        yield {
            "_index": index_name,
            "_id": row["product_id"],
            "_source": doc
        }

def index_docs():
    start = time.time()
    success, failed = bulk(es, doc_generator(), raise_on_error=False)
    print(f"Successfully indexed {success} documents")
    if failed:
        print(f"Failed to index {len(failed)} documents")
        print(f"Time taken: {time.time() - start} seconds")

if __name__ == "__main__":
    index_docs()
    es.indices.refresh(index=index_name)

    # Search query
    search_query = {
        "query": {
            "multi_match": {
                "query": "wood",
                "fields": ["product_name"]
            },
        },
        "size":1
    }

    # Perform search
    results = es.search(index=index_name, body=search_query)

    # Print results
    print("\nSearch Results:")
    for hit in results["hits"]["hits"]:
        print(f"Score: {hit['_score']}")
        print(f"Document: {json.dumps(hit['_source'], indent=2)}")
