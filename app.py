from flask import Flask, render_template, request, redirect, url_for, flash

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)

from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db_connection, create_tables

from matching import calculate_match_score
app = Flask(__name__)

app.secret_key = "foodshare-secret-key"



# ---------------- LOGIN CONFIGURATION ----------------

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"


# ---------------- USER CLASS ----------------

class User(UserMixin):

    def __init__(self, user_id, name, email, password, phone, role):

        self.id = user_id
        self.name = name
        self.email = email
        self.password = password
        self.phone = phone
        self.role = role


@login_manager.user_loader
def load_user(user_id):

    connection = get_db_connection()

    user = connection.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    connection.close()

    if user:

        return User(
            user["id"],
            user["name"],
            user["email"],
            user["password"],
            user["phone"],
            user["role"]
        )

    return None


# ---------------- HOME ----------------

@app.route("/")
def home():

    return render_template("index.html")


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        phone = request.form["phone"]
        role = request.form["role"]


        hashed_password = generate_password_hash(password)


        connection = get_db_connection()


        try:

            connection.execute("""
                INSERT INTO users
                (name, email, password, phone, role)

                VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                email,
                hashed_password,
                phone,
                role
            ))

            connection.commit()

            flash("Registration successful! Please login.")

            return redirect(url_for("login"))


        except Exception:

            flash("Email already registered.")


        finally:

            connection.close()


    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]

        password = request.form["password"]


        connection = get_db_connection()


        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()


        connection.close()


        if user and check_password_hash(
            user["password"],
            password
        ):

            user_object = User(
                user["id"],
                user["name"],
                user["email"],
                user["password"],
                user["phone"],
                user["role"]
            )


            login_user(user_object)


            if user["role"] == "donor":

                return redirect("/donor/dashboard")


            elif user["role"] == "receiver":

                return redirect("/receiver/dashboard")


            elif user["role"] == "admin":

                return redirect("/admin/dashboard")


        flash("Invalid email or password.")


    return render_template("login.html")


# ---------------- LOGOUT ----------------

@app.route("/logout")
@login_required
def logout():

    logout_user()

    flash("You have been logged out.")

    return redirect(url_for("home"))


# ---------------- DONOR DASHBOARD ----------------

@app.route("/donor/dashboard")
@login_required
def donor_dashboard():

    if current_user.role != "donor":

        flash("Access denied.")

        return redirect(url_for("home"))


    connection = get_db_connection()


    donations = connection.execute("""
        SELECT *
        FROM food_donations
        WHERE donor_id = ?
        ORDER BY created_at DESC
    """, (current_user.id,)).fetchall()


    connection.close()


    return render_template(
        "donor_dashboard.html",
        donations=donations
    )

# ---------------- ADD FOOD ----------------

@app.route("/donor/add-food", methods=["GET", "POST"])
@login_required
def add_food():

    if current_user.role != "donor":

        flash("Access denied.")

        return redirect(url_for("home"))


    if request.method == "POST":

        food_name = request.form["food_name"]

        category = request.form["category"]

        quantity = request.form["quantity"]

        prepared_time = request.form["prepared_time"]

        available_until = request.form["available_until"]

        location = request.form["location"]

        description = request.form["description"]


        connection = get_db_connection()


        connection.execute("""
            INSERT INTO food_donations
            (
                donor_id,
                food_name,
                category,
                quantity,
                description,
                prepared_time,
                available_until,
                location,
                status
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            current_user.id,
            food_name,
            category,
            quantity,
            description,
            prepared_time,
            available_until,
            location,
            "Available"
        ))


        connection.commit()

        connection.close()


        flash("Food donation added successfully!")

        return redirect(
            url_for("donor_dashboard")
        )


    return render_template("add_food.html")


# ---------------- RECEIVER DASHBOARD ----------------

