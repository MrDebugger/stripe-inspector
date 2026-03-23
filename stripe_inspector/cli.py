"""CLI interface for StripeInspector."""

import json
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from stripe_inspector import __version__
from stripe_inspector.core import StripeInspector, ALL_MODULES
from stripe_inspector.export import result_to_csv
from stripe_inspector.report import generate_html_report
from stripe_inspector.utils import format_timestamp


def version_callback(value: bool):
    if value:
        print(f"stripe-inspector {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="stripe-inspector",
    help="Security research tool to enumerate and inspect Stripe API keys.",
    add_completion=False,
)
console = Console()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(None, "--version", "-V", callback=version_callback, is_eager=True, help="Show version"),
):
    pass


def render_account(data: dict):
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan", width=24)
    table.add_column("Value")

    table.add_row("Account ID", data.get("id", "N/A"))
    table.add_row("Business Name", data.get("business_name") or "N/A")
    table.add_row("Display Name", data.get("display_name") or "N/A")
    table.add_row("Email", data.get("email") or "N/A")
    table.add_row("Country", data.get("country") or "N/A")
    table.add_row("Currency", data.get("default_currency") or "N/A")
    table.add_row("Business Type", data.get("business_type") or "N/A")
    table.add_row("Type", data.get("type") or "N/A")
    table.add_row("Charges Enabled", str(data.get("charges_enabled", "N/A")))
    table.add_row("Payouts Enabled", str(data.get("payouts_enabled", "N/A")))
    table.add_row("Statement Descriptor", data.get("statement_descriptor") or "N/A")
    table.add_row("URL", data.get("url") or "N/A")
    table.add_row("Support Phone", data.get("support_phone") or "N/A")
    table.add_row("MCC", data.get("mcc") or "N/A")

    individual = data.get("individual", {})
    if individual:
        name = f"{individual.get('first_name', '')} {individual.get('last_name', '')}".strip()
        if name:
            table.add_row("Owner Name", name)
        if individual.get("email"):
            table.add_row("Owner Email", individual["email"])
        if individual.get("title"):
            table.add_row("Owner Title", individual["title"])

    addr = data.get("address", {})
    if addr and any(addr.values()):
        parts = [v for v in [addr.get("line1"), addr.get("city"), addr.get("state"), addr.get("postal_code"), addr.get("country")] if v]
        table.add_row("Address", ", ".join(parts))

    caps = data.get("capabilities", {})
    if caps:
        table.add_row("Capabilities", ", ".join(caps.keys()))

    schedule = data.get("payout_schedule", {})
    if schedule:
        table.add_row("Payout Schedule", f"{schedule.get('interval', 'N/A')} ({schedule.get('delay_days', '?')} day delay)")

    return table


def render_balance(data: dict):
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("Type", style="bold")
    table.add_column("Amount", justify="right")
    table.add_column("Currency")

    for item in data.get("available", []):
        table.add_row("Available", f"{item['amount']:.2f}", item["currency"].upper())
    for item in data.get("pending", []):
        table.add_row("Pending", f"{item['amount']:.2f}", item["currency"].upper())

    return table


def render_list_table(data: dict, key: str, columns: list[tuple[str, str]]):
    items = data.get(key, [])
    if not items:
        return f"[dim]No {key} found[/dim]"

    table = Table(show_header=True, box=None, padding=(0, 2))
    for col_name, _ in columns:
        table.add_column(col_name, style="bold" if col_name == "ID" else None)

    timestamp_fields = {"created", "arrival_date", "current_period_start", "current_period_end"}

    for item in items[:20]:
        row = []
        for _, field in columns:
            val = item.get(field, "")
            if val is None:
                val = ""
            elif field in timestamp_fields and isinstance(val, (int, float)):
                val = format_timestamp(val)
            row.append(str(val))
        table.add_row(*row)

    count = data.get("count", len(items))
    has_more = data.get("has_more", False)
    suffix = f"\n[dim]Showing {min(20, count)} of {count}{'+ (has_more)' if has_more else ''}[/dim]"

    return table, suffix


