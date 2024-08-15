from flask import Flask, request, render_template, redirect, url_for, session
from firebase_admin import credentials, firestore, auth, storage
import firebase_admin
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os 
import secrets


load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Set a secret key for session management

# Initialize Firebase Admin SDK
cred = credentials.Certificate("islam-24-335fb-firebase-adminsdk-ukvhw-73f41ea577.json")
firebase_admin.initialize_app(cred, {'storageBucket': 'islam-24-335fb.appspot.com'})

# Get Firestore and Storage clients
db = firestore.client()
bucket = storage.bucket()

users_ref = db.collection("user")

# Dictionary to store verification codes temporarily
verification_codes = {}

def send_verification_email(email, code):
    """Sends a verification email with the provided code."""
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_APP_CODE")

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = email
    msg['Subject'] = 'Your Verification Code'
    
    body = f"Your verification code is {code}. It expires in 10 minutes."
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print(f"Verification email sent to {email}.")
    except Exception as e:
        print(f"Error sending email: {e}")

def get_doc_ids_by_email(email):
    """Fetches document IDs from Firestore by email."""
    query = users_ref.where("email", "==", email)
    docs = query.get()
    doc_ids = [doc.id for doc in docs]
    print(f"User_id: {doc_ids}")
    return doc_ids

def delete_user_data(doc_id):
    """Deletes Firestore document, Firebase Authentication user, and related storage files by document ID."""
    try:
        # Delete the Firestore document
        users_ref.document(doc_id).delete()

        # Delete the Firebase Authentication user
        auth.delete_user(doc_id)


        # Delete user files from Firebase Storage
        user_folder = f"image/{doc_id}/"
        blobs = bucket.list_blobs(prefix=user_folder)
        for blob in blobs:
            blob.delete()

    except Exception as e:
        print(f"Error occurred: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'email' in session and 'verification_code' in session:
        if request.method == 'POST':
            code = request.form.get('verification_code')
            print(f"Session Email: {session.get('email')}, Session Code: {session.get('verification_code')}")
            
            if code == session.get('verification_code'):
                email = session.get('email')
                doc_ids = get_doc_ids_by_email(email)
                if not doc_ids:
                    return render_template('index.html', message=f"No document found with the email: {email}")
                for doc_id in doc_ids:
                    delete_user_data(doc_id)
                return render_template('index.html', message="User data deleted successfully.")
            else:
                return render_template('index.html', message="Invalid verification code.")
    
    return render_template('index.html')

@app.route('/request_verification', methods=['POST'])
def request_verification():
    print("Form data:", request.form)
    email = request.form.get('email', None)
    
    if not email:  # Ensure email is not None or empty
        return render_template('index.html', message="Please enter an email address.")

    # Retrieve document IDs associated with the email
    doc_ids = get_doc_ids_by_email(email)

    if not doc_ids:
        return render_template('index.html', message=f"No document found with the email: {email}")

    # Generate and store verification code
    code = str(random.randint(100000, 999999))
    verification_codes[email] = {
        'code': code,
        'expires_at': datetime.now() + timedelta(minutes=10)
    }

    # Send verification email
    send_verification_email(email, code)
    
    # Store email and verification code in the session
    session['email'] = email
    session['verification_code'] = code

    print("Session email stored:", session['email'])
    print("Session verification_code stored:", session['verification_code'])

    return render_template('index.html', message="Verification code sent to your email.")



if __name__ == '__main__':
    app.run(debug=True)
