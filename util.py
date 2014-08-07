def resource(rule, endpoint):
    def wrap(view):
        app.add_url_rule(rule, view_func=view.as_view(endpoint))
        return view
    return wrap

def redirect(url):
    return '', 301, {'Location': url}

