
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from datetime import datetime, timedelta
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from logic import rd,loan,lumpsum,update_month,update_worth,fd
import os
from dotenv import load_dotenv
load_dotenv()


worth =0

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
client = MongoClient(os.getenv('MONGODB_URI'))


#client database

db = client.login
users_collection = db.users

#bank data mongodb datasets
db_codecash = client.bank
bank_collection = db_codecash['assets']




def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
#---------------------------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users_collection.find_one({'email': email})

        if user and user['password'] == password:
            session['user'] = user['user_name']    #this was the main game----------->
            return redirect(url_for('index'))
        else:
            print('Invalid email or password')
    
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        user_name = request.form['user_name']
        email = request.form['email']
        password = request.form['password']
        signup_time = datetime.now()

        # Check if email already exists
        existing_email = users_collection.find_one({'email': email})
        if existing_email:
            print('Email already exists')
            return redirect(url_for('signup'))

        # Check if username already exists
        existing_username = users_collection.find_one({'user_name': user_name})
        if existing_username:
            print('Username already exists')
            return redirect(url_for('signup'))

        # If email and username are unique, insert new user
        users_collection.insert_one({
            'user_name': user_name,
            'email': email,
            'password': password,
            'signup_time': signup_time,
            'worth':worth
        })
        session['user'] = user_name
        return redirect(url_for('index'))
    
    return render_template('signup.html')
#---------------------------------------------------------------------------------------


@app.route('/')
@login_required
def index():

    
    username = session.get('user')
    user = users_collection.find_one({'user_name': username})
    current_date = user.get('current_date', datetime.now())
    month_year = current_date.strftime("%B-%Y")
    
    worth = user.get('worth', 0)  

    asset_document = bank_collection.find_one({'_id': 'bank_assets'})
    bank_money = asset_document.get('total_assets') if asset_document else 0
    

    print(current_date)
    print( month_year)
    return render_template('index.html', month_year=month_year,username=username, worth=worth,bank=bank_money)


@app.route('/home')
# @login_required
def home():
    username = session.get('user')
    user = users_collection.find_one({'user_name': username})
    current_date = user.get('current_date', datetime.now())
    month_year = current_date.strftime("%B-%Y")
    worth = user.get('worth', 0)  
    print(month_year)
    asset_document = bank_collection.find_one({'_id': 'bank_assets'})
    bank_money = asset_document.get('total_assets') 
    return render_template('index.html', month_year=month_year,username=username, worth=worth,bank=bank_money)


@app.route('/next_month', methods=['POST'])
@login_required
def next_month():
    username = session.get('user')
    if username:
        update_month.next_month(username)
    return redirect(url_for('index'))


# @app.route('/stock',methods = ['GET','POST'])
# @login_required
# def stock():
#     username = session.get('user')
    
#     if request.method == 'POST':
#         user = users_collection.find_one({'username': username})
#         if user:
#             amount = request

