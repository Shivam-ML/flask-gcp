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
       # print(itemData,"-------------------->",type(itemData))
        logging.debug("itemData print")
       # print(categoryData,type(categoryData))
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
    
    
    
 #Display search results
@app.route("/query", methods=["GET", "POST"])
def query():
    #loggedIn, firstName, noOfItems = getLoginDetails()
    if request.method == "POST" or request.method == "GET":	
        print(request,"---------------------->request")
        search_q=request.args.get("search_q")
        print("search query is ",search_q)
        with connection.cursor() as conn:
            cur = conn
            search_query="SELECT * FROM products where name like \"%{}%\"".format(search_q)
            print(search_query)
            cur.execute(search_query)
            itemData = cur.fetchall()
            print("Search results from DB-------------->",itemData)
            cur.execute('SELECT categoryId, name FROM categories')
            categoryData = cur.fetchall()
        itemData = parse(itemData)
        future = publisher.publish(topic_name, b'1 user is accessing application', datakey='application accessed')
        future.result()
        print("connection completed")
        logging.info("MYSQL connection created")
        #return({"data":(itemData,loggedIn, firstName,noOfItems,categoryData)})
        result={"itemData":itemData,"categoryData":categoryData}
        return(result)
        #return render_template('home_search.html',itemData=itemData,loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems,categoryData=categoryData)
    
    



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
    app.run(host='0.0.0.0', port=8087, debug=True)
