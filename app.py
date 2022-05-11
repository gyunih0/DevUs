import hashlib
from datetime import datetime, timedelta

import jwt
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)

from pymongo import MongoClient
import certifi

SECRET_KEY = 'DEVUS'

ca = certifi.where()
client = MongoClient('mongodb+srv://test:sparta@cluster0.7y6m3.mongodb.net/myFirstDatabase?retryWrites=true&w=majority',
                     tlsCAFile=ca)
db = client.devus

'''
메인페이지 API
'''


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


@app.route('/project/<num_give>')
def project_detail(num_give):
    detail_cards = db.project.find_one({'num': int(num_give)}, {'_id': False})
    return render_template("detail.html", cards=detail_cards)


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
        fe_cards = list(db.project.find({'tech': 'Front-end'}, {'_id': False}))

        like_nums = list(db.like.find({'user_id': user_info['id']}, {'_id': False}))
        print("like", like_nums)
        like_nums = like_nums[0]['like_list']
        like_cards = []
        for like_num in like_nums:
            like_card = db.project.find_one({'num': like_num}, {'_id': False})
            like_cards.append(like_card)

        return render_template('main_member.html', user_info=user_info, all_cards=all_cards, like_cards=like_cards,
                               fe_cards=fe_cards, like_nums=like_nums)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("main", msg="로그인 정보가 없습니다."))


@app.route('/main/category')
def main_category():
    #get cookie -> userid
    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    user_info = db.user.find_one({"id": payload['id']})

    tech_receive = request.args['tech_give']
    id_receive = user_info['id']
    tech_cards = list(db.project.find({'tech': tech_receive}, {'_id': False}))
    print(tech_cards)
    like_cards = list(db.like.find({'user_id': id_receive}, {'_id': False}))
    like_nums = like_cards[0]['like_list']
    print(like_nums)

    for tech_card in tech_cards:
        if tech_card['num'] in like_nums:
            tech_card['status'] = 'like'
        else:
            tech_card['status'] = 'unlike'

    print(tech_cards)
    return jsonify({'cards_category': tech_cards})


@app.route("/main", methods=["POST"])
def project_post():
    user_name_receive = request.form.get('user_name', False)  # 폼에서 전송하는 데이터 받는 형식
    tech_receive = request.form.get('tech', False)
    description_receive = request.form.get('description', False)
    project_img_receive = 'none'

    file = request.files['project_file']  # html에서 파일 가져오기

    if file.filename != 'project_file':
        file.save("./static/test_images/" + secure_filename(file.filename))  # 파일저장
        project_img_receive = file.filename

    project_list = list(db.project.find({}, {'_id': False}))

    num = len(project_list) + 1  # 게시물 번호 부여
    while len(list(db.project.find({'num': num}))) != 0:  # 게시물 확인
        num += 1

    doc = {
        'num': num,  # 게시물 번호
        'user_name': user_name_receive,  # 게시물 작성자 이름
        'project_img': project_img_receive,  # 게시물 이미지
        'tech_receive': tech_receive,  # 기술(fn,bn,ful)
        'description': description_receive,  # 상세 설명
        'like': 0  # 좋아요 초기값 0
    }

    db.project.insert_one(doc)  # db 추가

    return render_template('main.html')


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


'''
좋아요 API
'''


# 좋아요 기능
@app.route('/like', methods=['POST'])
def like():
    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    user_info = db.user.find_one({"id": payload['id']})

    id_receive = user_info['id']  # 회원 아이디
    print(id_receive)
    num_receive = int(request.form['num_give'])  # 게시물 num
    # like_receive = int(request.form['like_give'])  # 기존 좋아요 개수

    project = db.project.find_one({'num': num_receive})
    like_receive = project['like']

    like_list = db.like.find_one({'user_id': id_receive})

    like_nums = like_list['like_list']  # [1,2,3]
    print(like_nums)
    # 좋아요가 안된 게시물이라면
    if num_receive not in like_nums:
        print("test")
        # db.like에 게시물 num 등록한다.
        like_nums.append(num_receive)
        print(like_nums)
        db.like.update_one({'user_id': id_receive}, {'$set': {'like_list': like_nums}})

        # db.project에서 게시물의 like를 올려준다
        db.project.update_one({'num': num_receive}, {'$set': {'like': like_receive + 1}})

        return jsonify({'result': 'success', 'like': like_receive + 1})
        # db.project.update-> like += 1, db.like.update  / result: like up /

    # 좋아요가 되있는 게시물이라면
    else:
        # db.like에 게시물 num를 제외시킨다.
        like_nums.remove(num_receive)
        db.like.update_one({'user_id': id_receive}, {'$set': {'like_list': like_nums}})

        # db.project에서 게시물의 like를 내려준다
        db.project.update_one({'num': num_receive}, {'$set': {'like': like_receive - 1}})

        return jsonify({'result': 'success', 'like': like_receive - 1})
        # db.project.update-> like -= 1, db.like.update / result: like down /


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
