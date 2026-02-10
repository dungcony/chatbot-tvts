"""
Vector Search - Tìm kiếm ngữ nghĩa trong MongoDB
Sử dụng MongoDB Atlas Vector Search với embedding 768 chiều.
"""

from models.document import get_collection, VECTOR_INDEX_NAME
from services.embedding import get_embedding_model


def vector_search(query: str, num_candidates: int = 150, limit: int = 4, score_threshold: float = 0.6):
    """
    Tìm kiếm vector trong MongoDB (theo Hình 4.2.3):
    - index: "vector_index"
    - numCandidates: 150
    - limit: 4
    - score_threshold: Chỉ giữ docs có score >= ngưỡng này

    Returns:
        list[dict]: Danh sách documents với keys: content, score
    """
    embedding_model = get_embedding_model()
    query_vector = embedding_model.embed_query(query)
    collection = get_collection()

    pipeline = [
        {
            "$vectorSearch": {
                "index": VECTOR_INDEX_NAME,
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": num_candidates,
                "limit": limit
            }
        },
        {
            "$project": {
                "_id": 0,
                "content": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]

    results = list(collection.aggregate(pipeline))

    # Lọc bỏ docs có score thấp hơn ngưỡng
    filtered = [doc for doc in results if doc.get("score", 0) >= score_threshold]
    return filtered
