@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(
            user.password_hash,
            password
        ):
            session.clear()
            session["user_id"] = user.id
            session["username"] = user.username

            flash(f"Welcome, {user.username}!", "success")

            return redirect(url_for("main.index"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")