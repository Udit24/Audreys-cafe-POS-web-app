from flask import Flask, render_template, request
import json
import os
import subprocess
from datetime import datetime
from reportlab.pdfgen import canvas
from escpos.printer import Usb

app = Flask(__name__)

# a folder is created with the current year tag
def get_data_folder():
    year = datetime.now().strftime("%Y")

    folder = os.path.join("data", year)

    os.makedirs(folder, exist_ok=True)

    return folder

# create a unique billno based on just time and date
def generate_bill_number():
    return datetime.now().strftime("%Y%m%d%H%M%S")

# bill saving and bill printing functions
def print_pdf(filename):
    subprocess.run(["lp", filename])

def create_bill_pdf(table_name, order, bill_number):

    data_folder = get_data_folder()

    filename = os.path.join(
        data_folder,
        bill_number + ".pdf"
    )

    # Create PDF
    c = canvas.Canvas(filename)

    y = 800

    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(300, y, "Audreys Korean Cafe")

    y -= 20

    c.setFont("Helvetica", 9)
    c.drawCentredString(
        300,
        y,
        "22(15) Feeder Road, Barrackpore"
    )

    y -= 15
    c.drawCentredString(
        300,
        y,
        "Contact: 8100030700"
    )

    y -= 15
    c.drawCentredString(
        300,
        y,
        "GSTIN 19ACCFA3878J1Z0"
    )

    y -= 15
    c.drawCentredString(
        300,
        y,
        "FSSAI 22823127000191"
    )

    y -= 25

    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    c.drawString(40, y, "DATE AND TIME : " + now)

    y -= 15
    c.drawString(40, y, "TABLE: " + table_name)

    y -= 15
    c.drawString(40, y, "BILL NO: " + bill_number)

    y -= 30

    # Column headings
    c.setFont("Helvetica-Bold", 9)

    c.drawString(40, y, "ITEM")
    c.drawString(300, y, "QTY")
    c.drawString(350, y, "PRICE")
    c.drawString(430, y, "AMOUNT")

    y -= 15

    c.setFont("Helvetica", 9)

    subtotal = 0

    for ordered_item in order:

        item_id = ordered_item["id"]
        quantity = ordered_item["quantity"]

        # Find item in menu
        with open("menu.json", "r") as file:
            menu = json.load(file)

        item = next(
            item for item in menu
            if item["id"] == item_id
        )

        name = item["name"]
        price = item["price"]

        amount = price * quantity

        subtotal += amount

        c.drawString(40, y, name)
        c.drawString(300, y, str(quantity))
        c.drawString(350, y, f"{price:.2f}")
        c.drawString(430, y, f"{amount:.2f}")

        y -= 15

    # Tax calculation
    cgst = subtotal * 0.025
    sgst = subtotal * 0.025

    grand_total = subtotal + cgst + sgst

    y -= 15

    c.line(40, y, 500, y)

    y -= 20

    c.drawString(350, y, "TOTAL")
    c.drawRightString(500, y, f"₹{subtotal:.2f}")

    y -= 15

    c.drawString(350, y, "CGST @ 2.5%")
    c.drawRightString(500, y, f"₹{cgst:.2f}")

    y -= 15

    c.drawString(350, y, "SGST @ 2.5%")
    c.drawRightString(500, y, f"₹{sgst:.2f}")

    y -= 20

    c.setFont("Helvetica-Bold", 11)

    c.drawString(350, y, "GRAND TOTAL")
    c.drawRightString(500, y, f"₹{grand_total:.2f}")

    c.save()

    return filename

