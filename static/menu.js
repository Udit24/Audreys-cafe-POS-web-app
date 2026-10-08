let order = savedOrder || [];


// ----------------------------------------
// ADD ITEM
// ----------------------------------------

function addItem(itemId) {

    // Find item in menu
    let menuItem = menu.find(item => item.id === itemId);

    // Check whether item is already in order
    let existingItem = order.find(item => item.id === itemId);


    if (existingItem) {

        // Already there → increase quantity
        existingItem.quantity += 1;

    } else {

        // Not there → add it
        order.push({
            id: itemId,
            quantity: 1
        });

    }

    displayBill();
}


// ----------------------------------------
// INCREASE QUANTITY
// ----------------------------------------

function increaseItem(itemId) {

    let item = order.find(item => item.id === itemId);

    if (item) {
        item.quantity += 1;
    }

    displayBill();
}


// ----------------------------------------
// DECREASE QUANTITY
// ----------------------------------------

function decreaseItem(itemId) {

    let item = order.find(item => item.id === itemId);

    if (!item) {
        return;
    }

    item.quantity -= 1;


    // If quantity reaches zero, remove it
    if (item.quantity <= 0) {

        order = order.filter(
            item => item.id !== itemId
        );

    }

    displayBill();
}


// ----------------------------------------
// REMOVE ITEM COMPLETELY
// ----------------------------------------

function removeItem(itemId) {

    order = order.filter(
        item => item.id !== itemId
    );

    displayBill();
}


// ----------------------------------------
// DISPLAY BILL
// ----------------------------------------

function displayBill() {

    let billContainer =
        document.getElementById("bill-items");

    billContainer.innerHTML = "";


    let total = 0;


    for (let orderItem of order) {

        // Find information about item
        let menuItem = menu.find(
            item => item.id === orderItem.id
        );


        if (!menuItem) {
            continue;
        }


        let itemTotal =
            menuItem.price * orderItem.quantity;

        total += itemTotal;


        // Create bill row

        let row = document.createElement("div");

        row.className = "bill-item";


        row.innerHTML = `

            <div class="bill-item-info">

                <div class="bill-item-name">
                    ${menuItem.name}
                </div>

                <div class="bill-item-price">
                    ₹${itemTotal}
                </div>

            </div>


            <div class="quantity-controls">

                <button
                    onclick="decreaseItem('${menuItem.id}')"
                >
                    −
                </button>


                <span>
                    ${orderItem.quantity}
                </span>


                <button
                    onclick="increaseItem('${menuItem.id}')"
                >
                    +
                </button>


                <button
                    class="remove-button"
                    onclick="removeItem('${menuItem.id}')"
                >
                    ×
                </button>

            </div>

        `;


        billContainer.appendChild(row);
    }


    // Update total

    document.getElementById("total").innerText =
        "₹" + total;
}


// ----------------------------------------
// SAVE ORDER / CLEAR ORDER
// ----------------------------------------

function saveOrder() {

    fetch("/save/" + tableName, {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify(order)

    })

    .then(response => response.json())

    .then(data => {

        if (data.success) {

            // Go back to table page
            window.location.href = "/";

        }

    });

}
function clearOrder() {

    order = [];

    displayBill();

    fetch("/save/" + tableName, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(order)
    })
    .then(response => response.json())
    .then(data => {

        if (data.success) {
            window.location.href = "/";
        }

    });

}
function printKOT() {

    if (order.length === 0) {
        alert("There is nothing to print.");
        return;
    }

    fetch("/save/" + tableName, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(order)
    })
    .then(response => response.json())
    .then(data => {

        if (data.success) {

            return fetch("/print_kot/" + tableName, {
                method: "POST"
            });

        }

    })
    .then(response => response.json())
    .then(data => {

        if (data.success) {
            alert("KOT printed.");
        }

    });

}
function printBill() {

    if (order.length === 0) {
        alert("There is nothing to bill.");
        return;
    }

    // Open bill.html immediately.
    // This prevents the browser from blocking the popup.
    let printWindow = window.open(
        "/bill/" + tableName,
        "_blank",
        "width=500,height=700"
    );

    if (!printWindow) {
        alert("Please allow pop-ups for this POS.");
        return;
    }


    // Create the permanent bill PDF
    fetch("/print_bill/" + tableName, {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify(order)

    })

    .then(response => response.json())

    .then(data => {

        if (!data.success) {

            printWindow.close();

            alert("Could not create bill.");

            return;
        }


        // Wait until bill.html has loaded
        if (printWindow.document.readyState === "complete") {

            sendBillToWindow(
                printWindow,
                data.bill_number
            );

        } else {

            printWindow.onload = function() {

                sendBillToWindow(
                    printWindow,
                    data.bill_number
                );

            };

        }

    })

    .catch(error => {

        console.error(error);

        printWindow.close();

        alert("Could not create bill.");

    });

}


function sendBillToWindow(printWindow, billNumber) {

    printWindow.postMessage(

        {
            type: "billData",

            table: tableName,

            order: order,

            billNumber: billNumber
        },

        window.location.origin

    );

}

window.addEventListener("message", function(event) {

    // Only accept messages from our own POS
    if (event.origin !== window.location.origin) {
        return;
    }


    // Bill printed successfully
    if (event.data.type === "billPrinted") {

        settleTable();

    }


    // Bill was cancelled
    if (event.data.type === "billPrintCancelled") {

        alert(
            "Bill was not settled because printing was cancelled."
        );

    }

});
function settleTable() {

    fetch("/settle/" + tableName, {

        method: "POST"

    })

    .then(response => response.json())

    .then(data => {

        if (data.success) {

            window.location.href = "/";

        } else {

            alert("Could not settle the table.");

        }

    })

    .catch(error => {

        console.error(error);

        alert("Could not settle the table.");

    });

}


function createPrintBill() {

    const tbody = document.querySelector("#print-items tbody");

    tbody.innerHTML = "";

    let subtotal = 0;

    order.forEach(orderedItem => {

        const item = menu.find(
            item => item.id === orderedItem.id
        );

        const quantity = orderedItem.quantity;

        const amount = item.price * quantity;

        subtotal += amount;

        const row = document.createElement("tr");

        row.innerHTML = `
            <td>${item.name}</td>
            <td>${quantity}</td>
            <td>₹${item.price.toFixed(2)}</td>
            <td>₹${amount.toFixed(2)}</td>
        `;

        tbody.appendChild(row);
    });

    const cgst = subtotal * 0.025;
    const sgst = subtotal * 0.025;
    const grandTotal = subtotal + cgst + sgst;

    document.getElementById("print-date").textContent =
        new Date().toLocaleString();

    document.getElementById("print-subtotal").textContent =
        subtotal.toFixed(2);

    document.getElementById("print-cgst").textContent =
        cgst.toFixed(2);

    document.getElementById("print-sgst").textContent =
        sgst.toFixed(2);

    document.getElementById("print-grand-total").textContent =
        grandTotal.toFixed(2);
}
// ----------------------------------------
// DISPLAY SAVED ORDER WHEN PAGE OPENS
// ----------------------------------------

displayBill();