@app.route('/bank', methods=['GET', 'POST'])
@login_required
def bank():
    username = session.get('user')
    user = users_collection.find_one({'user_name': username})
    
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount', 0))
            time_period = int(request.form.get('time-period', 0))
            action_type = request.form.get('action-type')

            if amount <= 0:
                flash('Amount must be greater than 0')
                return redirect(url_for('bank'))

            current_worth = user.get('worth', 0)
            current_fd = user.get('fd', 0)
            current_loan = user.get('loan', 0)

            # Handle different bank actions
            if action_type == 'deposit':
                if amount > current_worth:
                    flash('Insufficient funds')
                else:
                    # Update user's worth and bank assets
                    new_worth = current_worth - amount
                    users_collection.update_one(
                        {'user_name': username},
                        {'$set': {'worth': new_worth}}
                    )
                    bank_collection.update_one(
                        {'_id': 'bank_assets'},
                        {'$inc': {'total_assets': amount}}
                    )
                    flash('Deposit successful')

            elif action_type == 'withdraw':
                bank_assets = bank_collection.find_one({'_id': 'bank_assets'})
                if amount > bank_assets.get('total_assets', 0):
                    flash('Bank has insufficient funds')
                else:
                    # Update user's worth and bank assets
                    new_worth = current_worth + amount
                    users_collection.update_one(
                        {'user_name': username},
                        {'$set': {'worth': new_worth}}
                    )
                    bank_collection.update_one(
                        {'_id': 'bank_assets'},
                        {'$inc': {'total_assets': -amount}}
                    )
                    flash('Withdrawal successful')

            elif action_type == 'fd':
                if amount > current_worth:
                    flash('Insufficient funds for FD')
                else:
                    # Calculate FD interest (example: 6% per year)
                    interest_rate = 0.06
                    maturity_amount = amount * (1 + interest_rate * time_period/12)
                    
                    # Update user's worth, FD amount, and bank assets
                    new_worth = current_worth - amount
                    new_fd = current_fd + maturity_amount
                    
                    users_collection.update_one(
                        {'user_name': username},
                        {
                            '$set': {
                                'worth': new_worth,
                                'fd': new_fd,
                                'fd_maturity_date': datetime.now() + timedelta(days=time_period*30)
                            }
                        }
                    )
                    bank_collection.update_one(
                        {'_id': 'bank_assets'},
                        {'$inc': {'total_assets': amount}}
                    )
                    flash(f'FD created successfully. Maturity amount: {maturity_amount:.2f}')

            elif action_type == 'loan':
                # Calculate maximum loan amount (example: 2x of current worth)
                max_loan = current_worth * 2
                if amount > max_loan:
                    flash(f'Loan amount exceeds maximum limit of {max_loan}')
                elif current_loan > 0:
                    flash('You already have an existing loan')
                else:
                    # Calculate loan interest (example: 12% per year)
                    interest_rate = 0.12
                    repayment_amount = amount * (1 + interest_rate * time_period/12)
                    
                    # Update user's worth, loan amount, and bank assets
                    new_worth = current_worth + amount
                    users_collection.update_one(
                        {'user_name': username},
                        {
                            '$set': {
                                'worth': new_worth,
                                'loan': repayment_amount,
                                'loan_due_date': datetime.now() + timedelta(days=time_period*30)
                            }
                        }
                    )
                    bank_collection.update_one(
                        {'_id': 'bank_assets'},
                        {'$inc': {'total_assets': -amount}}
                    )
                    flash(f'Loan approved. Repayment amount: {repayment_amount:.2f}')

            elif action_type == 'repay_loan':
                if amount > current_worth:
                    flash('Insufficient funds to repay loan')
                elif amount > current_loan:
                    flash('Repayment amount exceeds loan amount')
                else:
                    # Update user's worth, loan amount, and bank assets
                    new_worth = current_worth - amount
                    new_loan = current_loan - amount
                    users_collection.update_one(
                        {'user_name': username},
                        {
                            '$set': {
                                'worth': new_worth,
                                'loan': new_loan
                            }
                        }
                    )
                    bank_collection.update_one(
                        {'_id': 'bank_assets'},
                        {'$inc': {'total_assets': amount}}
                    )
                    flash('Loan repayment successful')

        except ValueError:
            flash('Invalid amount or time period')
            return redirect(url_for('bank'))

    # Get updated user data
    user = users_collection.find_one({'user_name': username})
    current_date = user.get('current_date', datetime.now())
    month_year = current_date.strftime("%B-%Y")
    worth = user.get('worth', 0)
    fd = user.get('fd',0)
    loan =user.get('loan',0)
    asset_document = bank_collection.find_one({'_id': 'bank_assets'})
    bank_money = asset_document.get('total_assets') if asset_document else 0 
    return render_template('bank.html', 
                         month_year=month_year,
                         username=username,
                         worth=worth,
                         fd=fd,
                         loan=loan,
                         bank=bank_money)

@app.route('/leaderboard')
@login_required
def leaderboard():
    users = users_collection.find()
    username = session.get('user')
    user = users_collection.find_one({'user_name': username})
    current_date = user.get('current_date', datetime.now())
    month_year = current_date.strftime("%B-%Y")
    worth = user.get('worth', 0)  
    asset_document = bank_collection.find_one({'_id': 'bank_assets'})
    bank_money = asset_document.get('total_assets') 
    return render_template('leaderboard.html', users=users,user=user,username=username,month_year=month_year,worth=worth,bank=bank_money)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    username = session.get('user')
    user = users_collection.find_one({'user_name': username})

    if not user:
        flash('User not found.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_info':
            new_email = request.form.get('email')
            current_password = request.form.get('current_password')
            new_password = request.form.get('password')

            if not check_password_hash(user['password'], current_password):
                last_changed_date = user.get('password_last_changed', None)
                if last_changed_date:
                    flash(f'Incorrect password. Your password was last changed on {last_changed_date.strftime("%B %d, %Y")}.')
                else:
                    flash('Incorrect password.')
                return redirect(url_for('settings'))

            if check_password_hash(user['password'], new_password):
                flash('New password cannot be the same as the current password.')
                return redirect(url_for('settings'))

            updates = {}
            if new_email and new_email != user['email']:
                if users_collection.find_one({'email': new_email}):
                    flash('Email already exists.')
                else:
                    updates['email'] = new_email

            if new_password:
                updates['password'] = generate_password_hash(new_password)
                updates['password_last_changed'] = datetime.now()

            if updates:
                users_collection.update_one({'user_name': username}, {'$set': updates})
                flash('Information updated successfully.')

        elif action == 'delete_account':
            password = request.form.get('password')

            if check_password_hash(user['password'], password):
                users_collection.delete_one({'user_name': username})
                session.clear()
                flash('Account deleted successfully.')
                return redirect(url_for('login'))
            else:
                last_changed_date = user.get('password_last_changed', None)
                if last_changed_date:
                    flash(f'Incorrect password. Your password was last changed on {last_changed_date.strftime("%B %d, %Y")}.')
                else:
                    flash('Incorrect password.')
                return redirect(url_for('settings'))

        elif action == 'logout':
            session.clear()
            flash('Logged out successfully.')
            return redirect(url_for('login'))

    return render_template('settings.html', user=user)

if __name__ == '__main__':
    app.run()
