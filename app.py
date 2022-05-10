import hashlib
import jwt
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import requests
from datetime import datetime, timedelta
import gridfs

app = Flask(__name__)

from pymongo import MongoClient
import certifi

SECRET_KEY = 'DEVUS'

ca = certifi.where()
client = MongoClient('mongodb+srv://test:sparta@cluster0.7y6m3.mongodb.net/myFirstDatabase?retryWrites=true&w=majority', tlsCAFile=ca)
db = client.devus


@app.route('/')
def main():
    all_cards = list(db.project.find({}, {'_id': False}))
    fe_cards = list(db.project.find({'tech': 'Front-end'}, {'_id': False}))
    return render_template("main.html", all_cards=all_cards, fe_cards=fe_cards)


@app.route('/category')
def category():
    tech_receive = request.args['tech_give']
    tech_cards = list(db.project.find({'tech': tech_receive}, {'_id': False}))
    print(tech_cards)
    return jsonify({'cards_category': tech_cards})



'''
로그인 후 메인
'''

@app.route('/main')
def main_member():

    token_receive = request.cookies.get('mytoken')

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({"id": payload['id']})

        all_cards = list(db.project.find({}, {'_id': False}))
        like_nums = list(db.like.find({'user_id': user_info['id']}, {'_id': False}))  # userid & like_list

        like_cards = []
        for like_num in like_nums:
            like_card = db.project.find_one({'num': like_num}, {'_id': False})
            like_cards.append(like_card)

        return render_template('main_member.html', user_info=user_info, all_cards=all_cards, like_cards=like_cards)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 없습니다."))


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