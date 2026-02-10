"""
Vector Search - Tim kiem ngu nghia trong MongoDB
Ho tro loc theo truong (school).
"""
from models.document import get_collection, VECTOR_INDEX_NAME
from services.embedding import get_embedding_model


def vector_search(query, school=None, num_candidates=150, limit=4, score_threshold=0.6):
    embedding_model = get_embedding_model()
    query_vector = embedding_model.embed_query(query)
    collection = get_collection()

    vs_stage = {
        "$vectorSearch": {
            "index": VECTOR_INDEX_NAME,
            "path": "embedding",
            "queryVector": query_vector,
            "numCandidates": num_candidates,
            "limit": limit
        }
    }
    if school:
        vs_stage["$vectorSearch"]["filter"] = {"school": school}

    pipeline = [
        vs_stage,
        {"$project": {"_id": 0, "content": 1, "school": 1, "score": {"$meta": "vectorSearchScore"}}}
    ]
    results = list(collection.aggregate(pipeline))
    return [doc for doc in results if doc.get("score", 0) >= score_threshold]
