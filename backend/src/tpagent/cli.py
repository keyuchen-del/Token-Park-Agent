"""tpagent CLI — 本地命令行入口。"""

from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from tpagent import __version__
from tpagent.agents import ArticleWriter, WriteRequest
from tpagent.agents.ops_writer import OpsWriter, OpsWriteRequest
from tpagent.agents.topic_researcher import TopicResearcher, TopicResearchRequest
from tpagent.grep import GrepReport, scan_directory, scan_file
from tpagent.services.ops_parser import filter_required, parse_ops_images, specs_summary
from tpagent.storage import save_article, save_ops
from tpagent.storage.session import (
    SessionStage,
    create_session,
    estimate_cost,
    list_sessions,
    update_session,
)

app = typer.Typer(
    name="tpagent",
    help="Token 公园内容生产 Agent CLI",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _print_grep_report(report: GrepReport) -> None:
    """打印 grep 报告。"""
    table = Table(title="📋 发布前 grep 扫描", show_header=True)
    table.add_column("规则", style="cyan")
    table.add_column("命中数", justify="right", style="magenta")
    table.add_column("状态")
    for rule_id, count in report.rule_summary.items():
        status = "✅" if count == 0 else "❌"
        table.add_row(rule_id, str(count), status)
    console.print(table)

    if report.hits:
        console.print("\n[red]❌ 必须修复的命中：[/red]")
        for h in report.hits:
            console.print(
                f"  [{h.rule_name}] {Path(h.file).name}:{h.line_no}\n"
                f"      [yellow]{h.matched_text!r}[/yellow]"
                f" — {h.line_content.strip()[:100]}"
            )

    if report.exceptions:
        console.print("\n[yellow]⚠️  例外（需人工判断）：[/yellow]")
        for h in report.exceptions:
            console.print(
                f"  [{h.rule_name}] {Path(h.file).name}:{h.line_no} — [dim]{h.matched_text!r}[/dim]"
            )

    if report.can_publish:
        console.print("\n[bold green]✅ 可以发布[/bold green]")
    else:
        console.print("\n[bold red]❌ 不能发布，先修复上方命中[/bold red]")


def _print_token_usage(
    input_tokens: int,
    output_tokens: int,
    cache_read: int = 0,
    cache_creation: int = 0,
) -> None:
    """打印 token 用量 + 成本估算。"""
    cost = estimate_cost(input_tokens, output_tokens, cache_read, cache_creation)
    table = Table(title="💰 Token 用量", show_header=True)
    table.add_column("项", style="cyan")
    table.add_column("数值", justify="right", style="magenta")
    table.add_row("Input tokens", f"{input_tokens:,}")
    table.add_row("Output tokens", f"{output_tokens:,}")
    table.add_row("Cache read", f"{cache_read:,}")
    table.add_row("Cache creation", f"{cache_creation:,}")
    table.add_row("[bold]估算成本[/bold]", f"[bold]${cost:.4f}[/bold]")
    console.print(table)


# ============================================================
# version
# ============================================================
@app.command()
def version() -> None:
    """打印版本号."""
    console.print(f"[bold cyan]token-park-agent[/bold cyan] v{__version__}")


# ============================================================
# topics
# ============================================================
@app.command()
def topics(
    direction: str = typer.Option(..., "--direction", "-d", help="选题方向，一句话"),
    seed_links: list[str] = typer.Option(None, "--link", "-l", help="信源链接（可多次）"),
    avoid: list[str] = typer.Option(None, "--avoid", help="避免撞稿的近期选题（可多次）"),
) -> None:
    """拉今日热点 + 整理候选清单。

    示例：
        tpagent topics --direction "今天 AI 圈和国内科技圈"
        tpagent topics -d "国内 AI 资本开支" -l https://xxx -l https://yyy
    """
    console.print(
        Panel.fit(
            f"[bold]方向:[/bold] {direction}\n"
            + (f"[bold]信源:[/bold] {', '.join(seed_links)}\n" if seed_links else "")
            + (f"[bold]避免撞稿:[/bold] {', '.join(avoid)}" if avoid else ""),
            title="🔍 选题研究",
            border_style="cyan",
        )
    )

    researcher = TopicResearcher()
    with console.status("[cyan]Claude 拉热点 + 整理候选... 约 30-90 秒[/cyan]"):
        result = researcher.research(
            TopicResearchRequest(
                direction=direction,
                seed_links=seed_links,
                avoid_topics=avoid,
            )
        )

    _print_token_usage(
        result.input_tokens,
        result.output_tokens,
        result.cache_read_tokens,
        result.cache_creation_tokens,
    )
    console.print(f"\n🌐 web search 调用次数: [magenta]{result.web_search_count}[/magenta]")
    console.print("\n" + "=" * 60)
    console.print(Markdown(result.candidates_markdown))


# ============================================================
# write
# ============================================================
@app.command()
def write(
    topic: str = typer.Option(..., "--topic", "-t", help="选题，一句话"),
    material: str | None = typer.Option(None, "--material", "-m", help="信源链接或素材"),
    angle: str | None = typer.Option(None, "--angle", "-a", help="切入角度，特殊要求"),
    show_article: bool = typer.Option(False, "--show", "-s", help="终端直接打印文章 markdown"),
    also_ops: bool = typer.Option(False, "--with-ops", help="写完正文紧接着生成 ops 文档"),
) -> None:
    """写一篇 Token 公园风格的公众号长文。

    示例：
        tpagent write --topic "Anthropic 雪藏 Mythos" \\
                      --material "https://anthropic.com/news/mythos" \\
                      --angle "AI 公司自己喊停的剧本" --with-ops
    """
    console.print(
        Panel.fit(
            f"[bold]选题:[/bold] {topic}\n"
            + (f"[bold]角度:[/bold] {angle}\n" if angle else "")
            + (f"[bold]素材:[/bold] {material}" if material else ""),
            title="✍️  开始写作",
            border_style="cyan",
        )
    )

    # 创建 session
    article_session = create_session(topic=topic, angle=angle, material=material)
    console.print(f"📌 Session ID: [cyan]{article_session.id}[/cyan]")

    writer = ArticleWriter()
    with console.status("[cyan]Claude 正在写文章... 约 30-60 秒[/cyan]"):
        result = writer.write(WriteRequest(topic=topic, material=material, angle=angle))

    article_path = save_article(result.article_markdown, topic)

    _print_token_usage(
        result.input_tokens,
        result.output_tokens,
        result.cache_read_tokens,
        result.cache_creation_tokens,
    )
    console.print(f"\n字符数: [magenta]{len(result.article_markdown):,}[/magenta]")
    console.print(f"📝 文章已保存: [green]{article_path}[/green]")

    # 跑 grep
    report = scan_file(article_path)
    _print_grep_report(report)

    # 更新 session
    update_session(
        article_session.id,  # type: ignore[arg-type]
        stage=SessionStage.article,
        article_path=str(article_path),
        can_publish=report.can_publish,
        grep_hits=report.total_hits,
        total_input_tokens=result.input_tokens,
        total_output_tokens=result.output_tokens,
        total_cache_read_tokens=result.cache_read_tokens,
        estimated_cost_usd=estimate_cost(
            result.input_tokens,
            result.output_tokens,
            result.cache_read_tokens,
            result.cache_creation_tokens,
        ),
    )

    if show_article:
        console.print("\n" + "=" * 60)
        console.print("📄 文章内容")
        console.print("=" * 60)
        console.print(Markdown(result.article_markdown))

    if also_ops:
        console.print("\n" + "=" * 60)
        console.print("[cyan]🛠 紧接着生成 ops 文档...[/cyan]")
        _generate_ops(article_path, topic, session_id=article_session.id)


# ============================================================
# ops
# ============================================================
def _generate_ops(article_path: Path, topic: str, session_id: int | None = None) -> Path:
    """生成 ops 文档的核心逻辑（被 write --with-ops 和 ops 子命令共用）。"""
    article_md = article_path.read_text(encoding="utf-8")

    ops_writer = OpsWriter()
    with console.status("[cyan]Claude 正在写 ops 文档... 约 30-60 秒[/cyan]"):
        result = ops_writer.write(
            OpsWriteRequest(
                article_markdown=article_md,
                topic=topic,
            )
        )

    ops_path = save_ops(result.ops_markdown, topic)
    _print_token_usage(
        result.input_tokens,
        result.output_tokens,
        result.cache_read_tokens,
        result.cache_creation_tokens,
    )
    console.print(f"📋 ops 文档已保存: [green]{ops_path}[/green]")

    # 跑 grep（ops 也要符合规则）
    ops_report = scan_file(ops_path)
    _print_grep_report(ops_report)

    if session_id:
        update_session(
            session_id,
            ops_path=str(ops_path),
            stage=SessionStage.ops,
        )

    return ops_path


@app.command()
def ops(
    article: Path = typer.Argument(..., help="已有文章的 .md 路径"),
    topic: str | None = typer.Option(
        None,
        "--topic",
        "-t",
        help="选题（用于 ops 文件名）。不填时从文件名推断",
    ),
) -> None:
    """基于已有文章正文，生成图运营合一 ops 文档。

    示例：
        tpagent ops ./sessions/5.26/2026-05-26-mythos.md --topic "Anthropic Mythos"
    """
    if not article.exists():
        console.print(f"[red]❌ 文章不存在: {article}[/red]")
        raise typer.Exit(1)

    # 从文件名推断 topic
    if topic is None:
        # 2026-05-26-anthropic-mythos.md → "anthropic-mythos"
        stem = article.stem
        parts = stem.split("-", 3)
        topic = parts[3] if len(parts) >= 4 else stem
        console.print(f"[dim]从文件名推断选题: {topic}[/dim]")

    console.print(
        Panel.fit(
            f"[bold]源文章:[/bold] {article.name}\n[bold]选题:[/bold] {topic}",
            title="🛠 生成 ops 文档",
            border_style="cyan",
        )
    )

    _generate_ops(article, topic)


# ============================================================
# scan
# ============================================================
@app.command()
def scan(
    target: Path = typer.Argument(..., help="要扫描的 .md 文件或目录"),
) -> None:
    """跑 6 项 grep 扫描。

    示例：
        tpagent scan ./sessions/5.26/
    """
    if not target.exists():
        console.print(f"[red]❌ 路径不存在: {target}[/red]")
        raise typer.Exit(1)

    if target.is_dir():
        console.print(f"[cyan]扫描目录 {target} 下所有 .md 文件...[/cyan]")
        report = scan_directory(target)
    else:
        console.print(f"[cyan]扫描文件 {target}...[/cyan]")
        report = scan_file(target)

    _print_grep_report(report)

    if not report.can_publish:
        raise typer.Exit(1)


# ============================================================
# list
# ============================================================
@app.command(name="list")
def list_cmd(
    limit: int = typer.Option(20, "--limit", "-n", help="显示数量"),
    stage: str | None = typer.Option(
        None,
        "--stage",
        "-s",
        help="过滤阶段: topic / article / images / ops / ready / published",
    ),
) -> None:
    """列出历史 session（按时间倒序）。

    示例：
        tpagent list
        tpagent list -n 50 -s article
    """
    stage_filter = None
    if stage:
        try:
            stage_filter = SessionStage(stage)
        except ValueError:
            console.print(
                f"[red]❌ 未知阶段 '{stage}'。可选: "
                f"{', '.join(s.value for s in SessionStage)}[/red]"
            )
            raise typer.Exit(1) from None

    sessions = list_sessions(limit=limit, stage=stage_filter)

    if not sessions:
        console.print("[dim]还没有 session 记录。试试 `tpagent write ...`[/dim]")
        return

    table = Table(title=f"📚 最近 {len(sessions)} 个 Session", show_header=True)
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("时间", style="dim")
    table.add_column("选题", style="white")
    table.add_column("阶段", justify="center")
    table.add_column("Grep", justify="right")
    table.add_column("可发布", justify="center")
    table.add_column("成本 $", justify="right", style="magenta")

    for s in sessions:
        publishable = "✅" if s.can_publish else "❌"
        stage_color = {
            SessionStage.topic: "[yellow]选题[/yellow]",
            SessionStage.article: "[cyan]初稿[/cyan]",
            SessionStage.ops: "[blue]ops[/blue]",
            SessionStage.images: "[magenta]图片[/magenta]",
            SessionStage.ready: "[green]待发[/green]",
            SessionStage.published: "[bold green]已发[/bold green]",
        }.get(s.stage, s.stage.value)

        table.add_row(
            str(s.id),
            s.created_at.strftime("%m-%d %H:%M"),
            s.topic[:30],
            stage_color,
            str(s.grep_hits),
            publishable,
            f"{s.estimated_cost_usd:.3f}",
        )

    console.print(table)


# ============================================================
# images
# ============================================================
@app.command()
def images(
    ops_doc: Path = typer.Argument(..., help="ops 文档 .md 路径"),
    required_only: bool = typer.Option(
        True,
        "--required-only/--all",
        help="只出 ⭐ 必配图（默认）还是全部",
    ),
    candidates: int = typer.Option(
        3,
        "--candidates",
        "-c",
        help="每张图生成多少个候选",
    ),
    size: str = typer.Option(
        "1792x1024",
        "--size",
        help="图片尺寸：1024x1024 / 1792x1024 / 1024x1792",
    ),
    quality: str = typer.Option(
        "standard",
        "--quality",
        help="standard 或 hd（hd 慢且贵）",
    ),
    upload: bool = typer.Option(
        False,
        "--upload",
        help="生成后上传到 R2（需配置 R2_* env）",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="只解析 ops 文档不实际调 DALL-E（看花多少钱）",
    ),
) -> None:
    """从 ops 文档解析 image2 prompt → 调 DALL-E 出图。

    示例：
        # 解析看看
        tpagent images ./sessions/5.26/xxx-ops.md --dry-run

        # 实际出图，每张 3 候选
        tpagent images ./sessions/5.26/xxx-ops.md -c 3

        # 出图 + 上传 R2
        tpagent images ./sessions/5.26/xxx-ops.md --upload
    """
    if not ops_doc.exists():
        console.print(f"[red]❌ ops 文档不存在: {ops_doc}[/red]")
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold]ops 文档:[/bold] {ops_doc.name}\n"
            f"[bold]模式:[/bold] {'只必配图' if required_only else '全部图'}\n"
            f"[bold]每图候选:[/bold] {candidates}\n"
            f"[bold]尺寸:[/bold] {size} {quality}",
            title="🎨 图像生成 pipeline",
            border_style="cyan",
        )
    )

    # 解析 ops
    specs = parse_ops_images(ops_doc)
    if required_only:
        specs = filter_required(specs)

    if not specs:
        console.print("[red]❌ 没解析出任何图 spec。检查 ops 文档格式[/red]")
        raise typer.Exit(1)

    console.print(f"\n📊 解析到 {len(specs)} 张图:")
    console.print(specs_summary(specs))

    # 估算成本
    pricing = {
        ("standard", "1024x1024"): 0.040,
        ("standard", "1792x1024"): 0.080,
        ("standard", "1024x1792"): 0.080,
        ("hd", "1024x1024"): 0.080,
        ("hd", "1792x1024"): 0.120,
        ("hd", "1024x1792"): 0.120,
    }
    per_image = pricing.get((quality, size), 0.04)
    total_calls = len(specs) * candidates
    total_cost = round(per_image * total_calls, 4)
    console.print(
        f"\n💰 [bold]预估成本:[/bold] {total_calls} 张 × ${per_image} = "
        f"[bold magenta]${total_cost}[/bold magenta]"
    )

    if dry_run:
        console.print("\n[dim]dry-run 模式，不实际出图。[/dim]")
        return

    # 实际出图
    from tpagent.services.image_generator import DalleImageGenerator

    gen = DalleImageGenerator()

    output_dir = ops_doc.parent / f"{ops_doc.stem}-images"
    output_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"\n📂 输出目录: [green]{output_dir}[/green]")

    actual_cost = 0.0
    for spec in specs:
        prompt = spec.prompt_en or spec.prompt_zh
        if not prompt:
            console.print(f"[yellow]⚠️  跳过 {spec.image_id}: 没找到 prompt[/yellow]")
            continue

        console.print(f"\n[cyan]🎨 出图 {spec.image_id} {spec.image_title}...[/cyan]")
        with console.status(
            f"[cyan]DALL-E 出 {candidates} 个候选... 约 {candidates * 20} 秒[/cyan]"
        ):
            result = gen.generate(
                prompt=prompt,
                num_candidates=candidates,
                size=size,
                quality=quality,
                output_dir=output_dir,
                slug=spec.image_id.replace(" ", "-"),
            )
        actual_cost += result.cost_usd
        for c in result.candidates:
            console.print(f"  ✓ {c.image_path.name} (revised: {c.revised_prompt[:60]}...)")

    console.print(f"\n[bold green]✅ 所有图已生成，实际成本 ${actual_cost:.4f}[/bold green]")

    # 可选 R2 上传
    if upload:
        from tpagent.services.r2_uploader import R2Uploader

        uploader = R2Uploader()
        if not uploader.is_configured:
            console.print(
                "\n[yellow]⚠️  R2 未配置，跳过上传。"
                "填 R2_ACCOUNT_ID / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY 后再试[/yellow]"
            )
        else:
            console.print("\n[cyan]☁️  上传到 R2...[/cyan]")
            image_files = list(output_dir.glob("*.png"))
            results = uploader.upload_batch(image_files, prefix=output_dir.name)
            for r in results:
                console.print(f"  ✓ {r.url}")


# ============================================================
# serve
# ============================================================
@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="监听 host"),
    port: int = typer.Option(8000, help="监听端口"),
    reload: bool = typer.Option(False, "--reload", help="热重载（开发用）"),
) -> None:
    """启动 FastAPI 服务（API 模式）。"""
    import uvicorn

    uvicorn.run("tpagent.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