MODULE_RENDERERS = {
    "account": lambda d: (render_account(d), ""),
    "balance": lambda d: (render_balance(d), ""),
    "customers": lambda d: render_list_table(d, "customers", [
        ("ID", "id"), ("Name", "name"), ("Email", "email"), ("Country", "country"),
    ]),
    "charges": lambda d: render_list_table(d, "charges", [
        ("ID", "id"), ("Amount", "amount"), ("Currency", "currency"), ("Payer", "payer_name"), ("Email", "payer_email"), ("Card", "card_last4"),
    ]),
    "payment_intents": lambda d: render_list_table(d, "intents", [
        ("ID", "id"), ("Amount", "amount"), ("Currency", "currency"), ("Status", "status"),
    ]),
    "products": lambda d: render_list_table(d, "products", [
        ("ID", "id"), ("Name", "name"), ("Type", "type"), ("Active", "active"),
    ]),
    "payouts": lambda d: render_list_table(d, "payouts", [
        ("ID", "id"), ("Amount", "amount"), ("Currency", "currency"), ("Status", "status"),
    ]),
    "subscriptions": lambda d: render_list_table(d, "subscriptions", [
        ("ID", "id"), ("Customer", "customer"), ("Status", "status"), ("Currency", "currency"),
    ]),
    "invoices": lambda d: render_list_table(d, "invoices", [
        ("ID", "id"), ("Customer", "customer"), ("Amount Due", "amount_due"), ("Status", "status"),
    ]),
    "webhooks": lambda d: render_list_table(d, "endpoints", [
        ("ID", "id"), ("URL", "url"), ("Status", "status"),
    ]),
    "events": lambda d: render_list_table(d, "events", [
        ("ID", "id"), ("Type", "type"), ("Live", "livemode"),
    ]),
    "connected": lambda d: render_list_table(d, "accounts", [
        ("ID", "id"), ("Email", "email"), ("Country", "country"), ("Type", "type"),
    ]),
    "disputes": lambda d: render_list_table(d, "disputes", [
        ("ID", "id"), ("Amount", "amount"), ("Currency", "currency"), ("Status", "status"), ("Reason", "reason"),
    ]),
    "refunds": lambda d: render_list_table(d, "refunds", [
        ("ID", "id"), ("Amount", "amount"), ("Currency", "currency"), ("Status", "status"), ("Reason", "reason"),
    ]),
    "balance_transactions": lambda d: render_list_table(d, "transactions", [
        ("ID", "id"), ("Amount", "amount"), ("Net", "net"), ("Fee", "fee"), ("Type", "type"),
    ]),
    "coupons": lambda d: render_list_table(d, "coupons", [
        ("ID", "id"), ("Name", "name"), ("% Off", "percent_off"), ("Valid", "valid"),
    ]),
    "permission_scan": lambda d: (render_permission_scan(d), ""),
}


def render_permission_scan(data: dict):
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Status", width=3)
    table.add_column("Endpoint")

    for name in data.get("allowed", []):
        table.add_row("[green]OK[/green]", name)
    for name in data.get("denied", []):
        table.add_row("[red]NO[/red]", name)
    for err in data.get("errors", []):
        table.add_row("[yellow]??[/yellow]", f"{err['endpoint']} ({err.get('error', '')})")

    console.print(f"  [green]{data.get('allowed_count', 0)}[/green] allowed / "
                  f"[red]{data.get('denied_count', 0)}[/red] denied / "
                  f"[yellow]{data.get('error_count', 0)}[/yellow] errors "
                  f"out of {data.get('total_endpoints', 0)} endpoints\n")

    return table