@app.route("/receiver/dashboard")
@login_required
def receiver_dashboard():

    if current_user.role != "receiver":

        flash("Access denied.")

        return redirect(url_for("home"))


    search = request.args.get(
        "search",
        ""
    )

    category = request.args.get(
        "category",
        ""
    )

    receiver_location = request.args.get(
        "location",
        ""
    )

    requested_quantity = request.args.get(
        "quantity",
        "1"
    )


    try:

        requested_quantity = int(
            requested_quantity
        )

    except ValueError:

        requested_quantity = 1


    connection = get_db_connection()


    query = """
        SELECT *
        FROM food_donations
        WHERE status = 'Available'
    """

    parameters = []


    # ---------------- SEARCH ----------------

    if search:

        query += """
            AND (
                food_name LIKE ?
                OR location LIKE ?
            )
        """

        search_value = f"%{search}%"

        parameters.extend([
            search_value,
            search_value
        ])


    # ---------------- CATEGORY ----------------

    if category:

        query += """
            AND category = ?
        """

        parameters.append(category)


    query += """
        ORDER BY created_at DESC
    """


    foods = connection.execute(
        query,
        parameters
    ).fetchall()


    connection.close()


    # ---------------- MATCHING ----------------

    matched_foods = []


    for food in foods:

        score = calculate_match_score(
            food,
            receiver_location,
            category,
            requested_quantity
        )


        matched_foods.append({
            "food": food,
            "score": score
        })


    # Sort highest score first

    matched_foods.sort(
        key=lambda item: item["score"],
        reverse=True
    )


    return render_template(
        "receiver_dashboard.html",
        matched_foods=matched_foods,
        search=search,
        category=category,
        location=receiver_location,
        quantity=requested_quantity
    )
# ---------------- REQUEST FOOD ----------------

@app.route("/receiver/request/<int:food_id>",
           methods=["GET", "POST"])
@login_required
def request_food(food_id):

    if current_user.role != "receiver":

        flash("Access denied.")

        return redirect(url_for("home"))


    connection = get_db_connection()


    food = connection.execute("""
        SELECT *
        FROM food_donations
        WHERE id = ?
        AND status = 'Available'
    """, (food_id,)).fetchone()


    if not food:

        connection.close()

        flash("Food donation is no longer available.")

        return redirect(
            url_for("receiver_dashboard")
        )


    if request.method == "POST":

        quantity = int(
            request.form["quantity"]
        )


        # Check quantity
        if quantity <= 0 or quantity > food["quantity"]:

            flash(
                "Please enter a valid quantity."
            )

            connection.close()

            return redirect(
                url_for(
                    "request_food",
                    food_id=food_id
                )
            )


        # Insert request
        connection.execute("""
            INSERT INTO food_requests
            (
                food_id,
                receiver_id,
                quantity_requested,
                request_status
            )

            VALUES (?, ?, ?, ?)
        """,
        (
            food_id,
            current_user.id,
            quantity,
            "Pending"
        ))


        connection.commit()

        connection.close()


        flash(
            "Food request submitted successfully!"
        )


        return redirect(
            url_for("receiver_dashboard")
        )


    connection.close()


    return render_template(
        "request_food.html",
        food=food
    )


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():

    if current_user.role != "admin":

        flash("Access denied.")

        return redirect(url_for("home"))


    connection = get_db_connection()


    # Get users

    users = connection.execute("""
        SELECT *
        FROM users
        ORDER BY id DESC
    """).fetchall()


    # Get food donations with donor name

    foods = connection.execute("""
        SELECT
            food_donations.*,
            users.name AS donor_name

        FROM food_donations

        JOIN users
        ON food_donations.donor_id = users.id

        ORDER BY food_donations.created_at DESC

    """).fetchall()


    # Get requests with food and receiver information

    requests = connection.execute("""
        SELECT
            food_requests.*,
            food_donations.food_name,
            users.name AS receiver_name

        FROM food_requests

        JOIN food_donations
        ON food_requests.food_id = food_donations.id

        JOIN users
        ON food_requests.receiver_id = users.id

        ORDER BY food_requests.request_date DESC

    """).fetchall()


    connection.close()


    return render_template(
        "admin_dashboard.html",
        users=users,
        foods=foods,
        requests=requests
    )

# ---------------- DONOR REQUESTS ----------------

@app.route("/donor/requests")
@login_required
def donor_requests():

    if current_user.role != "donor":

        flash("Access denied.")

        return redirect(url_for("home"))


    connection = get_db_connection()


    requests = connection.execute("""
        SELECT
            food_requests.*,
            food_donations.food_name,
            food_donations.location,
            users.name AS receiver_name

        FROM food_requests

        JOIN food_donations
        ON food_requests.food_id = food_donations.id

        JOIN users
        ON food_requests.receiver_id = users.id

        WHERE food_donations.donor_id = ?

        ORDER BY food_requests.request_date DESC

    """, (current_user.id,)).fetchall()


    connection.close()


    return render_template(
        "donor_requests.html",
        requests=requests
    )

