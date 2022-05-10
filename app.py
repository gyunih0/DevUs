import hashlib
import jwt
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

from pymongo import MongoClient
import certifi

SECRET_KEY = 'DEVUS'

ca = certifi.where()
client = MongoClient('mongodb+srv://test:sparta@cluster0.7y6m3.mongodb.net/myFirstDatabase?retryWrites=true&w=majority', tlsCAFile=ca)
db = client.devus


@app.route('/')
def main():
    return render_template("main.html")


'''
회원 가입 API
'''

# HTML rendering
@app.route('/join')
def join():
    return render_template("join.html")


# 회원 등록
@app.route('/join/save', methods=['POST'])
def join_save():
    name_receive = request.form['name_give']
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']
    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()
    print(id_receive, pw_hash, name_receive)
    db.user.insert_one({'id': id_receive, 'pw': pw_hash, 'name': name_receive})

    return jsonify({'result': 'success'})


# ID 중복 체크
@app.route('/join/check_dup', methods=['POST'])
def check_dup():
    id_receive = request.form['id_give']
    exists = bool(db.user.find_one({"id": id_receive}))

    return jsonify({'result': 'success', 'exists': exists})



'''
로그인 API
'''

# HTML rendering
@app.route('/login')
def login():
    return render_template("login.html")


# 로그인 기능
@app.route('/login', methods=['POST'])
def sign_in():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    result = db.user.find_one({'id': id_receive, 'pw': pw_hash})
    print(result)

    if result is not None:
        payload = {
         'id': id_receive,
         'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({'result': 'success', 'token': token})  # deconde('utf-8') 오류

    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)