def display_results(result: dict):
    # Key info header
    key_type = result.get("key_type", "unknown")
    is_live = result.get("is_live", False)
    style = "bold red" if is_live else "bold yellow"
    label = "LIVE KEY" if is_live else "TEST KEY"
    if result.get("is_restricted"):
        label = f"RESTRICTED {label}"

    console.print()
    console.print(Panel(
        f"[{style}]{label}[/{style}]  {result['masked_key']}\n"
        f"[dim]{result.get('timestamp', '')}[/dim]",
        title="[bold]StripeInspector[/bold]",
        border_style="bright_blue",
    ))

    # Permissions summary
    perms = result.get("permissions", {})
    allowed = sum(1 for v in perms.values() if v == "allowed")
    denied = sum(1 for v in perms.values() if v == "denied")
    errors = sum(1 for v in perms.values() if v == "error")
    console.print(f"\n[bold]Permissions:[/bold] [green]{allowed} allowed[/green] | [red]{denied} denied[/red] | [yellow]{errors} errors[/yellow]\n")

    # Module results
    for name, module_result in result.get("modules", {}).items():
        if not module_result.get("success"):
            console.print(f"[bold]{name.upper()}[/bold]: [red]{module_result.get('error', 'Failed')}[/red]\n")
            continue

        data = module_result["data"]
        renderer = MODULE_RENDERERS.get(name)

        if renderer:
            output = renderer(data)
            if isinstance(output, tuple):
                table, suffix = output
                console.print(f"[bold bright_blue]{name.upper()}[/bold bright_blue]")
                if isinstance(table, str):
                    console.print(table)
                else:
                    console.print(table)
                if suffix:
                    console.print(suffix)
            else:
                console.print(f"[bold bright_blue]{name.upper()}[/bold bright_blue]")
                console.print(output)
        else:
            console.print(f"[bold bright_blue]{name.upper()}[/bold bright_blue]")
            console.print(f"[dim]{json.dumps(data, indent=2, default=str)[:500]}[/dim]")

        console.print()

    # PII Summary
    pii = result.get("pii", {})
    if pii.get("total_pii_items", 0) > 0:
        console.print("[bold bright_blue]PII EXPOSURE SUMMARY[/bold bright_blue]")
        pii_table = Table(show_header=False, box=None, padding=(0, 2))
        pii_table.add_column("Type", style="bold cyan", width=16)
        pii_table.add_column("Count", justify="right", width=6)
        pii_table.add_column("Samples")

        for label, key_name in [("Emails", "emails"), ("Names", "names"), ("Phones", "phones"),
                                 ("Cards", "cards"), ("Countries", "countries")]:
            items = pii.get(key_name, [])
            if items:
                samples = ", ".join(items[:5])
                if len(items) > 5:
                    samples += f" (+{len(items) - 5} more)"
                pii_table.add_row(label, str(len(items)), samples)

        console.print(pii_table)
        console.print()

    # Footer: rate limit + duration
    footer_parts = []
    rl = result.get("rate_limit", {})
    if rl.get("total_requests"):
        footer_parts.append(f"API requests: {rl['total_requests']}")
        if rl.get("remaining") is not None:
            footer_parts.append(f"Rate limit remaining: {rl['remaining']}")
    dur = result.get("duration_seconds")
    if dur is not None:
        footer_parts.append(f"Scan completed in {dur}s")
    if footer_parts:
        console.print(f"[dim]{' | '.join(footer_parts)}[/dim]")
        console.print()


