import os

from elasticsearch import Elasticsearch
from pathlib import Path

# Create the client instance
api_key = os.getenv("ES_LOCAL_API_KEY")
es = Elasticsearch("http://localhost:9200", api_key=api_key)
index_name = "wands"

def high_level_search(
        query_string, 
        availability=None, 
        product_class=None, 
        min_average_rating=None, 
        num_results=10,
    ):
    search_query = {
        "query": {
            "bool": {
                "should": [
                    {
                        "multi_match": {
                            "query": query_string,
                            "type": "phrase",
                            "fields": [
                                "product_name", 
                                "product_description"
                            ]
                        }
                    },
                    {
                        "multi_match": {
                            "query": query_string,
                            "fields": [
                                "product_name.exact", 
                                "product_description.exact"
                            ]
                        }
                    },
                ],
                "must": [
                    {
                        "multi_match": {
                            "query": query_string,
                            "fields": [
                                "product_name",
                                "product_description"
                            ]
                        }
                    }
                ],
                "filter": []
            },
        },
        "aggs": {
            "product_class": {
                "terms": {
                    "field": "product_class",
                    "size": 10
                }
            }
        }
    }

    if availability:
        search_query["query"]["bool"]["filter"].append(
            {
                "term": {
                    "availability": availability
                }
            }
        )
    if product_class:
        search_query["query"]["bool"]["filter"].append(
            {
                "term": {
                    "product_class": product_class
                }
            }
        )
    if min_average_rating:
        search_query["query"]["bool"]["filter"].append(
            {
                "range": {
                    "average_rating": {"gte": min_average_rating}
                }
            }
        )

    search_query["size"] = num_results
    results = es.search(index=index_name, body=search_query)
    return results


def format_hit_for_human(hit):
    """Prints score, product_id, product_name, and category_hierarchy, truncated prodiuct_description (150 characters) rating_count, average_rating, and review_count"""
    result = []
    # result.append(f"Score: {hit['_score']}")
    result.append(f"Product ID: {hit['_source']['product_id']}")
    result.append(f"Product Name: {hit['_source']['product_name']}")
    # result.append(f"Category Hierarchy: {hit['_source']['category_hierarchy']}")
    result.append(f"Product Class: {hit['_source']['product_class']}")
    result.append(f"Product Description: {hit['_source']['product_description'][:750]}...")
    # result.append(f"Rating Count: {hit['_source']['rating_count']}")
    result.append(f"Average Rating: {hit['_source']['average_rating']}")
    # result.append(f"Review Count: {hit['_source']['review_count']}")
    # result.append(f"Availability: {hit['_source']['availability']}")
    result.append("---")
    return "\n".join(result)

def format_results_for_human(results):
    print(f"Total Hits: {results['hits']['total']['value']}")
    print(f"Max Score: {results['hits']['max_score']}")
    min_score = min(hit['_score'] for hit in results['hits']['hits'])
    print(f"Min Score: {min_score}")
    print("="*100)
    for hit in results['hits']['hits']:
        print(format_hit_for_human(hit))

def format_aggs_for_human(aggs):
    """Returns a list of strings, each representing a bucket in the aggs"""
    result = []
    for agg_name, agg_data in aggs.items():
        result.append(f"\n{agg_name}:")
        for bucket in agg_data['buckets']:
            if bucket['key'] != '':
                result.append(f"  {bucket['key']}: {bucket['doc_count']}")
    return "Facet Counts:\n" + "\n".join(result)

def format_results_for_toolcall(results):
    """Returns a list of strings, each representing a hit"""
    hits = "\n".join([format_hit_for_human(hit) for hit in results['hits']['hits']])    
    aggs = format_aggs_for_human(results['aggregations'])
    return f"{hits}\n\n{aggs}"

if __name__ == "__main__":
    print(format_results_for_toolcall(high_level_search("standing desk", min_average_rating=3.9, num_results=5)))
    print('\n'*10)
    # print(yaml.dump(high_level_search("standing desk", num_results=5)))
    