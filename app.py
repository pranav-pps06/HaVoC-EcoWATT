from flask import Flask,render_template,request,redirect,url_for    

app=Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route("/login", methods=['GET'])
def login():
    return render_template('login.html')

@app.route("/newuser", methods=['GET'])
def newuser():
    return render_template('newuser.html')

@app.route("/terms", methods=['GET'])
def terms():
    return render_template('terms.html')

@app.route("/forgotpassword", methods=['GET'])
def forgotpassword():
    return render_template('forgotpassword.html')

app.run(host='0.0.0.0', port=5000)