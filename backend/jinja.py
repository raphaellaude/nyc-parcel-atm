from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader('./templates'),
    autoescape=select_autoescape()
)


def render_template(template_name, **kwargs):
    """
    Render a SQL template with the given keyword arguments.
    """
    template = env.get_template(template_name)
    return template.render(**kwargs)
