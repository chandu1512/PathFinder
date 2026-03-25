import json
import chromadb

with open("all_courses.json") as f:
    courses = json.load(f)

print(f"Loaded {len(courses)} courses")

client = chromadb.PersistentClient(path="./pathfinder_db")
collection = client.get_or_create_collection(
    name="udel_courses",
    metadata={"hnsw:space": "cosine"}
)

batch_size = 500
for i in range(0, len(courses), batch_size):
    batch = courses[i:i + batch_size]
    collection.add(
        ids=[f"course_{i+j}" for j in range(len(batch))],
        documents=[c.get("description", c.get("title", "")) for c in batch],
        metadatas=[{"title": c.get("title", ""), "url": c.get("url", "")} for c in batch]
    )
    print(f"Added batch {i//batch_size + 1}: {len(batch)} courses")

print(f"\nDone! Stored {collection.count()} courses in ChromaDB")
print("Database saved to ./pathfinder_db/")