#send KOT to thermal printer
def print_kot_to_printer(table_name, order):
    # use this in windows to get the two values wmic path Win32_USBHub get Name, DeviceID, Status
    # or in windows wmic path Win32_PnPEntity where "Name like '%Printer%'" get Name, DeviceID
    # system_profiler SPUSBDataType
    # Thermal Printer: Product ID: 0x1234, Vendor ID: 0x5678

    printer = Usb(
        0x1234,
        0x5678
    )

    with open("menu.json", "r") as file:
        menu = json.load(file)

    now = datetime.now()

    for ordered_item in order:

        item_id = ordered_item["id"]
        quantity = ordered_item["quantity"]

        item = next(
            item for item in menu
            if item["id"] == item_id
        )

        name = item["name"]

        for i in range(quantity):

            printer.set(
                align="center",
                bold=True,
                width=2,
                height=2
            )

            printer.text("KITCHEN ORDER\n")

            printer.set(
                align="left",
                bold=False,
                width=1,
                height=1
            )

            printer.text(
                "DATE: "
                + now.strftime("%d-%m-%Y")
                + "\n"
            )

            printer.text(
                "TIME: "
                + now.strftime("%H:%M:%S")
                + "\n"
            )

            printer.text(
                "TABLE: "
                + table_name
                + "\n"
            )

            printer.text("\n")

            printer.set(
                align="center",
                bold=True,
                width=2,
                height=2
            )

            printer.text(name + "\n")

            printer.set(
                align="center",
                bold=False,
                width=1,
                height=1
            )

            printer.feed(3)

            printer.cut()

    printer.close()


# print KOT
@app.route("/print_kot/<table_name>", methods=["POST"])
def print_kot(table_name):

    # Read orders
    with open("orders.json", "r") as file:
        orders = json.load(file)

    table_data = orders.get(
        table_name,
        {
            "active": False,
            "items": []
        }
    )

    order = table_data["items"]

    # Don't print an empty KOT
    if len(order) == 0:
        return {"success": False}

    # Print directly to thermal printer
    print_kot_to_printer(
        table_name,
        order
    )

    # KOT does NOT clear the table
    return {"success": True}

@app.route("/bill/<table_name>")
def bill(table_name):

    with open("menu.json", "r") as file:
        menu = json.load(file)

    return render_template(
        "bill.html",
        table=table_name,
        menu=menu
    )
@app.route("/print_bill/<table_name>", methods=["POST"])
def print_bill(table_name):

    # Get the current order from the browser
    order = request.get_json()

    # Don't process an empty bill
    if not order:
        return {"success": False}

    # Generate unique bill number
    bill_number = generate_bill_number()

    # Save permanent PDF
    filename = create_bill_pdf(
        table_name,
        order,
        bill_number
    )

    return {
        "success": True,
        "bill_number": bill_number
    }

@app.route("/settle/<table_name>", methods=["POST"])
def settle(table_name):

    with open("orders.json", "r") as file:
        orders = json.load(file)

    orders[table_name] = {
        "active": False,
        "items": []
    }

    with open("orders.json", "w") as file:
        json.dump(orders, file, indent=4)

    return {"success": True}

@app.route("/table/<table_name>")
def table(table_name):

    # Read menu
    with open("menu.json", "r") as file:
        menu = json.load(file)

    # Read saved orders
    with open("orders.json", "r") as file:
        orders = json.load(file)

    # Get this table's information
    table_data = orders.get(
        table_name,
        {
            "active": False,
            "items": []
        }
    )

    # Get this table's existing order
    current_order = table_data["items"]

    return render_template(
        "menu.html",
        table=table_name,
        menu=menu,
        current_order=current_order
    )


@app.route("/save/<table_name>", methods=["POST"])
def save(table_name):

    # Get order sent by JavaScript
    order = request.get_json()

    # Read existing orders
    with open("orders.json", "r") as file:
        orders = json.load(file)

    # Check whether there is anything in the order
    if len(order) > 0:
        active = True
    else:
        active = False

    # Save order and active status
    orders[table_name] = {
        "active": active,
        "items": order
    }

    # Write back to JSON
    with open("orders.json", "w") as file:
        json.dump(orders, file, indent=4)

    return {"success": True}

@app.route("/")
def home():

    # Read table names
    with open("tables.json", "r") as file:
        tables = json.load(file)

    # Read orders and active status
    with open("orders.json", "r") as file:
        orders = json.load(file)

    return render_template(
        "index.html",
        tables=tables,
        orders=orders
    )

app.run(host="localhost", port=8000, debug=True)