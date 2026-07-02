import logfire
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from agent.core.deps import AgentDeps, _search_regulations_tool
from agent.core.prompts import ASK_INSTRUCTIONS, CHECK_INSTRUCTIONS
from config import Config

logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()


def _build_agent(config: Config, instructions: str) -> Agent:
    model = OpenAIChatModel(
        config.llamacpp_model,
        provider=OpenAIProvider(base_url=config.llamacpp_url, api_key="not-needed"),
    )
    agent = Agent(model, deps_type=AgentDeps, instructions=instructions)
    agent.tool(_search_regulations_tool)
    return agent


def build_ask_agent(config: Config) -> Agent:
    return _build_agent(config, ASK_INSTRUCTIONS)


def build_check_agent(config: Config) -> Agent:
    return _build_agent(config, CHECK_INSTRUCTIONS)
