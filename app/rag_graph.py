from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
)


from app.llm import llm
from app.vector_store import (
    load_vector_store,
    create_retriever
)


class RAGState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    context: str


vector_store = load_vector_store()
retriever = create_retriever(vector_store)


def retrieve(state: RAGState):
    latest_messages = state["messages"][-1]

    question = latest_messages.content

    documents = retriever.invoke(question)

    context = "\n\n".join(
        document.page_content
        for document in documents
    )

    return {
        "context": context
    }

def generate(state: RAGState):
    system_message = SystemMessage(
        context=f"""
You are an assistant that answers question based only on the provided journal context.

Answer based only on the provided journal context.
Journal context:
{state["context"]}

Answer Clearly and concisely
if you don't find the answer, just say so
""")

    messages = [
        system_message,
        *state["messages"]
    ]

    response = llm.invoke(messages)

    return {
        "messages": [response]
    }

graph_builder = StateGraph(RAGState)

graph_builder.add_node("retrieve", retrieve)
graph_builder.add_node("generate",generate)

graph_builder.add_edge(START, "retrieve")
graph_builder.add_edge("retrieve", "generate")
graph_builder.add_edge("generate",END)

memory = InMemorySaver()

rag_graph = graph_builder.compile(
    checkpointer=memory
)