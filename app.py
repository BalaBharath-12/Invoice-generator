import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

# =========================
# DATABASE CONNECTION
# =========================
def get_connection():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "invoices.db")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# DATABASE INITIALIZATION
# =========================
def init_db():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT,
            invoice_date TEXT,
            client TEXT,
            billing_address TEXT,
            gstin TEXT,
            product TEXT,
            quantity REAL,
            unit_price REAL,
            tax REAL,
            total REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            address TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            address TEXT,
            tax_number TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()


# =========================
# HOME PAGE
# =========================
@app.route("/")
def home():
    return render_template("index.html")


# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "1234":
            return redirect(url_for("dashboard"))

        return "Invalid Username or Password"

    return render_template("login.html")


# =========================
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():

    conn = get_connection()

    invoices = conn.execute("SELECT * FROM invoices").fetchall()
    profile = conn.execute("SELECT * FROM business_profile LIMIT 1").fetchone()

    conn.close()

    return render_template("dashboard.html",
                           invoices=invoices,
                           profile=profile)


# =========================
# BUSINESS PROFILE
# =========================
@app.route("/business_profile", methods=["GET", "POST"])
def business_profile():

    conn = get_connection()

    if request.method == "POST":

        company_name = request.form.get("company_name")
        address = request.form.get("address")
        tax_number = request.form.get("tax_number")

        existing = conn.execute("SELECT * FROM business_profile").fetchone()

        if existing:
            conn.execute("""
                UPDATE business_profile
                SET company_name=?, address=?, tax_number=?
                WHERE id=?
            """, (company_name, address, tax_number, existing["id"]))

        else:
            conn.execute("""
                INSERT INTO business_profile
                (company_name,address,tax_number)
                VALUES (?,?,?)
            """, (company_name, address, tax_number))

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    profile = conn.execute("SELECT * FROM business_profile LIMIT 1").fetchone()
    conn.close()

    return render_template("business_profile.html", profile=profile)


# =========================
# CREATE INVOICE
# =========================
@app.route("/create_invoice", methods=["GET", "POST"])
def create_invoice():

    if request.method == "POST":

        conn = get_connection()
        cur = conn.cursor()

        invoice_number = request.form.get("invoice_number")
        invoice_date = request.form.get("invoice_date")
        client = request.form.get("client")
        billing_address = request.form.get("billing_address")
        gstin = request.form.get("gstin")

        products = request.form.getlist("product[]")
        quantities = request.form.getlist("quantity[]")
        prices = request.form.getlist("unit_price[]")
        taxes = request.form.getlist("tax[]")

        for i in range(len(products)):

            product = products[i]
            qty = float(quantities[i])
            price = float(prices[i])
            tax = float(taxes[i])

            item_total = qty * price
            tax_amount = item_total * (tax / 100)
            total = item_total + tax_amount

            cur.execute("""
                INSERT INTO invoices
                (invoice_number, invoice_date, client, billing_address,
                gstin, product, quantity, unit_price, tax, total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_number,
                invoice_date,
                client,
                billing_address,
                gstin,
                product,
                qty,
                price,
                tax,
                total
            ))

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("create_invoice.html")


# =========================
# DOWNLOAD INVOICE PDF
# =========================
@app.route("/download_invoice/<int:id>")
def download_invoice(id):

    conn = get_connection()
    invoice = conn.execute(
        "SELECT * FROM invoices WHERE id=?",
        (id,)
    ).fetchone()

    conn.close()

    if not invoice:
        return "Invoice not found"

    filename = f"invoice_{id}.pdf"
    filepath = os.path.join(os.getcwd(), filename)

    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica", 12)

    y = 750

    c.drawString(50, y, "INVOICE")
    y -= 40

    c.drawString(50, y, f"Invoice Number: {invoice['invoice_number']}")
    y -= 20
    c.drawString(50, y, f"Date: {invoice['invoice_date']}")
    y -= 20
    c.drawString(50, y, f"Client: {invoice['client']}")
    y -= 20
    c.drawString(50, y, f"Address: {invoice['billing_address']}")
    y -= 20
    c.drawString(50, y, f"GSTIN: {invoice['gstin']}")
    y -= 40

    c.drawString(50, y, f"Product: {invoice['product']}")
    y -= 20
    c.drawString(50, y, f"Quantity: {invoice['quantity']}")
    y -= 20
    c.drawString(50, y, f"Unit Price: ₹{invoice['unit_price']}")
    y -= 20
    c.drawString(50, y, f"Tax: {invoice['tax']}%")
    y -= 20
    c.drawString(50, y, f"Total: ₹{invoice['total']}")

    c.save()

    return send_file(filepath, as_attachment=True)


# =========================
# DELETE INVOICE
# =========================
@app.route("/delete_invoice/<int:id>")
def delete_invoice(id):

    conn = get_connection()

    conn.execute(
        "DELETE FROM invoices WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


# =========================
# CLIENTS
# =========================
@app.route("/clients", methods=["GET", "POST"])
def clients():

    conn = get_connection()

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        address = request.form.get("address")

        conn.execute(
            "INSERT INTO clients (name,email,phone,address) VALUES (?,?,?,?)",
            (name, email, phone, address)
        )

        conn.commit()

        return redirect(url_for("clients"))

    clients_list = conn.execute(
        "SELECT * FROM clients"
    ).fetchall()

    conn.close()

    return render_template(
        "clients.html",
        clients=clients_list
    )


# =========================
# RUN APP
# =========================
if __name__ == "__main__":
   app.run(debug=True, port=5000)