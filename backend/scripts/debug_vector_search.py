import asyncio
from src.core.llm_factory import EmbeddingFactory
from src.core.config_loader import config
from src.ingestion.vector_store_wrapper import VectorStoreWrapper

async def main():
    embedding_config = config.get_embedding_config()
    embeddings = EmbeddingFactory.create_embeddings(embedding_config)
    vsw = VectorStoreWrapper(embeddings)
    
    query = "What courses are offered?"
    print(f"Query: {query}")
    
    # Direct call to Chroma's similarity_search
    results = vsw.vector_store.similarity_search(query, k=3)
    print(f"\nNumber of results: {len(results)}")
    for i, doc in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"  Type: {type(doc)}")
        print(f"  Has page_content: {hasattr(doc, 'page_content')}")
        if hasattr(doc, 'page_content'):
            print(f"  Content preview: {doc.page_content[:200]}...")
        else:
            print(f"  Content: {str(doc)[:200]}...")
        print(f"  Metadata: {doc.metadata if hasattr(doc, 'metadata') else 'N/A'}")

if __name__ == "__main__":
    asyncio.run(main())
