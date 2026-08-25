from app.llm import llm


def ask_rag(question: str, retriever):
    documents = retriever.invoke(question)

    context = "\n\n".join(
        document.page_content
        for document in documents
    )

    prompt = f"""
You are an assistant that answers questions based on only on the provided journal context.

Context:
{context}

Answer clearly and cocisely
"""

    response = llm.invoke(prompt)

    return {
        "answer": response.content,
        "sources": [
            document.metadata 
            for document in documents
        ]
    }