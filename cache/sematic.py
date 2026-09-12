import hashlib
import uuid

import redis
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient, models


load_dotenv()

openai = OpenAI()
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

qdrant = QdrantClient(url="http://localhost:6333")
COLLECTION = "cache"


# Create Qdrant collection if it does not exist
def init_qdrant():
    if not qdrant.collection_exists(COLLECTION):
        qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=models.VectorParams(
                size=1536,
                distance=models.Distance.COSINE
            )
        )


# Create Redis key from exact question
def get_cache_key(prompt):
    prompt = prompt.strip().lower()
    return "cache:" + hashlib.sha256(prompt.encode()).hexdigest()


# Create embedding
def get_embedding(text):
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )

    return response.data[0].embedding


# Ask LLM
def ask_llm(prompt):
    response = openai.responses.create(
        model="gpt-5.4-mini",
        input=prompt
    )

    return response.output_text


# Search Qdrant for a similar question
def search_qdrant(embedding):
    result = qdrant.query_points(
        collection_name=COLLECTION,
        query=embedding,
        limit=1
    )

    if result.points and result.points[0].score > 0.9:
        return result.points[0].payload["answer"]

    return None


# Save question + answer in Qdrant
def save_to_qdrant(prompt, embedding, answer):
    qdrant.upsert(
        collection_name=COLLECTION,
        points=[
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "prompt": prompt,
                    "answer": answer
                }
            )
        ]
    )


def get_answer(prompt):

    # 1. Exact cache
    key = get_cache_key(prompt)
    answer = redis_client.get(key)

    if answer:
        print("REDIS CACHE HIT")
        return answer

    # 2. Semantic cache
    embedding = get_embedding(prompt)
    answer = search_qdrant(embedding)

    if answer:
        print("QDRANT CACHE HIT")
        redis_client.set(key, answer)
        return answer

    # 3. LLM
    print("LLM CALL")

    answer = ask_llm(prompt)

    redis_client.set(key, answer)
    save_to_qdrant(prompt, embedding, answer)

    return answer


# Setup once
init_qdrant()

query = input("Human Query: ")

print("\nAI RESPONSE\n")
print(get_answer(query))
