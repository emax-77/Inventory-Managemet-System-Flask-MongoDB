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

# Home page - List all Products-Sales-Invoices
@app.route('/')
def home():
    try:
        products = list(mongo.db.products.find())
        sales = list(mongo.db.sales.find())
        invoices = list(mongo.db.invoices.find())
        return render_template('index.html', products=products, sales=sales, invoices=invoices)
    except Exception as e:
        print(f"Error loading home page data: {e}")
        return "Error loading data", 500

# Product Create
@app.route('/products', methods=['GET', 'POST'])
def product_create():
    if request.method == 'POST':
        try:
            product_name = request.form.get('name')
            sku = request.form.get('sku')
            category = request.form.get('category')
            quantity_in_stock = int(request.form.get('quantity_in_stock'))
            price = float(request.form.get('price'))
            description = request.form.get('description')

            product = {
                'name': product_name,
                'quantity_in_stock': quantity_in_stock,
                'price': price,
                'sku': sku,
                'category': category,
                'description': description
            }
            # Insert the product into the database and check stock level
            mongo.db.products.insert_one(product)
            check_stock_level(product_id=product['_id'])
            return redirect(url_for('home'))
        except Exception as e:
            print(f"Error creating product: {e}")
            return "Error creating product", 500

    try:
        products = list(mongo.db.products.find())
        return render_template('product_add_new.html', products=products)
    except Exception as e:
        print(f"Error loading products: {e}")
        return "Error loading products", 500

# Product update / edit
@app.route('/products/<product_id>', methods=['GET', 'POST'])
def product_update(product_id):
    try:
        product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
        if not product:
            return "Product not found", 404

        if request.method == 'POST':
            try:
                product_name = request.form.get('name')
                sku = request.form.get('sku')
                category = request.form.get('category')
                quantity_in_stock = int(request.form.get('quantity_in_stock'))
                price = float(request.form.get('price'))
                description = request.form.get('description')
                
                updated_product = {
                    'name': product_name,
                    'sku': sku,
                    'category': category,
                    'quantity_in_stock': quantity_in_stock,
                    'price': price,
                    'description': description
                }
                # Update the product in the database and check stock level
                mongo.db.products.update_one({'_id': ObjectId(product_id)}, {'$set': updated_product})
                check_stock_level(product_id=product_id)
                return redirect(url_for('home'))
            except Exception as e:
                print(f"Error updating product: {e}")
                return "Error updating product", 500
        
        return render_template('product_update.html', product=product)
    except Exception as e:
        print(f"Error loading product: {e}")
        return "Error loading product", 500

# Product delete
@app.route('/products/delete/<product_id>', methods=['GET','POST'])
def product_delete(product_id):
    try:
        product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
        if not product:
            return "Product not found", 404

        if request.method == 'POST':
            # Delete the product from the database
            mongo.db.products.delete_one({'_id': ObjectId(product_id)})
            return redirect(url_for('home'))

        return render_template('product_confirm_delete.html', product=product)
    except Exception as e:
        print(f"Error deleting product: {e}")
        return "Error deleting product", 500

# Sale create
@app.route('/sales', methods=['GET', 'POST'])
def sale_create():
    if request.method == 'POST':
        try:
            product_id = request.form.get('product_id')
            quantity_sold = int(request.form.get('quantity_sold'))
            product = mongo.db.products.find_one({'_id': ObjectId(product_id)})

            if not product:
                return "Product not found", 404

            sale = {
                'product_id': ObjectId(product_id),
                'product': product['name'],
                'price': product['price'],
                'quantity_sold': quantity_sold,
                'sale_date': request.form.get('sale_date')
            }
            # Insert the sale into the database, update the product stock level & check stock level 
            mongo.db.sales.insert_one(sale)
            mongo.db.products.update_one({'_id': ObjectId(product_id)}, {'$inc': {'quantity_in_stock': -quantity_sold}})
            check_stock_level(product_id=product_id)
            return redirect(url_for('home'))
        except Exception as e:
            print(f"Error creating sale: {e}")
            return "Error creating sale", 500

    try:
        sales = list(mongo.db.sales.find())
        products = {str(product['_id']): product['name'] for product in mongo.db.products.find()}
        return render_template('sale_create.html', sales=sales, products=products)
    except Exception as e:
        print(f"Error loading sales: {e}")
        return "Error loading sales", 500

