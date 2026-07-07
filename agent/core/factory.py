import logfire
from pydantic_ai import Agent, NativeOutput
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from agent.core.actions import Done, SearchAction
from config import Config

logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()


def _build_model(config: Config) -> OpenAIChatModel:
    return OpenAIChatModel(
        config.llamacpp_model,
        provider=OpenAIProvider(base_url=config.llamacpp_url, api_key="not-needed"),
    )


def build_planner_agent(config: Config, instructions: str) -> Agent:
    """Prompted-path planner: returns a SearchAction or Done per turn, no tools.

    Uses NativeOutput so llama.cpp grammar-*forces* valid JSON (response_format
    json_schema). This targets Krikri, whose free-form JSON is unreliable under
    PromptedOutput, and — being output formatting, not tool-calling — does not
    hit llama.cpp's native tool-call parser.
    """
    return Agent(
        _build_model(config),
        output_type=NativeOutput([SearchAction, Done]),
        instructions=instructions,
        retries=3,
    )


def build_writer_agent(config: Config, instructions: str) -> Agent:
    """Prompted-path writer: plain streamed text answer, no tools."""
    return Agent(_build_model(config), instructions=instructions)
