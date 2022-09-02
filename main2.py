
#flask app for ecom
from flask import *
import sqlite3, hashlib, os
from werkzeug.utils import secure_filename
import requests
import logging
import os
from google.cloud import pubsub_v1

import pymysql.cursors

app = Flask(__name__)
connection = pymysql.connect(host='34.122.186.168',
                             user='root',
                             password='Asdf@1234',
                             database='ecom')


logging.info('MYSQL connection setup created')
# @app.route("/main")
# def main():
        # with connection:
                # with connection.cursor() as cursor:
                        # sql = "SELECT `id`, `password` FROM `users` WHERE `email`=%s"
                        # sql="show databases"
                        # cursor.execute(sql, ('webmaster@python.org',))
                        # cursor.execute(sql)
                        # result = cursor.fetchone()
                        # print("connection successfull")
                        # print(result)
                        # return(result)



publisher = pubsub_v1.PublisherClient()
topic_name = 'projects/casestudyproject-358809/topics/flask-gcp-topic'.format(
    project_id=os.getenv('GOOGLE_CLOUD_PROJECT'),
    topic='flask-gcp-topic', 
)

logging.info('This app is using pub-sub TOPIC as projects/casestudyproject-358809/topics/flask-gcp-topic')

#app = Flask(__name__)
app.secret_key = 'random string'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = set(['jpeg', 'jpg', 'png', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#main route
#Home page
@app.route("/")
def root():
    loggedIn, firstName, noOfItems = getLoginDetails()
    with connection.cursor() as conn:
        cur = conn
        cur.execute('SELECT productId, name, price, description, image, stock FROM products')
        itemData = cur.fetchall()
        cur.execute('SELECT categoryId, name FROM categories')
        categoryData = cur.fetchall()
        print(itemData,"-------------------->",type(itemData))
        logging.debug("itemData print")
        print(categoryData,type(categoryData))
    itemData = parse(itemData)
    future = publisher.publish(topic_name, b'1 user is accessing application', datakey='application accessed')
    future.result()
    print("connection completed")
    logging.info("MYSQL connection created")
    return render_template('home_search.html', itemData=itemData, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems, categoryData=categoryData)

#Fetch user details if logged in
def getLoginDetails():
    with connection.cursor() as conn:
        cur = conn
        if 'email' not in session:
            loggedIn = False
            firstName = ''
            noOfItems = 0
        else:
            loggedIn = True
            cur.execute("SELECT userId, firstName FROM users WHERE email = '" + session['email'] + "'")
            userId, firstName = cur.fetchone()
            cur.execute("SELECT count(productId) FROM kart WHERE userId = " + str(userId))
            noOfItems = cur.fetchone()[0]
    conn.close()
    return (loggedIn, firstName, noOfItems)

#Add item to cart
@app.route("/addItem", methods=["GET", "POST"])
def addItem():
    if request.method == "POST":
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        stock = int(request.form['stock'])
        categoryId = int(request.form['category'])

        #Upload image
        image = request.files['image']
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        imagename = filename
        with connection.cursor() as conn:
            try:
                cur = conn
                cur.execute('''INSERT INTO products (name, price, description, image, stock, categoryId) VALUES (?, ?, ?, ?, ?, ?)''', (name, price, description, imagename, stock, categoryId))
                connection.commit()
                msg="Added successfully"
                logging.debug("Item added in Cart")
            except:
                msg="Error occured"
                logging.error("Problem in adding Cart")
                connection.rollback()
        conn.close()
        print(msg)
        logging.info("item added")
        return redirect(url_for('root'))

#Remove item from cart
@app.route("/removeItem")
def removeItem():
    productId = request.args.get('productId')
    with connection.cursor() as conn:
        try:
            cur = conn
            cur.execute('DELETE FROM products WHERE productID = ' + productId)
            conn.commit()
            msg = "Deleted successsfully"
        except:
            conn.rollback()
            msg = "Error occured"
    conn.close()
    print(msg)
    return redirect(url_for('root'))

#Display all items of a category
@app.route("/displayCategory")
def displayCategory():
        loggedIn, firstName, noOfItems = getLoginDetails()
        categoryId = request.args.get("categoryId")
        with connection.cursor() as conn:
            cur = conn
            cur.execute("SELECT products.productId, products.name, products.price, products.image, categories.name FROM products, categories WHERE products.categoryId = categories.categoryId AND categories.categoryId = " + categoryId)
            data = cur.fetchall()
        conn.close()
        categoryName = data[0][4]
        data = parse(data)
        return render_template('displayCategory.html', data=data, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems, categoryName=categoryName)

@app.route("/account/profile")
def profileHome():
    if 'email' not in session:
        return redirect(url_for('root'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    return render_template("profileHome.html", loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

@app.route("/account/profile/edit")
def editProfile():
    if 'email' not in session:
        return redirect(url_for('root'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    with connection.cursor() as conn:
        cur = conn
        cur.execute("SELECT userId, email, firstName, lastName, address1, address2, zipcode, city, state, country, phone FROM users WHERE email = '" + session['email'] + "'")
        profileData = cur.fetchone()
    conn.close()
    return render_template("editProfile.html", profileData=profileData, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

@app.route("/account/profile/changePassword", methods=["GET", "POST"])
def changePassword():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    if request.method == "POST":
        oldPassword = request.form['oldpassword']
        #oldPassword = hashlib.md5(oldPassword.encode()).hexdigest()
        newPassword = request.form['newpassword']
        #newPassword = hashlib.md5(newPassword.encode()).hexdigest()
        with connection.cursor() as conn:
            cur = conn
            cur.execute("SELECT userId, password FROM users WHERE email = '" + session['email'] + "'")
            userId, password = cur.fetchone()
            if (password == oldPassword):
                try:
                    cur.execute("UPDATE users SET password = ? WHERE userId = ?", (newPassword, userId))
                    connection.commit()
                    msg="Changed successfully"
                    logging.info("Password Changed Successfully")
                except:
                    connection.rollback()
                    msg = "Failed"
                    logging.error("Update failed")
                return render_template("changePassword.html", msg=msg)
            else:
                msg = "Wrong password"
        conn.close()
        future = publisher.publish(topic_name, b'Password is successfully changed', datakey='password changed')
        future.result()
        return render_template("changePassword.html", msg=msg)
    else:
        return render_template("changePassword.html")
















 #Display search results
@app.route("/q", methods=["GET", "POST"])
def q():
    loggedIn, firstName, noOfItems = getLoginDetails()
    if request.method == "POST":        
        search_q=request.form['q']
        search_q={"search_q":search_q}
        print("search query is ",search_q)
        endpoint="https://flask-gcp-search-2-nsayxgrsra-uc.a.run.app/query"
        #itemData,loggedIn, firstName, noOfItems,categoryData=requests.get(endpoint,params=search_q)
        data_return=requests.get(endpoint,params=search_q)
        #print(type(data_return))
        #print(type(data_return.text),data_return.text)
        #print(data_return.json())
        #print(tuple(data_return.json()["categoryData"]),"----------------------------",data_return.json()["itemData"])
        itemData=tuple(data_return.json()["itemData"])
        categoryData=tuple(data_return.json()["categoryData"])
        print("itemData", itemData,"------------>",categoryData)
        return render_template('home_search.html',itemData=itemData,loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems,categoryData=categoryData)

@app.route("/updateProfile", methods=["GET", "POST"])
def updateProfile():
    if request.method == 'POST':
        email = request.form['email']
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        address1 = request.form['address1']
        address2 = request.form['address2']
        zipcode = request.form['zipcode']
        city = request.form['city']
        state = request.form['state']
        country = request.form['country']
        phone = request.form['phone']
        with connection.cursor() as con:
                try:
                    cur = con.cursor()
                    cur.execute('UPDATE users SET firstName = ?, lastName = ?, address1 = ?, address2 = ?, zipcode = ?, city = ?, state = ?, country = ?, phone = ? WHERE email = ?', (firstName, lastName, address1, address2, zipcode, city, state, country, phone, email))

                    connection.commit()
                    msg = "Saved Successfully"
                except:
                    connection.rollback()
                    msg = "Error occured"
        con.close()
        return redirect(url_for('editProfile'))

@app.route("/loginForm")
def loginForm():
    if 'email' in session:
        return redirect(url_for('root'))
    else:
        return render_template('login.html', error='')

@app.route("/login", methods = ['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if is_valid(email, password):
            session['email'] = email
            future = publisher.publish(topic_name, b'User logged in successfully', datakey='used logged in')
            future.result()
            logging.info("logged in success")
            return redirect(url_for('root'))
        else:
            error = 'Invalid UserId / Password'
            logging.warning("Invalid UserId / Password")
            return render_template('login.html', error=error)

@app.route("/productDescription")
def productDescription():
    loggedIn, firstName, noOfItems = getLoginDetails()
    productId = request.args.get('productId')
    with connection.cursor() as conn:
        cur = conn
        cur.execute('SELECT productId, name, price, description, image, stock FROM products WHERE productId = ' + productId)
        productData = cur.fetchone()
    conn.close()
    return render_template("productDescription.html", data=productData, loggedIn = loggedIn, firstName = firstName, noOfItems = noOfItems)

@app.route("/addToCart")
def addToCart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    else:
        productId = int(request.args.get('productId'))
        with connection.cursor() as conn:
            cur = conn
            cur.execute("SELECT userId FROM users WHERE email = '" + session['email'] + "'")
            userId = cur.fetchone()[0]
            try:
                print(userId, type(userId))
                print(productId,type(productId))
                sql_q="INSERT INTO kart (userId, productId) VALUES ({0}, {1})".format(userId,productId)
                print("-------------->",sql_q)
                val_u=(userId, productId)
                #cur.execute("INSERT INTO kart (userId, productId) VALUES (?, ?)", [userId, productId])
                cur.execute(sql_q)
                connection.commit()
                msg = "Added successfully"
                logging.info("Item added in cart")
                future = publisher.publish(topic_name, b'Item added in cart', datakey='item added')
                future.result()
            except:
                connection.rollback()
                msg = "Error occured"
        conn.close()
        return redirect(url_for('root'))

@app.route("/cart")
def cart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    email = session['email']
    with connection.cursor() as conn:
        cur = conn
        cur.execute("SELECT userId FROM users WHERE email = '" + email + "'")
        userId = cur.fetchone()[0]
        cur.execute("SELECT products.productId, products.name, products.price, products.image FROM products, kart WHERE products.productId = kart.productId AND kart.userId = " + str(userId))
        products = cur.fetchall()
    totalPrice = 0
    for row in products:
        totalPrice += row[2]
    return render_template("cart.html", products = products, totalPrice=totalPrice, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

@app.route("/checkout")
def checkout():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    email = session['email']
    with connection.cursor() as conn:
        cur = conn
        cur.execute("SELECT userId FROM users WHERE email = '" + email + "'")
        userId = cur.fetchone()[0]
        cur.execute("SELECT products.productId, products.name, products.price, products.image FROM products, kart WHERE products.productId = kart.productId AND kart.userId = " + str(userId))
        products = cur.fetchall()
    future = publisher.publish(topic_name, b'Successfully placed order ', datakey='order placed')
    future.result()
    logging.info("order placed")
    totalPrice = 0
    for row in products:
        totalPrice += row[2]
    return render_template("checkout.html", products = products, totalPrice=totalPrice, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)


@app.route("/logout")
def logout():
    session.pop('email', None)
    return redirect(url_for('root'))

def is_valid(email, password):
    con = connection.cursor() 
    cur = con
    cur.execute('SELECT email, password FROM users')
    data = cur.fetchall()
    for row in data:
        if row[0] == email and row[1] == password:
            return True
    return False

@app.route("/register", methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        #Parse form data    
        password = request.form['password']
        email = request.form['email']
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        address1 = request.form['address1']
        address2 = request.form['address2']
        zipcode = request.form['zipcode']
        city = request.form['city']
        state = request.form['state']
        country = request.form['country']
        phone = request.form['phone']

        with connection.cursor() as con:
            try:
                cur = con.cursor()
                cur.execute('INSERT INTO users (password, email, firstName, lastName, address1, address2, zipcode, city, state, country, phone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (password, email, firstName, lastName, address1, address2, zipcode, city, state, country, phone))

                connection.commit()

                msg = "Registered Successfully"
            except:
                connection.rollback()
                msg = "Error occured"
        con.close()
        return render_template("login.html", error=msg)

@app.route("/registerationForm")
def registrationForm():
    return render_template("register.html")

def allowed_file(filename):
    return '.' in filename and \
            filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def parse(data):
    ans = []
    i = 0
    while i < len(data):
        curr = []
        for j in range(4):
            if i >= len(data):
                break
            curr.append(data[i])
            i += 1
        ans.append(curr)
    return ans

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