# Sale delete
@app.route('/sales/delete/<sale_id>', methods=['GET','POST'])
def sale_delete(sale_id):
    try:
        sale = mongo.db.sales.find_one({'_id': ObjectId(sale_id)})
        if not sale:
            return "Sale not found", 404

        if request.method == 'POST':
            # Delete the sale from the database and update the product stock level
            mongo.db.sales.delete_one({'_id': ObjectId(sale_id)})
            mongo.db.products.update_one({'_id': sale['product_id']}, {'$inc': {'quantity_in_stock': sale['quantity_sold']}})
            return redirect(url_for('home'))

        return render_template('sale_confirm_delete.html', sale=sale)
    except Exception as e:
        print(f"Error deleting sale: {e}")
        return "Error deleting sale", 500

# Invoice create
@app.route('/invoice/new', methods=['GET', 'POST'])
def invoice_create():
    if request.method == 'POST':
        try:
            sale_ids = request.form.getlist('sales')
            sales = [ObjectId(sale_id) for sale_id in sale_ids]
            invoice_number = request.form.get('invoice_number')
            total_amount = sum(sale['quantity_sold'] * mongo.db.products.find_one({'_id': sale['product_id']})['price']
                               for sale in mongo.db.sales.find({'_id': {'$in': sales}}))
            invoice = {'invoice_number': invoice_number, 'sales': sales, 'total_amount': total_amount}
            # Insert the invoice into the database
            mongo.db.invoices.insert_one(invoice)
            return redirect(url_for('invoice_detail', invoice_id=invoice['_id']))
        except Exception as e:
            print(f"Error creating invoice: {e}")
            return "Error creating invoice", 500

    try:
        sales = list(mongo.db.sales.find())
        return render_template('invoice_form.html', sales=sales)
    except Exception as e:
        print(f"Error loading invoice form: {e}")
        return "Error loading invoice form", 500

# Invoice detail
@app.route('/invoice/<invoice_id>', methods=['GET', 'POST'])
def invoice_detail(invoice_id):
    try:
        invoice = mongo.db.invoices.find_one({'_id': ObjectId(invoice_id)})
        if not invoice:
            return "Invoice not found", 404

        sales = mongo.db.sales.find({'_id': {'$in': invoice['sales']}})
        products = {str(product['_id']): product['name'] for product in mongo.db.products.find()}

        # Create a dictionary to store the product details, save the invoice as a JSON file and download it
        if request.method == 'POST':
            product_details = [
                {
                    'name': mongo.db.products.find_one({'_id': sale['product_id']})['name'],
                    'quantity': sale['quantity_sold']
                }
                for sale in sales
            ]
            invoice_dict = {
                'invoice_number': invoice['invoice_number'],
                'total_amount': invoice['total_amount'],
                'products': product_details
            }
            invoice_json = json.dumps(invoice_dict)
            filename = f"invoice_{invoice['invoice_number']}.json"
            response = Response(invoice_json, mimetype='application/json')
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            return response

        return render_template('invoice_detail.html', invoice=invoice, sales=sales, products=products)
    except Exception as e:
        print(f"Error loading invoice details: {e}")
        return "Error loading invoice details", 500

# Invoice delete
@app.route('/invoice/delete/<invoice_id>', methods=['GET', 'POST'])
def invoice_delete(invoice_id):
    try:
        invoice = mongo.db.invoices.find_one({'_id': ObjectId(invoice_id)})
        if not invoice:
            return "Invoice not found", 404

        if request.method == 'POST':
            # Delete the invoice from the database
            mongo.db.invoices.delete_one({'_id': ObjectId(invoice_id)})
            return redirect(url_for('home'))

        return render_template('invoice_confirm_delete.html', invoice=invoice)
    except Exception as e:
        print(f"Error deleting invoice: {e}")
        return "Error deleting invoice", 500

# Invoice list
@app.route('/invoices')
def manage_invoices():
    try:
        invoices = list(mongo.db.invoices.find())
        return render_template('invoice_list.html', invoices=invoices)
    except Exception as e:
        print(f"Error loading invoices: {e}")
        return "Error loading invoices", 500

if __name__ == "__main__":
    app.run(debug=True)
