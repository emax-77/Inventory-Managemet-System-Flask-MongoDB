from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_pymongo import PyMongo
from bson.objectid import ObjectId

app = Flask(__name__)

# Set up environment variables
import os
def _require_env(name):
    value = os.getenv(name)
    if value is None:
        raise Exception(f"Environment variable {name} is not set.")
    return value

# Use environment variables for MongoDB login
mongo_login = _require_env('MY_MONGODB_LOGIN')

# Configure MongoDB connection via environment variables
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

# Home page
@app.route('/')
def home():
    products = mongo.db.products.find()
    sales = mongo.db.sales.find()
    invoices = mongo.db.invoices.find()
    return render_template('index.html', products=products, sales=sales, invoices=invoices)

# Product creation
@app.route('/products', methods=['GET', 'POST'])
def manage_products():
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
        # Insert the product into the database
        mongo.db.products.insert_one(product)
        return redirect(url_for('manage_products'))

    # List all products
    products = mongo.db.products.find()
    return render_template('product_list.html', products=products)

# Product update / edit
@app.route('/products/<product_id>', methods=['GET', 'POST'])
def update_product(product_id):
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
        mongo.db.products.update_one({'_id': ObjectId(product_id)}, {'$set': product})
        return redirect(url_for('manage_products'))
    return render_template('update_product.html', product=product)

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
def manage_sales():
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
        mongo.db.sales.insert_one(sale)
        return redirect(url_for('manage_sales'))

    # List all sales
    sales = mongo.db.sales.find()
    products = {str(product['_id']): product['name'] for product in mongo.db.products.find()}
    return render_template('sale_list.html', sales=sales, products=products)

# Sale delete
@app.route('/sales/<sale_id>/delete', methods=['POST'])
def delete_sale(sale_id):
    mongo.db.sales.delete_one({'_id': ObjectId(sale_id)})
    return redirect(url_for('manage_sales'))


# Invoice create
@app.route('/invoice/new', methods=['GET', 'POST'])
def create_invoice():
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
@app.route('/invoice/<invoice_id>')
def invoice_detail(invoice_id):
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
