"""Main CLI application entry point."""

import asyncio
from pathlib import Path

import typer
from rich.console import Console

from subterminator import __version__
from subterminator.cli.output import OutputFormatter, PromptType
from subterminator.cli.prompts import is_interactive, select_service
from subterminator.core.agent import AIBrowserAgent
from subterminator.core.ai import (
    ClaudeActionPlanner,
    ClaudeInterpreter,
    HeuristicInterpreter,
)
from subterminator.core.browser import PlaywrightBrowser
from subterminator.core.engine import CancellationEngine
from subterminator.services import create_service, get_mock_pages_dir
from subterminator.services.mock import MockServer
from subterminator.services.registry import (
    get_available_services,
    get_service_by_id,
    suggest_service,
)
from subterminator.utils.config import ConfigLoader
from subterminator.utils.exceptions import ConfigurationError
from subterminator.utils.session import SessionLogger

console = Console()


def _run_mcp_orchestration(
    service: str,
    model: str | None,
    max_turns: int,
    dry_run: bool,
    verbose: bool,
    no_checkpoint: bool,
    profile_dir: str | None,
    formatter: "OutputFormatter",
) -> None:
    """Run AI-driven MCP orchestration.

    Exit codes for --auto mode:
    - 0: Success (TaskResult.success=True)
    - 1: Failure (TaskResult.success=False)
    - 2: Configuration error (missing API key, bad model)
    - 5: MCP connection error
    - 130: SIGINT (user cancelled)
    """
    from dotenv import load_dotenv

    load_dotenv()  # Load .env file before accessing env vars

    from subterminator.mcp_orchestrator import LLMClient, MCPClient, TaskRunner
    from subterminator.mcp_orchestrator.exceptions import (
        ConfigurationError as MCPConfigError,
    )
    from subterminator.mcp_orchestrator.exceptions import MCPConnectionError
    from subterminator.mcp_orchestrator.services import netflix  # noqa: F401

    console.print("[bold blue]MCP Orchestration Mode[/bold blue]")
    console.print(f"Service: {service}")
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
            service=service,
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
    target: str = typer.Option(
        "live",
        "--target",
        "-t",
        help="Target environment: 'live' for real site, 'mock' for local testing",
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
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Directory for session artifacts (screenshots, logs)",
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
    cdp_url: str | None = typer.Option(
        None,
        "--cdp-url",
        help="Connect to existing Chrome via CDP URL. Start Chrome with: "
        "chrome --remote-debugging-port=9222",
    ),
    profile_dir: str | None = typer.Option(
        None,
        "--profile-dir",
        help="Use persistent browser profile directory for session persistence",
    ),
    use_chromium: bool = typer.Option(
        False,
        "--use-chromium",
        help="Use Playwright's Chromium instead of system Chrome (for testing/CI)",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable AI debug logging (saves all requests/responses to session dir)",
    ),
    # MCP Orchestration options
    auto: bool = typer.Option(
        False,
        "--auto",
        help="Use AI-driven MCP orchestration (experimental)",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="LLM model override for --auto mode (default: claude-sonnet-4-20250514)",
    ),
    max_turns: int = typer.Option(
        20,
        "--max-turns",
        help="Maximum orchestration turns for --auto mode",
    ),
    no_checkpoint: bool = typer.Option(
        False,
        "--no-checkpoint",
        help="Disable human checkpoints in --auto mode",
    ),
) -> None:
    """Cancel a subscription service."""
    # Validate mutual exclusivity of browser options early (before browser init)
    if cdp_url and profile_dir:
        console.print(
            "[red]Error:[/red] --cdp-url and --profile-dir cannot be used together"
        )
        raise typer.Exit(code=1)

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

    # T15.7: ToS disclaimer
    formatter = OutputFormatter(verbose=verbose)
    formatter.show_warning(
        "This tool automates browser interactions with subscription services.\n"
        "Use at your own risk. The service's Terms of Service may prohibit automation."
    )

    # MCP Orchestration mode (--auto flag)
    if auto:
        _run_mcp_orchestration(
            service=selected_service,
            model=model,
            max_turns=max_turns,
            dry_run=dry_run,
            verbose=verbose,
            no_checkpoint=no_checkpoint,
            profile_dir=profile_dir,
            formatter=formatter,
        )
        return  # _run_mcp_orchestration handles exit

    try:
        # Load configuration
        config = ConfigLoader.load()
        if output_dir:
            config.output_dir = output_dir

        # Start mock server if using mock target
        mock_server = None
        if target == "mock":
            mock_pages_path = get_mock_pages_dir(selected_service)
            project_root = Path(__file__).parent.parent.parent.parent
            mock_pages_dir = project_root / mock_pages_path
            if not mock_pages_dir.exists():
                console.print(
                    f"[red]Error: Mock pages not found at {mock_pages_dir}[/red]"
                )
                raise typer.Exit(code=4)
            mock_server = MockServer(mock_pages_dir, port=8000)
            mock_server.start()

        # Create components
        service_obj = create_service(selected_service, target)

        # Determine browser mode: default to system Chrome unless --use-chromium
        effective_cdp_url = cdp_url
        if not use_chromium and not cdp_url and not profile_dir:
            # Default: launch system Chrome with remote debugging
            from subterminator.core.browser import launch_system_chrome

            if verbose:
                console.print("[dim]Launching system Chrome...[/dim]")
            effective_cdp_url = launch_system_chrome()
            if verbose:
                console.print(f"[dim]Connected via {effective_cdp_url}[/dim]")

        browser = PlaywrightBrowser(
            headless=headless,
            cdp_url=effective_cdp_url,
            user_data_dir=profile_dir,
        )
        heuristic = HeuristicInterpreter()

        # Create AI interpreter if API key available
        ai = None
        if config.anthropic_api_key:
            ai = ClaudeInterpreter(api_key=config.anthropic_api_key)
        elif verbose:
            formatter.show_warning("No ANTHROPIC_API_KEY set - AI detection disabled")

        # Create session logger
        session = SessionLogger(
            output_dir=config.output_dir,
            service=selected_service,
            target=target,
        )

        # Create input callback for human checkpoints
        def input_callback(checkpoint_type: str, timeout: int) -> str | None:
            prompt_type_map = {
                "AUTH": PromptType.AUTH,
                "CONFIRM": PromptType.CONFIRM,
                "UNKNOWN": PromptType.UNKNOWN,
            }
            prompt_type = prompt_type_map.get(checkpoint_type, PromptType.UNKNOWN)
            return formatter.show_human_prompt(prompt_type, timeout)

        # Create AI agent if API key available
        agent = None
        if config.anthropic_api_key:
            planner = ClaudeActionPlanner(
                api_key=config.anthropic_api_key,
                debug=debug,
                session_dir=session.session_dir if debug else None,
            )
            agent = AIBrowserAgent(
                browser=browser,
                planner=planner,
                heuristic=heuristic,
                service=service_obj,
                input_callback=input_callback,
                output_callback=formatter.show_progress,
                debug=debug,
                session_dir=session.session_dir if debug else None,
            )
        elif verbose:
            formatter.show_warning("No ANTHROPIC_API_KEY set - AI agent disabled")

        # Create engine
        engine = CancellationEngine(
            service=service_obj,
            browser=browser,
            heuristic=heuristic,
            ai=ai,
            session=session,
            config=config,
            output_callback=formatter.show_progress,
            input_callback=input_callback,
            agent=agent,
        )

        # Show dry-run notice
        if dry_run:
            formatter.show_dry_run_notice()

        try:
            # Run the cancellation
            result = asyncio.run(engine.run(dry_run=dry_run))

            # T15.6: Exit code handling
            if result.success:
                formatter.show_success(result)
                raise typer.Exit(code=0)
            elif result.state.name == "ABORTED":
                print("\nOperation aborted.")
                raise typer.Exit(code=2)
            else:
                formatter.show_failure(result)
                raise typer.Exit(code=1)
        finally:
            # Stop mock server if it was started
            if mock_server:
                mock_server.stop()

    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(code=4)


if __name__ == "__main__":
    app()
