# pyright: reportMissingImports=false
import asyncio
import os
import sys
from dataclasses import dataclass

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

load_dotenv()

# Third-party imports
import gradio as gr  # type: ignore
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Local module imports
from browser_use import Agent
from browser_use.llm import ChatOpenAI
from browser_use.llm.ollama.chat import list_local_ollama_models, ChatOllama


@dataclass
class ActionResult:
	is_done: bool
	extracted_content: str | None
	error: str | None
	include_in_memory: bool


@dataclass
class AgentHistoryList:
	all_results: list[ActionResult]
	all_model_outputs: list[dict]


def parse_agent_history(history_str: str) -> None:
	console = Console()

	# Split the content into sections based on ActionResult entries
	sections = history_str.split('ActionResult(')

	for i, section in enumerate(sections[1:], 1):  # Skip first empty section
		# Extract relevant information
		content = ''
		if 'extracted_content=' in section:
			content = section.split('extracted_content=')[1].split(',')[0].strip("'")

		if content:
			header = Text(f'Step {i}', style='bold blue')
			panel = Panel(content, title=header, border_style='blue')
			console.print(panel)
			console.print()

	return None


async def run_browser_task(
	task: str,
	api_key: str,
	model: str = 'gpt-4o',
	headless: bool = True,
	provider: str = 'openai',
) -> str:
	if provider == 'openai' and not api_key.strip():
		return 'Please provide an API key'
	if provider == 'openai':
		os.environ['OPENAI_API_KEY'] = api_key
	try:
		if provider == 'ollama':
			llm = ChatOllama(model=model)
		else:
			from browser_use.llm import ChatOpenAI
			llm = ChatOpenAI(model=model)
		agent = Agent(
			task=task,
			llm=llm,
		)
		result = await agent.run()
		return str(result)
	except Exception as e:
		return f'Error: {str(e)}'


def create_ui():
	with gr.Blocks(title='Browser Use GUI') as interface:
		gr.Markdown('# Browser Use Task Automation')
		with gr.Row():
			with gr.Column():
				api_key = gr.Textbox(label='OpenAI API Key', placeholder='sk-...', type='password')
				task = gr.Textbox(
					label='Task Description',
					placeholder='E.g., Find flights from New York to London for next week',
					lines=3,
				)
				provider = gr.Radio(['openai', 'ollama'], value='openai', label='Provider')

				# Dynamic model choices based on provider
				def get_models_choice(provider_selected):
					if provider_selected == 'ollama':
						models = list_local_ollama_models()
						if not models:
							models = ['No local Ollama models found']
						return gr.Dropdown.update(choices=models, value=models[0] if models else None)
					else:
						return gr.Dropdown.update(choices=['gpt-4o', 'gpt-3.5-turbo'], value='gpt-4o')

				model = gr.Dropdown(choices=['gpt-4o', 'gpt-3.5-turbo'], label='Model', value='gpt-4o')
				provider.change(get_models_choice, inputs=provider, outputs=model)

				headless = gr.Checkbox(label='Run Headless', value=True)
				submit_btn = gr.Button('Run Task')

			with gr.Column():
				output = gr.Textbox(label='Output', lines=10, interactive=False)

			submit_btn.click(
				fn=lambda *args: asyncio.run(run_browser_task(*args)),
				inputs=[task, api_key, model, headless, provider],
				outputs=output,
			)
	return interface


if __name__ == '__main__':
	demo = create_ui()
	demo.launch()
