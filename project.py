#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect, flash
import pymysql.cursors
import os
#Authenticates the register
import bcrypt
#for uploading photo:
from app import app
#from flask import Flask, flash, request, redirect, render_template
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


###Initialize the app from Flask
##app = Flask(__name__)
##app.secret_key = "secret key"

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       port = 8889,
                       user='root',
                       password='root',
                       db='WelcomeHome',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)


def allowed_image(filename):

    if not "." in filename:
        return False

    ext = filename.rsplit(".", 1)[1]

    if ext.upper() in app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        return True
    else:
        return False


def allowed_image_filesize(filesize):

    if int(filesize) <= app.config["MAX_IMAGE_FILESIZE"]:
        return True
    else:
        return False


#Define a route to hello function
@app.route('/')
def hello():
    return render_template('index.html')

#Define route for login
@app.route('/login')
def login():
    return render_template('login.html')

#Define route for register
@app.route('/register')
def register():
    cursor = conn.cursor()
    cursor.execute('SELECT roleID, rDescription FROM Role')
    roles = cursor.fetchall()
    cursor.close()
    return render_template('register.html', roles=roles)

#Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    if request.method == 'POST':
        # Grabs information from the forms
        username = request.form['username']
        password = request.form['password']

        # Cursor used to send queries
        cursor = conn.cursor()

        # Executes query to fetch the stored password for the given username
        query = 'SELECT password FROM Person WHERE userName = %s'
        cursor.execute(query, (username,))
        stored_data = cursor.fetchone()
        cursor.close()

        error = None
        if stored_data:
            # Directly access the stored password from the fetched data
            stored_password = stored_data['password']

            # Verify the password using bcrypt
            if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                # Store only the username in session
                session['username'] = username

                return redirect(url_for('home'))  # Redirect to the home page
            else:
                error = 'Invalid password'
        else:
            error = 'Invalid username or user does not exist'

        # Return to login page with error
        return render_template('login.html', error=error)
    else:
        return render_template('login.html')



@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    if request.method == 'POST':
        # Grab information from the form
        username = request.form['username']
        password = request.form['password']
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
        role = request.form['role']

        # Hash the password with a salt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        cursor = conn.cursor()
        
        # Check if the username already exists
        query = 'SELECT * FROM Person WHERE userName = %s'
        cursor.execute(query, (username,))
        data = cursor.fetchone()

        error = None
        if data:
            error = "This user already exists"
            return render_template('register.html', error=error)
        else:
            try:
                # Insert into Person table
                insert_person = """
                INSERT INTO Person (userName, password, fname, lname, email)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(insert_person, (username, hashed_password, fname, lname, email))
                
                # Insert role into Act table
                insert_act = """
                INSERT INTO Act (userName, roleID)
                VALUES (%s, %s)
                """
                cursor.execute(insert_act, (username, role))
                
                conn.commit()
                return render_template('index.html')
            except Exception as e:
                conn.rollback()
                error = f"An error occurred: {str(e)}"
                return render_template('register.html', error=error)
            finally:
                cursor.close()
    else:
        return redirect('/register')



@app.route('/home')
def home():
    user = session['username']
    session.pop('orderID', None)
    session.pop('mainCategory', None)
    session.pop('subCategory', None)
    session.pop('client', None)
    return render_template('home.html', username=user)

@app.route('/findsingleItem', methods=["GET", "POST"])
def findsingleItem():
    user = session['username']
    ItemID = request.args['ItemID']
    cursor = conn.cursor();
    query = 'SELECT Item.mainCategory, Item.subCategory, Item.iDescription AS itemDescription, Piece.pieceNum, Piece.roomNum, Piece.shelfNum, Piece.pNotes, Piece.pDescription AS pieceDescription, Piece.length, Piece.width, Piece.height FROM Piece NATURAL JOIN Item WHERE Piece.ItemID = %s;'
    cursor.execute(query, ItemID)
    data = cursor.fetchall()
    cursor.close()
    if data:
        return render_template('findsingleItem.html', itemID=ItemID, locations=data)
    else:
        error = f"Item '{ItemID}' does not exist."
        return render_template('home.html', username=user, error2=error)
        


@app.route('/findorderItem', methods=["GET", "POST"])
def findorderItem():
    user = session['username']
    orderID = request.args['orderID']
    cursor = conn.cursor();
    query = 'SELECT Item.ItemID, Item.mainCategory, Item.subCategory, Item.iDescription AS itemDescription, Piece.pieceNum, Piece.pDescription AS pieceDescription, Piece.length, Piece.width, Piece.height, Piece.roomNum, Piece.shelfNum, Piece.pNotes FROM Piece NATURAL JOIN Item NATURAL JOIN ItemIn WHERE ItemIn.orderID = %s ORDER BY ItemID,pieceNum;'
    cursor.execute(query, orderID)
    data = cursor.fetchall()
    cursor.close()
    if not data:
        error = f"Order '{orderID}' does not exist."
        return render_template('home.html', username=user, error3=error)
    return render_template('findorderItem.html', OrderID=orderID, location=data)



@app.route('/acceptDonation', methods=['GET', 'POST'])
def acceptDonation():
    user = session['username']
    cursor = conn.cursor();
    query = 'SELECT userName FROM `Act` WHERE userName = %s AND roleID=2'
    cursor.execute(query, (user))
    user1 = cursor.fetchone()
    cursor.close()
    error = None
    if(user1):
        donor = request.args['DonorID']
    else:
        #returns an error message to the html page
        error = 'Only Staff Member could accept a donation'
        return render_template('home.html', username=user, error=error)  


    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT userName FROM `Act` WHERE userName = %s AND roleID=1'
    cursor.execute(query, (donor))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    cursor.close()
    error = None
    if(data):
        #creates a session for the the user
        #session is a built in
        return render_template('acceptDonation.html', Donor=donor) 
    else:
        #returns an error message to the html page
        error = 'This person is not registered as a donor!'
        return render_template('home.html', username=user, error=error)       

@app.route('/enterItem', methods=['GET', 'POST'])
def enterItem():
    if request.method == 'POST':
        donor_id = request.form['donor_id']
        if not donor_id:
            return redirect(url_for('acceptDonation'))
        mainCategory = request.form['mainCategory']
        subCategory = request.form['subCategory']
        iDescription = request.form['iDescription']
        photo = request.form['photo']
        color = request.form['color']
        isNew = request.form['isNew']
        hasPieces = request.form['hasPieces']
        material = request.form['material']
        cursor = conn.cursor()
        
        try:
            query = 'SELECT * FROM Category WHERE mainCategory = %s AND subCategory = %s'
            cursor.execute(query, (mainCategory, subCategory))
            data = cursor.fetchone()

            if not data:
                insert_cat = """
                INSERT INTO Category (mainCategory, subCategory)
                VALUES (%s, %s)
                """
                cursor.execute(insert_cat, (mainCategory, subCategory))
                conn.commit()

            insert_item = """
            INSERT INTO Item (iDescription, photo, color, isNew, hasPieces, material, mainCategory, subCategory)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_item, (iDescription, photo, color, isNew, hasPieces, material, mainCategory, subCategory))
            conn.commit()
            itemID = cursor.lastrowid

            insert_donated_by_query = """
            INSERT INTO DonatedBy (ItemID, userName, donateDate)
            VALUES (%s, %s, CURDATE())
            """
            cursor.execute(insert_donated_by_query, (itemID, donor_id))
            conn.commit()

            success_message = "Item successfully donated!"
            return render_template('acceptDonation.html', Donor=donor_id, itemID=itemID, success=success_message)

        except Exception as e:
            conn.rollback()
            error_message = f"Failed to donate the item. Error: {str(e)}"
            return render_template('acceptDonation.html', Donor=donor_id, error=error_message)

        finally:
            cursor.close()
            
