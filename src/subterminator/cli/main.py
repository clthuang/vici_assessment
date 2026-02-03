"""Main CLI application entry point."""

import asyncio
from pathlib import Path

import typer

from subterminator import __version__
from subterminator.cli.output import OutputFormatter, PromptType
from subterminator.core.ai import ClaudeInterpreter, HeuristicInterpreter
from subterminator.core.browser import PlaywrightBrowser
from subterminator.core.engine import CancellationEngine
from subterminator.services.mock import MockServer
from subterminator.services.netflix import NetflixService
from subterminator.utils.config import ConfigLoader
from subterminator.utils.exceptions import ConfigurationError
from subterminator.utils.session import SessionLogger
from subterminator.services.registry import get_service_by_id, suggest_service, get_available_services
from subterminator.cli.prompts import is_interactive, select_service

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


@app.command(epilog="Migration note: The positional syntax 'subterminator cancel netflix' is deprecated. Use '--service netflix' instead.")
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
) -> None:
    """Cancel a subscription service."""
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
        selected_service = select_service(plain=plain)
        if selected_service is None:
            typer.echo("Cancelled.")
            raise typer.Exit(code=2)
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

    try:
        # Load configuration
        config = ConfigLoader.load()
        if output_dir:
            config.output_dir = output_dir

        # Start mock server if using mock target
        mock_server = None
        if target == "mock":
            mock_pages_dir = (
                Path(__file__).parent.parent.parent.parent / "mock_pages" / "netflix"
            )
            if not mock_pages_dir.exists():
                print(f"\033[31mError: Mock pages not found at {mock_pages_dir}\033[0m")
                raise typer.Exit(code=4)
            mock_server = MockServer(mock_pages_dir, port=8000)
            mock_server.start()

        # Create components
        service_obj = NetflixService(target=target)
        browser = PlaywrightBrowser(headless=headless)
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
        print(f"\033[31mConfiguration error: {e}\033[0m")
        raise typer.Exit(code=4)


if __name__ == "__main__":
    app()
