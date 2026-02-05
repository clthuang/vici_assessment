"""Main CLI application entry point."""

import asyncio

import typer
from rich.console import Console

from subterminator import __version__
from subterminator.cli.output import OutputFormatter
from subterminator.cli.prompts import is_interactive, select_service
from subterminator.services.registry import (
    get_available_services,
    get_service_by_id,
    suggest_service,
)

console = Console()

app = typer.Typer(
    name="subterminator",
    help="CLI tool for automating subscription cancellations.",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"SubTerminator v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """SubTerminator - CLI tool for automating subscription cancellations."""
    pass


@app.command(
    epilog="Note: Use 'subterminator cancel --service netflix' or interactive mode."
)
def cancel(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Run without making actual changes (stops at final confirmation)",
    ),
    headless: bool = typer.Option(
        False,
        "--headless",
        help="Run browser in headless mode (no visible window)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-V",
        help="Show detailed progress information",
    ),
    service: str | None = typer.Option(
        None,
        "--service",
        "-s",
        help="Service to cancel (bypasses interactive menu)",
    ),
    no_input: bool = typer.Option(
        False,
        "--no-input",
        help="Disable all interactive prompts",
    ),
    plain: bool = typer.Option(
        False,
        "--plain",
        help="Disable colors and animations",
    ),
    profile_dir: str | None = typer.Option(
        None,
        "--profile-dir",
        help="Use persistent browser profile directory for session persistence",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="LLM model override (default: claude-sonnet-4-20250514)",
    ),
    max_turns: int = typer.Option(
        20,
        "--max-turns",
        help="Maximum orchestration turns",
    ),
    no_checkpoint: bool = typer.Option(
        False,
        "--no-checkpoint",
        help="Disable human checkpoints",
    ),
) -> None:
    """Cancel a subscription service.

    Uses AI-driven MCP orchestration to navigate the cancellation flow.

    Exit codes:
    - 0: Success (cancellation completed)
    - 1: Failure (cancellation failed)
    - 2: User cancelled (via Ctrl+C or menu)
    - 3: Invalid service
    - 5: MCP connection error
    - 130: SIGINT during orchestration
    """
    from dotenv import load_dotenv

    load_dotenv()  # Load .env file before accessing env vars

    from subterminator.mcp_orchestrator import LLMClient, MCPClient, TaskRunner
    from subterminator.mcp_orchestrator.exceptions import (
        ConfigurationError as MCPConfigError,
    )
    from subterminator.mcp_orchestrator.exceptions import MCPConnectionError
    from subterminator.mcp_orchestrator.services import netflix  # noqa: F401

    # Service resolution
    if service:
        service_info = get_service_by_id(service)
        if not service_info:
            suggestion = suggest_service(service)
            available = [s.id for s in get_available_services()]
            typer.echo(f"Error: Unknown service '{service}'.")
            if suggestion:
                typer.echo(f"Did you mean: {suggestion}?")
            typer.echo(f"Available services: {', '.join(available)}")
            raise typer.Exit(code=3)
        elif not service_info.available:
            typer.echo(f"Error: Service '{service}' is not yet available.")
            typer.echo("This service is coming soon.")
            raise typer.Exit(code=3)
        selected_service = service_info.id
    elif is_interactive(no_input):
        selected = select_service(plain=plain)
        if selected is None:
            typer.echo("Cancelled.")
            raise typer.Exit(code=2)
        selected_service = selected
    else:
        typer.echo("Error: --service required in non-interactive mode.")
        typer.echo("Usage: subterminator cancel --service <name>")
        raise typer.Exit(code=3)

    # ToS disclaimer
    formatter = OutputFormatter(verbose=verbose)
    formatter.show_warning(
        "This tool automates browser interactions with subscription services.\n"
        "Use at your own risk. The service's Terms of Service may prohibit automation."
    )

    # MCP Orchestration
    console.print("[bold blue]MCP Orchestration Mode[/bold blue]")
    console.print(f"Service: {selected_service}")
    console.print(f"Max turns: {max_turns}")
    if verbose:
        console.print(f"Model: {model or 'default'}")
        console.print(f"Checkpoints: {'disabled' if no_checkpoint else 'enabled'}")

    try:
        # Create clients
        mcp = MCPClient(profile_dir=profile_dir)
        llm = LLMClient(model_name=model)

        # Create runner
        runner = TaskRunner(
            mcp_client=mcp,
            llm_client=llm,
            disable_checkpoints=no_checkpoint,
        )

        # Run orchestration
        console.print("\n[dim]Starting orchestration...[/dim]\n")

        result = asyncio.run(runner.run(
            service=selected_service,
            max_turns=max_turns,
            dry_run=dry_run,
        ))

        # Display result
        if result.success:
            console.print("\n[green bold]Success![/green bold]")
            console.print(f"Verified: {result.verified}")
            console.print(f"Turns: {result.turns}")
            if result.final_url:
                console.print(f"Final URL: {result.final_url}")
            raise typer.Exit(code=0)
        else:
            console.print("\n[red bold]Failed[/red bold]")
            console.print(f"Reason: {result.reason}")
            console.print(f"Turns: {result.turns}")
            if result.error:
                console.print(f"Error: {result.error}")
            if result.final_url:
                console.print(f"Final URL: {result.final_url}")

            # Map reason to exit code
            if result.reason == "human_rejected" and "SIGINT" in (result.error or ""):
                raise typer.Exit(code=130)
            elif result.reason == "mcp_error":
                raise typer.Exit(code=5)
            else:
                raise typer.Exit(code=1)

    except MCPConfigError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(code=2)
    except MCPConnectionError as e:
        console.print(f"[red]MCP connection error: {e}[/red]")
        raise typer.Exit(code=5)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
        raise typer.Exit(code=130)


if __name__ == "__main__":
    app()