@app.route('/enterPiece', methods=['GET', 'POST'])
def enterPiece():
    if request.method == 'POST':
        itemID = request.form['itemID']
        pieceNum = request.form['pieceNum']
        pDescription = request.form['pDescription']
        length = request.form['length']
        width = request.form['width']
        height = request.form['height']
        roomNum = request.form['roomNum']
        shelfNum = request.form['shelfNum']
        pNotes = request.form['pNotes']

        # Check if required fields are filled
        if not itemID or not pieceNum or not roomNum or not shelfNum:
            error_message1 = "Please fill in all the required fields."
            return render_template('acceptDonation.html', error1=error_message1)

        cursor = conn.cursor()

        try:
            query_location = 'SELECT * FROM Location WHERE roomNum = %s AND shelfNum = %s'
            cursor.execute(query_location, (roomNum, shelfNum))
            location_data = cursor.fetchone()

            if not location_data:
                # Insert into Location table if the combination doesn't exist
                insert_location = """
                INSERT INTO Location (roomNum, shelfNum)
                VALUES (%s, %s)
                """
                cursor.execute(insert_location, (roomNum, shelfNum))
                conn.commit()

            # Insert piece into the Piece table
            insert_piece = """
            INSERT INTO Piece (ItemID, pieceNum, pDescription, length, width, height, roomNum, shelfNum, pNotes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_piece, (itemID, pieceNum, pDescription, length, width, height, roomNum, shelfNum, pNotes))
            conn.commit()

            # Success message
            success_message1 = "Piece successfully entered!"
            return render_template('acceptDonation.html', itemID=itemID, success1=success_message1)

        except Exception as e:
            # Rollback in case of error and capture the error message
            conn.rollback()
            error_message1 = f"Failed to enter the piece. Error: {str(e)}"
            return render_template('acceptDonation.html', error1=error_message1)

        finally:
            cursor.close()

    # Render the form for the GET request
    itemID = request.args.get('itemID')
    return render_template('acceptDonation.html', itemID=itemID)

@app.route('/startOrder', methods=['GET'])
def start_order():
    cursor = conn.cursor()
    try:
        user = session.get('username')
        session.pop('mainCategory', None)
        session.pop('subCategory', None)

        # Check if the logged-in user is staff (roleID = 2)
        query = 'SELECT userName FROM `Act` WHERE userName = %s AND roleID = 2'
        cursor.execute(query, (user,))
        user1 = cursor.fetchone()
        cursor.close()

        if not user1:
            error = 'Only Staff Member could start an order.'
            return render_template('home.html', username=user, error1=error)

        client = request.args.get('client')
        orderNotes = request.args.get('orderNotes')
        
        if client:
            session['client'] = client
        cursor = conn.cursor()
        query = "SELECT username FROM Act WHERE username = %s AND roleID = 4"
        cursor.execute(query, (client,))
        client_result = cursor.fetchone()
        if not client_result:
            error = f"Client '{client}' does not exist."
            return render_template('home.html', username=user, error1=error)

        # Insert the new order;
        orderID = session.get('orderID')  
        if not orderID:
            query = """
            INSERT INTO Ordered (orderDate, orderNotes, supervisor, client)
            VALUES (CURRENT_DATE, %s, %s, %s)
        """
            cursor.execute(query, (orderNotes, user, client))
            conn.commit()
        # Fetch the newly generated orderID (auto-incremented)
            orderID = cursor.lastrowid
            session['orderID'] = orderID

        # Fetch main categories for dropdown
        cursor.execute('SELECT DISTINCT mainCategory FROM Item')
        main_categories = [row['mainCategory'] for row in cursor.fetchall()] 

  
        return render_template('startOrder.html', orderID=orderID, main_categories=main_categories, client = client)

    except Exception as e:
        return f"An error occurred: {e}", 500

    finally:
        cursor.close()

@app.route('/getSubCategories', methods=['GET'])
def get_subcategories():
    main_category = request.args.get('mainCategory')
    cursor = conn.cursor()
    try:
        query = "SELECT DISTINCT subCategory FROM Item WHERE mainCategory = %s"
        cursor.execute(query, (main_category,))
        sub_categories = [row['subCategory'] for row in cursor.fetchall()]

        # Generate HTML options for the subcategory drop-down
        options = '<option value="">Select Sub-category</option>'
        for sub_category in sub_categories:
            options += f'<option value="{sub_category}">{sub_category}</option>'

        return options
    except Exception as e:
        return f"Error fetching subcategories: {e}", 500
    finally:
        cursor.close()

@app.route('/shopping', methods=['GET', 'POST'])
def shopping():
    cursor = conn.cursor()
    try:
        # Retrieve orderID from session
        orderID = session.get('orderID')  
        if not orderID:
            return redirect('/home')  # Redirect to home if no orderID is found

        main_category = session.get('mainCategory')
        sub_category = session.get('subCategory')

        if not main_category or not sub_category:
            main_category = request.args.get('mainCategory')
            sub_category = request.args.get('subCategory')
            if main_category and sub_category:
                # Save them in session for future requests
                session['mainCategory'] = main_category
                session['subCategory'] = sub_category
        client = session.get('client')  
        if not client:
            return redirect('/home')  

        query = """
            SELECT ItemID, iDescription 
            FROM Item 
            WHERE mainCategory = %s AND subCategory = %s 
            AND ItemID NOT IN (SELECT ItemID FROM ItemIn)
        """
        cursor.execute(query, (main_category, sub_category))
        items = cursor.fetchall()

        error_message = None

        if request.method == 'POST':
            selected_items = request.form.getlist('items')
            if not selected_items:
                error_message = "No item selected. Please select at least one item."  
            else:
                for itemID in selected_items:
                    query = """
                        INSERT INTO ItemIn (orderID, ItemID)
                        VALUES (%s, %s)
                    """
                    cursor.execute(query, (orderID, itemID))
                conn.commit()
                return redirect(f'/shopping?mainCategory={main_category}&subCategory={sub_category}')

        # Pass the list of available items to the template along with the error message
        return render_template('shopping.html', orderID=orderID, items=items, client=client, 
                               error_message=error_message, main_category=main_category, sub_category=sub_category)

    except Exception as e:
        return f"An error occurred: {e}", 500

    finally:
        cursor.close()



def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
	
@app.route('/')
def upload_form():
	return render_template('upload.html')

@app.route('/', methods=['POST'])
def upload_file():
	if request.method == 'POST':
        # check if the post request has the file part
		if 'file' not in request.files:
			flash('No file part')
			return redirect(request.url)
		file = request.files['file']
		if file.filename == '':
			flash('No file selected for uploading')
			return redirect(request.url)
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			flash('File successfully uploaded')
			return redirect('/')
		else:
			flash('Allowed file types are txt, pdf, png, jpg, jpeg, gif')
			return redirect(request.url)


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('orderID', None)
    session.pop('mainCategory', None)
    session.pop('subCategory', None)
    session.pop('client', None)
    return redirect('/')
        
app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug = True)
