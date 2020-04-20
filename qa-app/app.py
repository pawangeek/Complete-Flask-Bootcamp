from flask import Flask, render_template, g, request, session, redirect, url_for
from database import get_db
import os

# Module for generating and checking hash of passwords
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY']=os.urandom(24)

# Decorator and function to teardown the database every time a requests ends
# It's going to check if there is an active database if there is we'll close it that way
# you don't have any memory leaks after the root finishes and the response returns to the user.

# The application context keeps track of the application-level data during a request,
# More at https://flask.palletsprojects.com/en/1.1.x/appcontext/


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite.db'):
        g.sqlite_db.close()


def get_current_user():

    # If user not in session than none
    user_result = None

    # If user in session then pass user from user session
    if 'user' in session:
        user = session['user']

        db = get_db()
        user_cur = db.execute('select id, name, password, admin, expert from users where name = ?', [user])
        user_result = user_cur.fetchone()

    return user_result


@app.route('/')
def index():
    user = get_current_user()
    return render_template('home.html', user=user)


@app.route('/answer')
def answer():
    user = get_current_user()

    return render_template('answer.html',user=user)


@app.route('/ask', methods=['GET','POST'])
def ask():
    user = get_current_user()
    db = get_db()

    if request.method == 'POST':
        db.execute('insert into questions (question_text, asked_by_id, expert_id) values (?,?,?)', [request.form['question'], user['id'], request.form['expert']])
        db.commit()

        return redirect(url_for('index'))

    # It will get all experts from our database
    expert_cur = db.execute('select id, name from users where expert= 1')
    expert_results = expert_cur.fetchall()

    return render_template('ask.html', user=user,  experts = expert_results)


@app.route('/login', methods=['GET', 'POST'])
def login():
    user = get_current_user()
    if request.method == 'POST':
        db = get_db()

        name = request.form['name']
        password = request.form['password']

        # check row where the name matches with the current one
        user_cur = db.execute('select id, name, password from users where name = ?', [name])
        # just fetch one row with query
        user_result = user_cur.fetchone()

        # Use to check our stored password with the new one
        if check_password_hash(user_result['password'],password):

            # To create a session for user
            session['user']=user_result['name']
            return redirect(url_for('index'))
        else:
            return redirect((url_for('login')))

    return render_template('login.html', user=user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    user = get_current_user()
    if request.method == "POST":
        db = get_db()

        # It generate hashed password for 'password' by cryptographic sha256
        hashed = generate_password_hash(request.form['password'], method='sha256')

        # Taking 0 for admin and 0 for expert is that it's user (by default)
        # Id is autoincrement hence no need to pass
        db.execute('insert into users (name, password, expert, admin) values (?,?,?,?)', [request.form['name'], hashed, '0', '0'])
        db.commit()

        session['user'] = request.form['name']

        return redirect(url_for('index'))

    return render_template('register.html', user=user)


@app.route('/unanswered')
def unanswered():
    user = get_current_user()
    db = get_db()

    question_cur = db.execute('select question_text, asked_by_id from questions where answer_text is null and expert_id=?',[user['id']])
    questions = question_cur.fetchall()

    return render_template('unanswered.html', user=user,questions=questions)


@app.route('/users')
def users():
    user = get_current_user()

    db = get_db()
    user_cur = db.execute('select id, name, expert, admin from users')

    # Fetch all will fetch all the data present in the database
    user_results = user_cur.fetchall()

    return render_template('users.html', user=user, users=user_results)


@app.route('/question')
def question():
    user = get_current_user()
    return render_template('question.html', user=user)


@app.route('/promote/<user_id>')
def promote(user_id):
    db = get_db()

    # update those users and promote them to admin
    db.execute('update users set expert=1 where id=?',[user_id])
    db.commit()

    # Return url again for users
    return redirect(url_for('users'))


@app.route('/demote/<user_id>')
def demote(user_id):
    db = get_db()

    # update those users and promote them to admin
    db.execute('update users set expert=0 where id=?', [user_id])
    db.commit()

    # Return url again for users
    return redirect(url_for('users'))


@app.route('/logout')
def logout():

    # popout user from session and replace with none
    session.pop('user',None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True)
