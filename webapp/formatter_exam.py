def format_html(
    items: list[str],
    output_filename: str,
    title: str,
    header_text: str,
    items_per_row: int,
    font_size: int,
):
    """
    Format exam content as HTML.

    Args:
        items: List of items to display (characters or words)
        output_filename: Path to output HTML file
        title: Title of the exam
        header_text: Header text to display
        items_per_row: Number of items per row in the grid
        font_size: Font size for the items
    """
    html_content = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='UTF-8'>",
        f"<title>{title}</title>",
        "<style>",
        "  @page { size: letter; margin: 1in; }",
        "  body { font-family: 'Songti SC', 'STSong', serif; }",
        "  h1 { text-align: center; }",
        "  .items-grid { display: grid;",
        f"   grid-template-columns: repeat({items_per_row}, 1fr);",
        "    gap: 1em 0;",
        "  }",
        "  .item {",
        f"   font-size: {font_size}pt;",
        "    display: flex;",
        "    align-items: center;",
        "    justify-content: center;",
        "  }",
        "  .header { font-size: 10pt; text-align: right; padding-bottom: 20px; page-break-inside: avoid; }",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>{title}</h1>",
    ]

    if header_text:
        html_content.append("<div class='header'>")
        html_content.append(f"<p>{header_text}</p>")
        html_content.append("</div>")

    if items:
        html_content.append("<div class='items-grid'>")
        for item in items:
            html_content.append(f"<div class='item'>{item}</div>")
        html_content.append("</div>")

    html_content.extend(["</body>", "</html>"])

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(html_content))