@app.command()
def inspect(
    key: str = typer.Argument(..., help="Stripe API key to inspect"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table, json"),
    report: Optional[str] = typer.Option(None, "--report", "-r", help="Generate HTML report to file"),
    pdf: Optional[str] = typer.Option(None, "--pdf", help="Generate PDF report to file"),
    csv_dir: Optional[str] = typer.Option(None, "--csv", help="Export per-module CSV files to directory"),
    modules: Optional[str] = typer.Option(None, "--modules", "-m", help="Comma-separated modules to run"),
    deep: bool = typer.Option(False, "--deep", "-d", help="Fetch all pages (not just first 100)"),
    silent: bool = typer.Option(False, "--silent", "-s", help="Suppress table output (use with --report/--csv/--json)"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output"),
):
    """Inspect a Stripe API key and enumerate accessible data."""
    if no_color:
        console.no_color = True

    module_list = None
    if modules:
        module_list = [m.strip() for m in modules.split(",")]
        invalid = [m for m in module_list if m not in ALL_MODULES]
        if invalid:
            console.print(f"[red]Unknown modules: {', '.join(invalid)}[/red]")
            console.print(f"[dim]Available: {', '.join(ALL_MODULES.keys())}[/dim]")
            raise typer.Exit(1)

    inspector = StripeInspector(key, modules=module_list, deep=deep)

    if not inspector.validate_key():
        console.print("[red]Invalid key format.[/red] Expected: sk_test_*, sk_live_*, rk_test_*, rk_live_*")
        raise typer.Exit(1)

    if deep:
        console.print("[bold yellow]DEEP MODE: Fetching all pages (this may take a while).[/bold yellow]\n")

    if inspector.key_type and "live" in inspector.key_type:
        console.print("[bold red]WARNING: This is a LIVE key. Data accessed is real.[/bold red]\n")

    import threading, itertools

    spinner_running = True
    spinner_text = "Starting..."

    def spinner_thread():
        frames = itertools.cycle(["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"])
        while spinner_running:
            sys.stderr.write(f"\r  {next(frames)} {spinner_text}" + " " * 20)
            sys.stderr.flush()
            import time; time.sleep(0.08)

    t = threading.Thread(target=spinner_thread, daemon=True)
    t.start()

    def on_progress(module_name: str):
        nonlocal spinner_text
        spinner_text = f"Scanning {module_name}..."

    result = inspector.inspect(progress_callback=on_progress)
    spinner_running = False
    t.join(timeout=0.2)
    sys.stderr.write("\r  Done." + " " * 40 + "\n")
    sys.stderr.flush()

    if output == "json":
        print(json.dumps(result, indent=2, default=str))
    elif not silent:
        display_results(result)

    if report:
        html = generate_html_report(result)
        with open(report, "w", encoding="utf-8") as f:
            f.write(html)
        console.print(f"[green]HTML report saved to {report}[/green]")

    if pdf:
        try:
            from stripe_inspector.report import generate_pdf_report
            pdf_bytes = generate_pdf_report(result)
            with open(pdf, "wb") as f:
                f.write(pdf_bytes)
            console.print(f"[green]PDF report saved to {pdf}[/green]")
        except ImportError as e:
            console.print(f"[red]{e}[/red]")

    if csv_dir:
        import os
        os.makedirs(csv_dir, exist_ok=True)
        csvs = result_to_csv(result)
        for mod_name, csv_content in csvs.items():
            path = os.path.join(csv_dir, f"{mod_name}.csv")
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(csv_content)
        console.print(f"[green]CSV files saved to {csv_dir}/ ({len(csvs)} files)[/green]")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
    token: Optional[str] = typer.Option(None, "--token", "-t", help="Bearer token for API auth"),
):
    """Start the web UI server."""
    import uvicorn
    from stripe_inspector.web.app import create_app

    web_app = create_app(token=token)

    console.print(Panel(
        f"[bold green]StripeInspector Web UI[/bold green]\n\n"
        f"URL: [link]http://{host}:{port}[/link]\n"
        f"Auth: {'[yellow]Token required[/yellow]' if token else '[dim]None (local only)[/dim]'}",
        border_style="bright_blue",
    ))

    uvicorn.run(web_app, host=host, port=port, log_level="warning")


@app.command(name="list-modules")
def list_modules():
    """List available inspection modules."""
    table = Table(title="Available Modules", show_header=True)
    table.add_column("Module", style="bold cyan")
    table.add_column("Endpoint")

    endpoints = {
        "account": "/v1/account",
        "balance": "/v1/balance",
        "customers": "/v1/customers",
        "charges": "/v1/charges",
        "payment_intents": "/v1/payment_intents",
        "products": "/v1/products",
        "payouts": "/v1/payouts",
        "subscriptions": "/v1/subscriptions",
        "invoices": "/v1/invoices",
        "webhooks": "/v1/webhook_endpoints",
        "events": "/v1/events",
        "connected": "/v1/accounts",
        "disputes": "/v1/disputes",
        "refunds": "/v1/refunds",
        "balance_transactions": "/v1/balance_transactions",
        "coupons": "/v1/coupons",
        "permission_scan": "all endpoints (35+)",
    }

    for name in ALL_MODULES:
        table.add_row(name, endpoints.get(name, ""))

    console.print(table)


@app.command()
def batch(
    file: str = typer.Argument(..., help="File containing one Stripe key per line"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table, json"),
    report_dir: Optional[str] = typer.Option(None, "--report-dir", help="Directory to save HTML reports per key"),
    modules: Optional[str] = typer.Option(None, "--modules", "-m", help="Comma-separated modules to run"),
    deep: bool = typer.Option(False, "--deep", "-d", help="Fetch all pages"),
):
    """Batch inspect multiple Stripe keys from a file."""
    import os

    try:
        with open(file, "r") as f:
            keys = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1)

    if not keys:
        console.print("[red]No keys found in file.[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Found {len(keys)} key(s) to inspect.[/bold]\n")

    if report_dir:
        os.makedirs(report_dir, exist_ok=True)

    module_list = None
    if modules:
        module_list = [m.strip() for m in modules.split(",")]

    all_results = []

    for i, key in enumerate(keys, 1):
        inspector = StripeInspector(key, modules=module_list, deep=deep)

        if not inspector.validate_key():
            console.print(f"[{i}/{len(keys)}] [red]Invalid key: {inspector.masked_key}[/red]")
            continue

        console.print(f"[{i}/{len(keys)}] Inspecting {inspector.masked_key}...")
        result = inspector.inspect()
        all_results.append(result)

        if output == "table":
            display_results(result)
            console.print("[dim]" + "-" * 60 + "[/dim]\n")

        if report_dir:
            html = generate_html_report(result)
            safe_name = inspector.masked_key.replace("...", "_").replace("*", "")
            report_path = os.path.join(report_dir, f"{safe_name}.html")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(html)
            console.print(f"  [green]Report: {report_path}[/green]")

    if output == "json":
        print(json.dumps(all_results, indent=2, default=str))

    console.print(f"\n[bold green]Batch complete: {len(all_results)}/{len(keys)} keys inspected.[/bold green]")


@app.command()
def diff(
    key1: str = typer.Argument(..., help="First Stripe API key"),
    key2: str = typer.Argument(..., help="Second Stripe API key"),
    modules: Optional[str] = typer.Option(None, "--modules", "-m", help="Comma-separated modules to run"),
):
    """Compare permissions and data between two Stripe keys."""
    module_list = None
    if modules:
        module_list = [m.strip() for m in modules.split(",")]

    # Default to permission_scan for diff
    if not module_list:
        module_list = ["account", "permission_scan"]

    console.print("[bold]Inspecting key 1...[/bold]")
    i1 = StripeInspector(key1, modules=module_list)
    if not i1.validate_key():
        console.print("[red]Key 1: Invalid format[/red]")
        raise typer.Exit(1)
    r1 = i1.inspect()

    console.print("[bold]Inspecting key 2...[/bold]")
    i2 = StripeInspector(key2, modules=module_list)
    if not i2.validate_key():
        console.print("[red]Key 2: Invalid format[/red]")
        raise typer.Exit(1)
    r2 = i2.inspect()

    # Display comparison
    console.print()
    console.print(Panel(
        f"Key 1: [cyan]{r1['masked_key']}[/cyan]  ({r1.get('key_type', '?')})\n"
        f"Key 2: [cyan]{r2['masked_key']}[/cyan]  ({r2.get('key_type', '?')})",
        title="[bold]Diff[/bold]",
        border_style="bright_blue",
    ))

    # Compare permissions
    p1 = r1.get("permissions", {})
    p2 = r2.get("permissions", {})
    all_mods = sorted(set(list(p1.keys()) + list(p2.keys())))

    if all_mods:
        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("Module", style="bold")
        table.add_column("Key 1")
        table.add_column("Key 2")
        table.add_column("Match")

        for mod in all_mods:
            v1 = p1.get(mod, "-")
            v2 = p2.get(mod, "-")
            c1 = "green" if v1 == "allowed" else "red" if v1 == "denied" else "yellow"
            c2 = "green" if v2 == "allowed" else "red" if v2 == "denied" else "yellow"
            match = "[green]=[/green]" if v1 == v2 else "[red]![/red]"
            table.add_row(mod, f"[{c1}]{v1}[/{c1}]", f"[{c2}]{v2}[/{c2}]", match)

        console.print("\n[bold]Permission Comparison:[/bold]")
        console.print(table)

    # Compare permission_scan if available
    ps1 = r1.get("modules", {}).get("permission_scan", {})
    ps2 = r2.get("modules", {}).get("permission_scan", {})
    if ps1.get("success") and ps2.get("success"):
        a1 = set(ps1["data"].get("allowed", []))
        a2 = set(ps2["data"].get("allowed", []))
        only1 = sorted(a1 - a2)
        only2 = sorted(a2 - a1)
        both = sorted(a1 & a2)

        console.print(f"\n[bold]Endpoint Access:[/bold]")
        console.print(f"  [green]Both keys:[/green] {len(both)} endpoints")
        if only1:
            console.print(f"  [cyan]Only key 1:[/cyan] {', '.join(only1)}")
        if only2:
            console.print(f"  [cyan]Only key 2:[/cyan] {', '.join(only2)}")
        if not only1 and not only2:
            console.print(f"  [dim]Keys have identical access[/dim]")

    # Compare account info
    ac1 = r1.get("modules", {}).get("account", {})
    ac2 = r2.get("modules", {}).get("account", {})
    if ac1.get("success") and ac2.get("success"):
        d1 = ac1["data"]
        d2 = ac2["data"]
        same_account = d1.get("id") == d2.get("id")
        console.print(f"\n[bold]Account:[/bold] {'[green]Same account[/green]' if same_account else '[yellow]Different accounts[/yellow]'}")
        if not same_account:
            console.print(f"  Key 1: {d1.get('display_name', 'N/A')} ({d1.get('id', 'N/A')})")
            console.print(f"  Key 2: {d2.get('display_name', 'N/A')} ({d2.get('id', 'N/A')})")

    console.print()


if __name__ == "__main__":
    app()
