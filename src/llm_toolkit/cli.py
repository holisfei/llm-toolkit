"""命令行聊天工具 —— llm-toolkit 的用户面。
设计:一个简单 REPL(Read-Eval-Print Loop),多轮对话,流式输出。
今天范围严格:可选模型、多轮、流式、/quit 退出
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from llm_toolkit.client import LLM
from llm_toolkit.types import Message, Role

app = typer.Typer(help="llm-toolkit 命令行聊天工具")
console = Console()

@app.command()
def chat(
    model: Annotated[
        str,      
        typer.Option(
            "--model",
            "-m",
            help="要使用的模型,如 deepseek-v4-flash / claude-sonnet-4-6 / glm-4.7")
    ] = "deepseek-v4-flash",
    system: Annotated[
        str | None, 
        typer.Option(
            "--system", 
            "-s", 
            help="可选的 system prompt")
    ] = None
) -> None:
    """启动交互式聊天。"""
    asyncio.run(_chat_loop(model=model, system=system))

async def _chat_loop(model: str, system: str | None) -> None:  
    """异步主循环。Typer 命令(同步)调用 asyncio.run 进到这里。"""

    # 保存历史
    messages:list[Message] = []

    # Step 1:构造 LLM 实例和历史列表
    llm = LLM(model)
    if system is not None:
        messages.append(Message(role=Role.SYSTEM, content=system))
    
    # Step 2:打印欢迎信息(用 console.print,可加颜色)
    welcome_text = Text("✨ 欢迎使用 llm-toolkit ✨", justify="center")
    model_info = Text(
        "\n\n🤖 当前模型: ",               
        style="bold dim cyan") + Text(model, style="bold yellow"
    )
    hint_text = Text(
        "\n💡 输入你的问题开始对话，输入 /exit 退出。", 
        justify="center", style="italic green"
    )
    panel_content = welcome_text + model_info + hint_text
    console.print(
        Panel(
            panel_content,
            title="[bold magenta]llm-toolkit cli[/]",
            border_style="bright_blue",
            padding=(1, 2),
            expand=False         
        )
    )

    # Step 3:进入 REPL 循环 while True:
    while True:
        try:
            # 3.1 用 console.input("[bold cyan]You>[/] ") 读用户输入
            user_input: str = console.input("[bold white]You>[/] ")
            # 3.2 strip 一下,空输入 continue
            input_text = user_input.strip()
            if len(input_text) == 0:
                continue
            # 3.3 处理退出命令:输入是 "/exit" 就 break
            if input_text == "/exit":
                console.print(f"[dim]{llm.cost_tracker.summary()}[/]")
                console.print("\n[dim]再见![/]")
                break
            # 3.4 把用户输入 append 成 USER message 到 history
            messages.append(Message(role=Role.USER, content=input_text))
            # 3.5 调用流式接口:
            full_reply: str = ""
            print("Assistant> ")
            async for chunk in llm.stream_chat(messages):
                print(chunk.chunk, end="", flush=True)
                full_reply += chunk.chunk
            print()
            # 3.6 把完整回复 append 成 ASSISTANT message 到 history
            messages.append(Message(role=Role.ASSISTANT, content=full_reply))
        except (EOFError, KeyboardInterrupt): # Ctrl-D/Ctrl-C(EOF)
            console.print(f"[dim]{llm.cost_tracker.summary()}[/]")
            console.print("\n[dim]再见![/]")
            break


@app.command()
def version() -> None:
    """显示版本号"""
    typer.echo("llm-toolkit v0.1.0")

def main() -> None:
    """供 pyproject.toml 的 entry-point 调用。"""
    app()


if __name__ == "__main__":
    main()