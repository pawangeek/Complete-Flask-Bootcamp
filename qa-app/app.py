from flask import Flask, render_template, g, request, session, redirect, url_for
from database import get_db
import os

# Module for generating and checking hash of passwords
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)  # create 24 length random key

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
    db = get_db()

    ques_cur = db.execute('''select questions.id as question_id, questions.question_text, 
                            askers.name as asker_name, experts.name as expert_name from questions 
                            join users as askers on askers.id = questions.asked_by_id join users as experts 
                            on experts.id = questions.expert_id where questions.answer_text is not null''')
    ques = ques_cur.fetchall()

    return render_template('home.html', user=user, ques=ques)


@app.route('/answer/<question_id>', methods=['GET', 'POST'])
def answer(question_id):
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))

    if user['expert'] == 0:
        return redirect(url_for('index'))

    db = get_db()

    if request.method == 'POST':
        db.execute('update questions set answer_text = ? where id = ?', [request.form['answer'], question_id])
        db.commit()

        return redirect(url_for('unanswered'))

    question_cur = db.execute('select id, question_text from questions where id = ?', [question_id])
    question = question_cur.fetchone()

    return render_template('answer.html', user=user, question=question)


@app.route('/ask', methods=['GET', 'POST'])
def ask():
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))

    db = get_db()

    if request.method == 'POST':
        db.execute('insert into questions (question_text, asked_by_id, expert_id) values (?,?,?)', [request.form['question'], user['id'], request.form['expert']])
        db.commit()

        return redirect(url_for('index'))

    # It will get all experts from our database
    expert_cur = db.execute('select id, name from users where expert= 1')
    expert_results = expert_cur.fetchall()

    return render_template('ask.html', user=user,  experts=expert_results)


@app.route('/login', methods=['GET', 'POST'])
def login():
    user = get_current_user()
    error = None
    if request.method == 'POST':
        db = get_db()

        name = request.form['name']
        password = request.form['password']

        # check row where the name matches with the current one
        user_cur = db.execute('select id, name, password from users where name = ?', [name])
        # just fetch one row with query
        user_result = user_cur.fetchone()

        if user_result:
            # Use to check our stored password with the new one
            if check_password_hash(user_result['password'], password):

                # To create a session for user
                session['user'] = user_result['name']
                return redirect(url_for('index'))
            else:
                error = 'Password is incorrect'

        else:
            error = 'Username is incorrect'

    return render_template('login.html', user=user, error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    user = get_current_user()
    if request.method == "POST":
        db = get_db()

        existing_cur = db.execute('select id from users where name = ?', [request.form['name']])
        existing = existing_cur.fetchone()

        if existing:
            return render_template('register.html', user=user, error='User already Exist')
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

    if not user:
        return redirect(url_for('login'))

    if user['expert'] == 0:
        return redirect(url_for('index'))

    db = get_db()

    question_cur = db.execute('''select questions.id, questions.question_text, users.name from questions 
                            join users on users.id = questions.asked_by_id where answer_text is null and 
                            expert_id=?''', [user['id']])

    questions = question_cur.fetchall()

    return render_template('unanswered.html', user=user, questions=questions)


@app.route('/users')
def users():
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))

    if user['admin'] == 0:
        return redirect(url_for('index'))

    db = get_db()
    user_cur = db.execute('select id, name, expert, admin from users')

    # Fetch all will fetch all the data present in the database
    user_results = user_cur.fetchall()

    return render_template('users.html', user=user, users=user_results)


@app.route('/question/<question_id>')
def question(question_id):
    user = get_current_user()
    db = get_db()

    question_cur = db.execute('''select questions.question_text, questions.answer_text, 
                            askers.name as asker_name, experts.name as expert_name from questions join users 
                            as askers on askers.id = questions.asked_by_id join users as experts on 
                            experts.id = questions.expert_id where questions.id = ?''', [question_id])

    question = question_cur.fetchone()

    return render_template('question.html', user=user, question=question)


@app.route('/promote/<user_id>')
def promote(user_id):
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))

    if user['admin'] == 0:
        return redirect(url_for('index'))

    db = get_db()

    # update those users and promote them to admin
    db.execute('update users set expert=1 where id=?', [user_id])
    db.commit()

    # Return url again for users
    return redirect(url_for('users'))


@app.route('/demote/<user_id>')
def demote(user_id):
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))

    if user['admin'] == 0:
        return redirect(url_for('index'))

    db = get_db()

    # update those users and promote them to admin
    db.execute('update users set expert=0 where id=?', [user_id])
    db.commit()

    # Return url again for users
    return redirect(url_for('users'))


@app.route('/logout')
def logout():

    # popout user from session and replace with none
    session.pop('user', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True)
