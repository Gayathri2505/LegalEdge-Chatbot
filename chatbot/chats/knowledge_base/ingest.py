import os
import json
import hashlib
from tqdm import tqdm
from django.utils import timezone
from langchain.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from chats.models import Document
from ..utils.embeddings import generate_embedding

# Supported file types and their loaders
FILE_LOADERS = {
    ".pdf": PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".doc": Docx2txtLoader,
    ".txt": TextLoader
}

def get_file_loader(file_path):
    """Get appropriate loader based on file extension"""
    ext = os.path.splitext(file_path)[1].lower()
    return FILE_LOADERS.get(ext)

def load_document(file_path):
    """Load document using LangChain loader"""
    loader_class = get_file_loader(file_path)
    if not loader_class:
        raise ValueError(f"Unsupported file type: {file_path}")
    
    loader = loader_class(file_path)
    return loader.load()

def process_file(file_path):
    """Process a single file into chunks"""
    try:
        docs = load_document(file_path)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", " ", ""]  # Legal-aware splitting
        )
        return text_splitter.split_documents(docs)
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return []

def get_file_hash(file_path):
    """Generate MD5 hash of file content"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def embed_and_store(file_path):
    filename = os.path.basename(file_path)
    current_hash = get_file_hash(file_path)
    current_mtime = os.path.getmtime(file_path)
    
    # Check if file needs processing
    latest_doc = Document.objects.filter(
        metadata__file_name=filename
    ).order_by('-modified_at').first()
    
    if latest_doc and (latest_doc.metadata.get('file_hash') == current_hash and 
                      latest_doc.modified_at.timestamp() >= current_mtime):
        print(f"⏩ Skipping unchanged file: {filename}")
        return
    
    print(f"📄 Processing: {filename}")
    
    # Process with LangChain
    chunks = process_file(file_path)
    if not chunks:
        return
        
    current_time = timezone.now()
    
    # Delete old chunks if they exist
    if latest_doc:
        Document.objects.filter(metadata__file_name=filename).delete()
        print(f"♻️ Deleted old versions of {filename}")
    
    # Prepare documents for bulk insert
    docs_to_insert = []
    for idx, chunk in enumerate(chunks):
        embedding = generate_embedding(chunk.page_content)
        metadata = {
            "file_name": filename,
            "chunk_index": idx,
            "file_hash": current_hash,
            "file_mtime": current_mtime,
            "source": chunk.metadata.get("source", file_path),
            "page": chunk.metadata.get("page", 0),
        }
        
        docs_to_insert.append(Document(
            content=chunk.page_content,
            metadata=metadata,
            embedding=embedding,
            created_at=current_time,
            modified_at=current_time
        ))
    
    if docs_to_insert:
        Document.objects.bulk_create(docs_to_insert, batch_size=100)
        print(f"✅ Inserted {len(docs_to_insert)} chunks from {filename}")

def embed_folder(folder_path):
    """Process all supported files in a folder"""
    for root, _, files in os.walk(folder_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in FILE_LOADERS:
                full_path = os.path.join(root, file)
                embed_and_store(full_path)