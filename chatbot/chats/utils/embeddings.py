from sentence_transformers import SentenceTransformer

# Load model once when Django starts
model = SentenceTransformer("all-MiniLM-L6-v2")

def generate_embedding(text: str) -> list:
    return model.encode(text).tolist()
