from flask import current_app as app, redirect, url_for

print("import routes.py")


@app.route("/")
def main():
    return redirect(url_for("/dash/"))
