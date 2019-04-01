from flask import Flask,render_template,url_for,request
import nltk 
from functools import wraps
import pandas as pd
from rake_nltk import Rake
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer
import pickle
from sklearn.externals import joblib
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL,MySQLdb
import bcrypt




app = Flask(__name__)


app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'flaskdb'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

@app.route('/')
def main():
    return render_template("main.html")

@app.route('/home')
def home():
    return render_template("home.html")    

@app.route('/login',methods=["GET","POST"])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password'].encode('utf-8')

        curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        curl.execute("SELECT * FROM users WHERE email=%s",(email,))
        user = curl.fetchone()
        curl.close()

        if user is not None:
            if bcrypt.hashpw(password, user["password"].encode('utf-8')) == user["password"].encode('utf-8'):
                session['name'] = user['name']
                session['email'] = user['email']
                return render_template("my.html")
            else:
                return "Error password and email not match"
        else:
            return "Error user not found"
    else:
        return render_template("login.html")

@app.route('/logout', methods=["GET", "POST"])
def logout():
    session.clear()
    return render_template("home.html")

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    else:
        name = request.form['name']
        email = request.form['email']
        password = request.form['password'].encode('utf-8')
        hash_password = bcrypt.hashpw(password, bcrypt.gensalt())

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (name, email, password) VALUES (%s,%s,%s)",(name,email,hash_password,))
        mysql.connection.commit()
        session['name'] = request.form['name']
        session['email'] = request.form['email']
        return redirect(url_for('login'))


    
    

@app.route('/my')
def my():
    return render_template('my.html')

@app.route('/Recommend',methods=['POST'])
def Recommend():
    ds = pd.read_csv('Recommend100.csv')
    df = pd.read_csv('Recommend100l.csv')
    df = df[['Title','Genre','Author','Publication','Summary']]
    ds = ds[['Title','Genre','Author','Publication','Summary']]
    # discarding the commas between the author' full names and getting only the first three names
    df['Author'] = df['Author'].map(lambda x: x.split(',')[:3])
    # putting the genres in a list of words
    df['Genre'] = df['Genre'].map(lambda x: x.lower().split(','))
    df['Publication'] = df['Publication'].map(lambda x: x.split(' '))
    # merging together first and last name for each author and publication, so it's considered as one word 
    # and there is no mix up between people sharing a first name
    for index, row in df.iterrows():
        row['Author'] = [x.lower().replace(' ','') for x in row['Author']]
        row['Publication'] = ''.join(row['Publication']).lower()
    # initializing the new column
    df['Key_words'] = ""

    for index, row in df.iterrows():
        plot = row['Summary']
    
        # instantiating Rake, by default is uses english stopwords from NLTK
        # and discard all puntuation characters
        r = Rake()
    # extracting the words by passing the text
    r.extract_keywords_from_text(plot)
    # getting the dictionary with key words and their scores
    key_words_dict_scores = r.get_word_degrees()
    # assigning the key words to the new column
    row['Key_words'] = list(key_words_dict_scores.keys())
    # dropping the Summary column
    df.drop(columns = ['Summary'], inplace = True)
    df.set_index('Title', inplace = True)
    ds.set_index('Title', inplace = True)
    df['bag_of_words'] = ''
    columns = df.columns
    for index, row in df.iterrows():
        words = ''
        for col in columns:
            if col != 'Publication':
                words = words + ' '.join(row[col])+ ' '
            else:
                words = words + row[col]+ ' '
        row['bag_of_words'] = words
    
    df.drop(columns = [col for col in df.columns if col!= 'bag_of_words'], inplace = True)
    # instantiating and generating the count matrix
    count = CountVectorizer()
    count_matrix = count.fit_transform(df['bag_of_words'])
    # creating a Series for the book titles so they are associated to an ordered numerical
    # list I will use later to match the indexes
    indices = pd.Series(df.index)
    # generating the cosine similarity matrix
    cosine_sim = cosine_similarity(count_matrix, count_matrix)
        
    if request.method == 'POST':
        title = request.form['comment']
        recommended_books = []
        title = title.lower()
        # gettin the index of the books that matches the title
        idx = indices[indices == title].index[0]

        # creating a Series with the similarity scores in descending order
        score_series = pd.Series(cosine_sim[idx]).sort_values(ascending = False)
     
        # getting the i    ndexes of the 3 most similar books
        top_3_indexes = list(score_series.iloc[1:4].index)

        # populating the list with the titles of the best 3 matching books
        for i in top_3_indexes:
            recommended_books.append(list(ds.index)[i])

    return render_template('result.html', x = recommended_books[0], y = recommended_books[1], z= recommended_books[2], a = top_3_indexes[0], b = top_3_indexes[1], c = top_3_indexes[2] )

@app.route('/about')
def about():
    return render_template("about.html") 


if __name__ == '__main__':

    app.secret_key = "^A%DJAJU^JJ123"
    app.run(debug=True)
