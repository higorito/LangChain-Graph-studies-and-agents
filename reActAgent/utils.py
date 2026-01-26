from langchain.chat_models import init_chat_model, BaseChatModel

def load_llm() -> BaseChatModel:
    return init_chat_model("gpt-oss:20b-cloud", model_provider="ollama")