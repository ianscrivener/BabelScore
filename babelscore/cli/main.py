import click
from babelscore.cli.shell import run_shell


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """BabelScore — LLM translation quality benchmark."""
    if ctx.invoked_subcommand is None:
        run_shell()


def main():
    cli()