# ---------------- APPROVE REQUEST ----------------

@app.route(
    "/donor/request/<int:request_id>/approve",
    methods=["POST"]
)
@login_required
def approve_request(request_id):

    if current_user.role != "donor":

        flash("Access denied.")

        return redirect(url_for("home"))


    connection = get_db_connection()


    # Find request belonging to this donor

    request_data = connection.execute("""
        SELECT
            food_requests.*,
            food_donations.quantity,
            food_donations.donor_id

        FROM food_requests

        JOIN food_donations
        ON food_requests.food_id = food_donations.id

        WHERE food_requests.id = ?

    """, (request_id,)).fetchone()


    if not request_data:

        connection.close()

        flash("Request not found.")

        return redirect(
            url_for("donor_requests")
        )


    # Security check

    if request_data["donor_id"] != current_user.id:

        connection.close()

        flash("You cannot manage this request.")

        return redirect(
            url_for("donor_requests")
        )


    # Check status

    if request_data["request_status"] != "Pending":

        connection.close()

        flash("This request has already been processed.")

        return redirect(
            url_for("donor_requests")
        )


    # Check quantity

    if request_data["quantity_requested"] > request_data["quantity"]:

        connection.close()

        flash("Not enough food quantity available.")

        return redirect(
            url_for("donor_requests")
        )


    # Approve request

    connection.execute("""
        UPDATE food_requests

        SET request_status = 'Approved'

        WHERE id = ?
    """, (request_id,))


    # Reduce food quantity

    new_quantity = (
        request_data["quantity"]
        -
        request_data["quantity_requested"]
    )


    if new_quantity == 0:

        new_status = "Completed"

    else:

        new_status = "Available"


    connection.execute("""
        UPDATE food_donations

        SET quantity = ?,
            status = ?

        WHERE id = ?
    """,
    (
        new_quantity,
        new_status,
        request_data["food_id"]
    ))


    connection.commit()

    connection.close()


    flash("Food request approved successfully!")


    return redirect(
        url_for("donor_requests")
    )

# ---------------- REJECT REQUEST ----------------

@app.route(
    "/donor/request/<int:request_id>/reject",
    methods=["POST"]
)
@login_required
def reject_request(request_id):

    if current_user.role != "donor":

        flash("Access denied.")

        return redirect(url_for("home"))


    connection = get_db_connection()


    request_data = connection.execute("""
        SELECT
            food_requests.*,
            food_donations.donor_id

        FROM food_requests

        JOIN food_donations
        ON food_requests.food_id = food_donations.id

        WHERE food_requests.id = ?

    """, (request_id,)).fetchone()


    if not request_data:

        connection.close()

        flash("Request not found.")

        return redirect(
            url_for("donor_requests")
        )


    # Security check

    if request_data["donor_id"] != current_user.id:

        connection.close()

        flash("You cannot manage this request.")

        return redirect(
            url_for("donor_requests")
        )


    # Check request status

    if request_data["request_status"] != "Pending":

        connection.close()

        flash("This request has already been processed.")

        return redirect(
            url_for("donor_requests")
        )


    # Reject request

    connection.execute("""
        UPDATE food_requests

        SET request_status = 'Rejected'

        WHERE id = ?
    """, (request_id,))


    connection.commit()

    connection.close()


    flash("Food request rejected.")


    return redirect(
        url_for("donor_requests")
    )

# ---------------- RECEIVER REQUEST HISTORY ----------------

@app.route("/receiver/requests")
@login_required
def receiver_requests():

    if current_user.role != "receiver":

        flash("Access denied.")

        return redirect(url_for("home"))


    connection = get_db_connection()


    requests = connection.execute("""
        SELECT
            food_requests.*,
            food_donations.food_name,
            food_donations.location

        FROM food_requests

        JOIN food_donations
        ON food_requests.food_id = food_donations.id

        WHERE food_requests.receiver_id = ?

        ORDER BY food_requests.request_date DESC

    """, (current_user.id,)).fetchall()


    connection.close()


    return render_template(
        "receiver_requests.html",
        requests=requests
    )


# ---------------- CREATE TABLES ----------------

create_tables()


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":

    import os
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )

