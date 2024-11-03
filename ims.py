from flask import Flask, Response, render_template, request, redirect, url_for, json
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
import smtplib
import os

app = Flask(__name__)

# Set up environment variables 
def _require_env(name):
    value = os.getenv(name)
    if value is None:
        raise Exception(f"Environment variable {name} is not set.")
    return value

# configure MongoDB connection via environment variables
mongo_login = _require_env('MY_MONGODB_LOGIN')
app.config["MONGO_URI"] = mongo_login
mongo = PyMongo(app)

# Test MongoDB Connection
@app.route('/test_db')
def test_db():
    try:
        # Check if connection is successful
        db = mongo.db
        db.command("ping")
        return "Connected to MongoDB successfully!"
    except Exception as e:
        return f"An error occurred: {e}"
    

# Check the stock level and send an email if the stock level is low
def check_stock_level(product_id):
    accepted_stock_level = 2 # Set the accepted stock level 
    try:
        # Retrieve product details from the database
        product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
        if not product:
            print(f"No product found with ID: {product_id}")
            return
        
        # Check if stock level is low
        if product['quantity_in_stock'] > accepted_stock_level:
            print(f"Stock level is sufficient for product {product['name']}")
            return

        # Load SMTP settings from environment variables
        try:
            email_username = os.getenv('EMAIL_HOST_USER')
            email_password = os.getenv('EMAIL_HOST_PASSWORD')
            if not email_username or not email_password:
                raise ValueError("Email credentials are missing")

        except Exception as e:
            print(f"Error loading email credentials: {e}")
            return
        
        # email details
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        smtp_sender = 'my_testing_email77@gmail.com'
        smtp_receiver = 'peter.wirth@gmail.com'
        smtp_subject = 'Low Stock Alert'
        smtp_message = f'The stock level for product {product["name"]} is low. Current stock: {product["quantity_in_stock"]}'

        # Send email notification
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_username, email_password)
                server.sendmail(smtp_sender, smtp_receiver, f'Subject: {smtp_subject}\n\n{smtp_message}')
            print("Email sent successfully!")

        except smtplib.SMTPException as e:
            print(f"Error sending email: {e}")
    
    except Exception as e:
        print(f"An error occurred while checking stock level: {e}")


# Home page - List all products, sales, and invoices
@app.route('/')
def home():
    products = mongo.db.products.find()
    sales = mongo.db.sales.find()
    invoices = mongo.db.invoices.find()
    return render_template('index.html', products=products, sales=sales, invoices=invoices)

# Product Create
@app.route('/products', methods=['GET', 'POST'])
def product_create():
    if request.method == 'POST':
        # Add new product
        product_name = request.form.get('name')
        sku = request.form.get('sku')
        category = request.form.get('category')
        quantity_in_stock = int(request.form.get('quantity_in_stock'))
        price = float(request.form.get('price'))
        description = request.form.get('description')
        product = {  'name': product_name,
                     'quantity_in_stock': quantity_in_stock,
                     'price': price,
                     'sku': sku,
                     'category': category,
                     'description': description}
        # Insert the product into the database and check stock level
        mongo.db.products.insert_one(product)
        check_stock_level(product_id=product['_id'])
        return redirect(url_for('home'))

    products = mongo.db.products.find()
    return render_template('product_add_new.html', products=products)

# Product update / edit
@app.route('/products/<product_id>', methods=['GET', 'POST'])
def product_update(product_id):
    product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
    if request.method == 'POST':
        product_name = request.form.get('name')
        sku = request.form.get('sku')
        category = request.form.get('category')
        quantity_in_stock = int(request.form.get('quantity_in_stock'))
        price = float(request.form.get('price'))
        description = request.form.get('description')
        product = {
            'name': product_name,
            'sku': sku,
            'category': category,
            'quantity_in_stock': quantity_in_stock,
            'price': price,
            'description': description
        }
        # Update the product in the database and check stock level
        mongo.db.products.update_one({'_id': ObjectId(product_id)}, {'$set': product})
        check_stock_level(product_id=product['_id'])
        return redirect(url_for('home'))
    return render_template('product_update.html', product=product)

# Product delete
@app.route('/products/delete/<product_id>', methods=['GET','POST'])
def product_delete(product_id):
    product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
    if request.method == 'POST':
        mongo.db.products.delete_one({'_id': ObjectId(product_id)})
        return redirect(url_for('home'))
    return render_template('product_confirm_delete.html', product=product)


# Sale create
@app.route('/sales', methods=['GET', 'POST'])
def sale_create():
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        quantity_sold = int(request.form.get('quantity_sold'))
        sale = {
            'product_id': ObjectId(product_id),
            'product': mongo.db.products.find_one({'_id': ObjectId(product_id)})['name'],
            'price': mongo.db.products.find_one({'_id': ObjectId(product_id)})['price'],
            'quantity_sold': quantity_sold,
            'sale_date': request.form.get('sale_date')
        }
        # Update product quantity_in_stock (decrease by quantity_sold)
        mongo.db.products.update_one({'_id': ObjectId(product_id)}, {'$inc': {'quantity_in_stock': -quantity_sold}})
        # Insert the sale into the database and check stock level
        mongo.db.sales.insert_one(sale)
        check_stock_level(product_id=product_id)
        return redirect(url_for('home'))

    # List all sales
    sales = mongo.db.sales.find()
    products = {str(product['_id']): product['name'] for product in mongo.db.products.find()}
    return render_template('sale_create.html', sales=sales, products=products)

# Sale delete
@app.route('/sales/delete/<sale_id>', methods=['GET','POST'])
def sale_delete(sale_id):
    sale = mongo.db.sales.find_one({'_id': ObjectId(sale_id)})
    if request.method == 'POST':
        # Update product quantity_in_stock
        mongo.db.products.update_one({'_id': sale['product_id']}, {'$inc': {'quantity_in_stock': sale['quantity_sold']}})
        # Delete the sale
        mongo.db.sales.delete_one({'_id': ObjectId(sale_id)})
        return redirect(url_for('home'))
    return render_template('sale_confirm_delete.html', sale=sale)

# Invoice create
@app.route('/invoice/new', methods=['GET', 'POST'])
def invoice_create():
    if request.method == 'POST':
        sale_ids = request.form.getlist('sales')
        sales = [ObjectId(sale_id) for sale_id in sale_ids]
        invoice_number = request.form.get('invoice_number')
        total_amount = sum(sale['quantity_sold'] * mongo.db.products.find_one({'_id': sale['product_id']})['price']
                           for sale in mongo.db.sales.find({'_id': {'$in': sales}}))
        invoice = {'invoice_number': invoice_number, 'sales': sales, 'total_amount': total_amount}
        mongo.db.invoices.insert_one(invoice)
        return redirect(url_for('invoice_detail', invoice_id=invoice['_id']))

    sales = mongo.db.sales.find()
    return render_template('invoice_form.html', sales=sales)

# Invoice detail
@app.route('/invoice/<invoice_id>', methods=['GET', 'POST'])
def invoice_detail(invoice_id):
    if request.method == 'POST':
        # Fetch the invoice and related sales
        invoice = mongo.db.invoices.find_one({'_id': ObjectId(invoice_id)})
        sales = mongo.db.sales.find({'_id': {'$in': invoice['sales']}})
        
        # Create a list of product details for each sale item
        product_details = []
        for sale in sales:
            product = mongo.db.products.find_one({'_id': sale['product_id']})
            if product:            
                product_details.append({
                    'name': product['name'],
                    'quantity': sale.get('quantity_sold',0)                 
                })

        # Create the invoice dictionary with product details
        invoice_dict = {
            'invoice_number': invoice['invoice_number'],
            'total_amount': invoice['total_amount'],
            'products': product_details
        }

        # Convert dictionary to JSON string
        invoice_json = json.dumps(invoice_dict)

        # Create the response object and set headers with invoice number as filename
        filename = f"invoice_{invoice['invoice_number']}.json"
        response = Response(invoice_json, mimetype='application/json')
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'

        # Return the response to trigger the file download
        return response

    
    invoice = mongo.db.invoices.find_one({'_id': ObjectId(invoice_id)})
    sales = mongo.db.sales.find({'_id': {'$in': invoice['sales']}})
    products = {str(product['_id']): product['name'] for product in mongo.db.products.find()}

    return render_template('invoice_detail.html', invoice=invoice, sales=sales, products=products)

# Invoice delete
@app.route('/invoice/delete/<invoice_id>', methods=['GET', 'POST'])
def invoice_delete(invoice_id):
    invoice = mongo.db.invoices.find_one({'_id': ObjectId(invoice_id)})
    if request.method == 'POST':
        mongo.db.invoices.delete_one({'_id': ObjectId(invoice_id)})
        return redirect(url_for('home'))  
    return render_template('invoice_confirm_delete.html', invoice=invoice)
  
# Invoice list
@app.route('/invoices')
def manage_invoices():
    invoices = mongo.db.invoices.find()
    return render_template('invoice_list.html', invoices=invoices)





if __name__ == "__main__":
    app.run(debug=True)
