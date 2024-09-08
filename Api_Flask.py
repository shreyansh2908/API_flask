from flask import Flask, request, jsonify, render_template, abort
from flask_sqlalchemy import SQLAlchemy
import json

app = Flask(__name__)

# Configure your database connection here
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:0302@localhost:3306/LAB11'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the Menu model
class Menu(db.Model):
    __tablename__ = 'Menu'
    item_id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(80), nullable=False)
    item_price = db.Column(db.Integer, nullable=False)

# Define the CustomerOrder model
class CustomerOrder(db.Model):
    __tablename__ = 'CustomerOrder'
    customer_id = db.Column(db.Integer, primary_key=True)
    items = db.Column(db.JSON, nullable=False)  # JSON column to store list of item_ids

with app.app_context():
    db.create_all()

def require_appropriate_headers(f):
    def decorator(*args, **kwargs):
        if request.headers.get('rootOrg') != 'Restuarant' or request.headers.get('org') != 'Shaandar':
            abort(418)
        return f(*args, **kwargs)
    decorator.__name__ = f.__name__
    return decorator

@app.errorhandler(418)
def teapot_error(e):
    return jsonify(error="There is some issue. Please try again"), 418

@app.route('/admin/menu', methods=['GET'])
@require_appropriate_headers
def view_menu_list():
    menu_items = Menu.query.all()
    return jsonify([{'item_id': item.item_id, 'item_name': item.item_name, 'item_price': item.item_price} for item in menu_items]), 200

@app.route('/admin/menu', methods=['POST'])
@require_appropriate_headers
def add_menu_item():
    data = request.json
    if Menu.query.get(data['item_id']):
        abort(418)  # Item already exists
    new_item = Menu(item_id=data['item_id'], item_name=data['item_name'], item_price=data['item_price'])
    db.session.add(new_item)
    db.session.commit()
    return jsonify(message="Item added successfully."), 200

@app.route('/admin/menu', methods=['PUT'])
@require_appropriate_headers
def update_menu_item():
    data = request.json
    item = Menu.query.get(data['item_id'])
    if not item:
        abort(418)  # Item does not exist
    item.item_name = data['item_name']
    item.item_price = data['item_price']
    db.session.commit()
    return jsonify(message="Item updated successfully."), 200

@app.route('/staff/orders', methods=['GET'])
@require_appropriate_headers
def view_customer_orders():
    all_orders = CustomerOrder.query.all()
    orders_list = []
    for order in all_orders:
        items_list = json.loads(order.items)
        detailed_items = []
        for item_id in items_list:
            item = Menu.query.get(item_id)
            if item:
                detailed_items.append({
                    'item_id': item.item_id,
                    'item_name': item.item_name,
                    'item_price': item.item_price
                })
        orders_list.append({
            'customer_id': order.customer_id,
            'items': detailed_items
        })
    return jsonify(orders_list), 200

@app.route('/staff/bill', methods=['GET'])
@require_appropriate_headers
def view_order_and_bill_amount():
    customer_id = request.args.get('customer_id')
    order = CustomerOrder.query.filter_by(customer_id=customer_id).first()
    if order:
        items_list = json.loads(order.items)
        detailed_items = []
        bill_amount = 0
        for item_id in items_list:
            item = Menu.query.get(item_id)
            if item:
                detailed_items.append({
                    'item_id': item.item_id,
                    'item_name': item.item_name,
                    'item_price': item.item_price
                })
                bill_amount += item.item_price
        return jsonify({
            'customer_id': customer_id,
            'bill_amount': bill_amount,
            'items': detailed_items
        }), 200
    else:
        abort(418)

@app.route('/customer/order', methods=['GET'])
@require_appropriate_headers
def view_current_order():
    customer_id = request.headers.get('customerId')
    order = CustomerOrder.query.filter_by(customer_id=customer_id).first()
    if order:
        items_list = json.loads(order.items)
        detailed_items = []
        for item_id in items_list:
            item = Menu.query.get(item_id)
            if item:
                detailed_items.append({
                    'item_id': item.item_id,
                    'item_name': item.item_name,
                    'price': item.item_price
                })
        return jsonify(detailed_items), 200
    else:
        abort(418)

@app.route('/customer/order/add', methods=['POST'])
@require_appropriate_headers
def add_item_to_order():
    customer_id = request.headers.get('customerId')
    data = request.json
    item = Menu.query.get(data['item_id'])
    if not item:
        abort(418)  # Item not in menu
    order = CustomerOrder.query.filter_by(customer_id=customer_id).first()
    if not order:
        order = CustomerOrder(customer_id=customer_id, items=json.dumps([]))
        db.session.add(order)
    items_list = json.loads(order.items)
    if data['item_id'] not in items_list:
        items_list.append(data['item_id'])
        order.items = json.dumps(items_list)
        db.session.commit()
        return jsonify(message="Item added to the order successfully."), 200
    else:
        abort(418)  # Item already in order

@app.route('/customer/order/remove/<int:item_id>', methods=['DELETE'])
@require_appropriate_headers
def remove_item_from_order(item_id):
    customer_id = request.headers.get('customerId')
    order = CustomerOrder.query.filter_by(customer_id=customer_id).first()
    if not order:
        abort(418)  # Order not found
    items_list = json.loads(order.items)
    if item_id in items_list:
        items_list.remove(item_id)
        order.items = json.dumps(items_list)
        db.session.commit()
        return jsonify(message="Item removed from the order successfully."), 200
    else:
        abort(418)  # Item not in order

@app.route('/customer/bill', methods=['GET'])
@require_appropriate_headers
def render_bill():
    customer_id = request.headers.get('customerId')
    order = CustomerOrder.query.filter_by(customer_id=customer_id).first()
    if not order:
        abort(418)  # Order not found
    items_list = json.loads(order.items)
    detailed_items = []
    total_price = 0
    for item_id in items_list:
        item = Menu.query.get(item_id)
        if item:
            detailed_items.append({
                'item_id': item.item_id,
                'item_name': item.item_name,
                'item_price': item.item_price
            })
            total_price += item.item_price
    # Assuming you have a 'bill.html' in your 'templates' directory
    return render_template('bill.html', items=detailed_items, total_price=total_price, customer_id=customer_id)

if __name__ == '__main__':
    app.run(debug=True)
