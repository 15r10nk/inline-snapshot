import mkdocs


class ReplaceUrlPlugin(mkdocs.plugins.BasePlugin):
    def on_page_content(self, html, page, config, files):
        return html.replace("docs/assets", "assets")
