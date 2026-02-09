from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import qrcode
from io import BytesIO
import base64

app = Flask(__name__)
app.secret_key = "secret123"

# MySQL connection
db = mysql.connector.connect(
    host="switchback.proxy.rlwy.net",
    user="root",
    password="Root@1234",
    database="railway",
    port=39048
)

cursor = db.cursor(dictionary=True)


# ================= HOME =================
@app.route("/")
def home():
    session["cart"] = []
    return render_template("index.html")


# ================= SCAN =================
@app.route("/scan", methods=["GET", "POST"])
def scan():
    if "cart" not in session:
        session["cart"] = []

    message = None

    if request.method == "POST":
        barcode = request.form.get("barcode")

        if barcode:
            cursor.execute("SELECT * FROM products WHERE barcode=%s", (barcode,))
            product = cursor.fetchone()

            if product:

                # ❌ Out of stock
                if product["quantity"] <= 0:
                    message = "Out of Stock"
                else:
                    # ✔ add to cart
                    cart = session["cart"]
                    cart.append(product)
                    session["cart"] = cart

                    # 🔻 reduce quantity in DB
                    cursor.execute(
                        "UPDATE products SET quantity = quantity - 1 WHERE id=%s",
                        (product["id"],),
                    )
                    db.commit()

                    # ⚠ low stock warning
                    if product["quantity"] - 1 < 5:
                        message = "⚠ Low Stock Warning"

    cart = session["cart"]
    total = sum(item["price"] for item in cart)

    return render_template("scan.html", cart=cart, total=total, message=message)


# ================= CLEAR CART =================
@app.route("/clear")
def clear():
    session["cart"] = []
    return redirect(url_for("scan"))


# ================= PAYMENT =================
@app.route("/payment")
def payment():
    cart = session.get("cart", [])
    total = sum(item["price"] for item in cart)

    if total == 0:
        return redirect(url_for("scan"))

    upi_id = "demo@upi"
    name = "Scango Store"

    upi_url = f"upi://pay?pa={upi_id}&pn={name}&am={total}&cu=INR"

    qr = qrcode.make(upi_url)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    return render_template("payment.html", total=total, qr=img_str)


# ================= ADMIN LOGIN =================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        cursor.execute(
            "SELECT * FROM admin WHERE username=%s AND password=%s",
            (username, password),
        )
        admin = cursor.fetchone()

        if admin:
            session["admin"] = admin["username"]
            return redirect(url_for("admin_panel"))

    return render_template("admin_login.html")


# ================= ADMIN PANEL =================
@app.route("/admin")
def admin_panel():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    return render_template("admin.html", products=products)


# ================= ADD PRODUCT =================
@app.route("/add_product", methods=["POST"])
def add_product():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    name = request.form.get("name")
    price = request.form.get("price")
    quantity = request.form.get("quantity")
    barcode = request.form.get("barcode")

    if name and price and quantity and barcode:
        cursor.execute(
            "INSERT INTO products (name, price, quantity, barcode) VALUES (%s, %s, %s, %s)",
            (name, price, quantity, barcode),
        )
        db.commit()

    return redirect(url_for("admin_panel"))


# ================= UPDATE PRODUCT =================
@app.route("/update_product/<int:id>", methods=["POST"])
def update_product(id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    name = request.form.get("name")
    price = request.form.get("price")
    quantity = request.form.get("quantity")
    barcode = request.form.get("barcode")

    cursor.execute(
        "UPDATE products SET name=%s, price=%s, quantity=%s, barcode=%s WHERE id=%s",
        (name, price, quantity, barcode, id),
    )
    db.commit()

    return redirect(url_for("admin_panel"))


# ================= DELETE PRODUCT =================
@app.route("/delete_product/<int:id>")
def delete_product(id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    cursor.execute("DELETE FROM products WHERE id=%s", (id,))
    db.commit()
    return redirect(url_for("admin_panel"))


# ================= LOGOUT =================
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
