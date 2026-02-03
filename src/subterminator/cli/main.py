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

app = typer.Typer(
    name="subterminator",
    help="CLI tool for automating subscription cancellations.",
    no_args_is_help=True,
)


SUPPORTED_SERVICES = ["netflix"]


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


@app.command()
def cancel(
    service: str = typer.Argument(
        ...,
        help="Service to cancel (currently only 'netflix' supported)",
    ),
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
) -> None:
    """Cancel a subscription service."""
    # T15.5: Service validation
    if service.lower() not in SUPPORTED_SERVICES:
        print(f"\033[31mError: Unsupported service '{service}'.\033[0m")
        print(f"Supported services: {', '.join(SUPPORTED_SERVICES)}")
        raise typer.Exit(code=3)  # Invalid args

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
            service=service.lower(),
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
