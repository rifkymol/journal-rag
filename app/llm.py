from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()
# Fungsi ChatOpenAI adalah integrasi LangChain untuk berkomunikasi dengan model OpenAI
llm = ChatOpenAI(
    model="gpt-5-mini"
)

def ask_llm(question: str):
    # fungsi invoke adalah menjalankan/invoke model dengan sebuah input dan mendapatkan output
    response = llm.invoke(question)

    return response.content