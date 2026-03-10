import asyncio
from src.core.llm_factory import LLMFactory
from src.core.config_loader import config
from langchain_core.prompts import ChatPromptTemplate

async def main():
    llm_config = config.get_llm_config()
    llm = LLMFactory.create_llm(llm_config)
    
    prompt = ChatPromptTemplate.from_template("Say 'Hello World'")
    chain = prompt | llm
    result = chain.invoke({})
    print(f"LLM test result: {result}")

asyncio.run(main())
