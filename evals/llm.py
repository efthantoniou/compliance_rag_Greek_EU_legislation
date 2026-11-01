from pydantic import BaseModel
from pydantic_ai import Agent, NativeOutput
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from config import Config


def build_structured_agent(
    config: Config,
    instructions: str,
    output_model: type[BaseModel],
    *,
    base_url: str | None = None,
    model_name: str | None = None,
) -> Agent:
    model = OpenAIChatModel(
        model_name or config.llamacpp_model,
        provider=OpenAIProvider(base_url=base_url or config.llamacpp_url, api_key="not-needed"),
    )
    return Agent(model, instructions=instructions, output_type=NativeOutput(output_model))
