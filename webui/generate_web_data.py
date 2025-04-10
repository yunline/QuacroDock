import minify_html

with open("webui/index.html", encoding="utf8") as html_file:
    html_body = html_file.read()

with open("webui/script.js", encoding="utf8") as script_file:
    script = script_file.read()

with open("webui/style.css", encoding="utf8") as css_file:
    css = css_file.read()

out_html_raw = f"""
<head>
    <script>{script}</script>
    <style>{css}</style>
</head>
{html_body}
"""

out_html_mini = minify_html.minify(
    out_html_raw, 
    minify_js=True, 
    minify_css=True
)

out_py = f"""# this file is auto generated
frontend_html = {repr(out_html_mini)}
"""

with open("quacro/quacro_web_data.py", "w", encoding="utf8") as out_file:
    out_file.write(out_py)
