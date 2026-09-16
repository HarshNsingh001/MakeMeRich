from langchain_core.language_models.chat_models import BaseChatModel
from core.config import get_settings

def get_llm() -> BaseChatModel:
    """
    Factory function to instantiate the LLM model based on user's environment config.
    Returns a BaseChatModel which can be used seamlessly with LangChain/LangGraph.
    """
    settings = get_settings()
    provider = settings.active_llm_provider.lower()
    
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is missing from environment")
        return ChatOpenAI(
            api_key=settings.openai_api_key, 
            model="gpt-4o",
            temperature=0.0
        )
        
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is missing from environment")
        return ChatGoogleGenerativeAI(
            api_key=settings.gemini_api_key,
            model="gemini-3.6-flash",
            temperature=0.0
        )
        
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is missing from environment")
        return ChatAnthropic(
            api_key=settings.anthropic_api_key, 
            model="claude-3-5-sonnet-20240620",
            temperature=0.0
        )
        
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}. Options are: openai, gemini, anthropic.")
