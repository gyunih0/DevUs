import hashlib
from datetime import datetime, timedelta

import jwt
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename

from operator import itemgetter

app = Flask(__name__)

from pymongo import MongoClient
import certifi

SECRET_KEY = 'DEVUS'

ca = certifi.where()
client = MongoClient('mongodb+srv://test:sparta@cluster0.7y6m3.mongodb.net/myFirstDatabase?retryWrites=true&w=majority',
                     tlsCAFile=ca)
db = client.devus


def get_user_info(token_receive):
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    user_info = db.user.find_one({"id": payload['id']})
    return user_info


'''
메인페이지 API
'''


@app.route('/')
def main():
    # 모든 card 가져오기
    all_cards = list(db.project.find({}, {'_id': False}))

    # 좋아요 많은 순으로 정렬
    top3_like_cards = sorted(all_cards[0:3], key=lambda like_card: like_card['like'], reverse=True)
    print(len(top3_like_cards))

    # 카테고리 선택 전 Front-end card 가져오기
    fe_cards = list(db.project.find({'tech': 'Front-end'}, {'_id': False}))

    return render_template("main.html", all_cards=all_cards, fe_cards=fe_cards, top3_like_cards=top3_like_cards)


@app.route('/category')
def category():
    # 카테고리 선택 시 카테고리명 받아오기
    tech_receive = request.args['tech_give']

    # 카테고리 별 card 가져오기
    tech_cards = list(db.project.find({'tech': tech_receive}, {'_id': False}))
    return jsonify({'cards_category': tech_cards})


@app.route('/project/<num_give>')
def project_detail(num_give):
    # 상세페이지 카드 가져오기
    detail_cards = db.project.find_one({'num': int(num_give)}, {'_id': False})

    # 토큰 가져오기
    token_receive = request.cookies.get('mytoken')

    # 토큰 null 판별을 위한 트리거
    exist_token = False

    # 토근 null 판별
    if token_receive is not None:
        exist_token = True

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({"id": payload['id']})

        like_nums = list(db.like.find({'user_id': user_info['id']}, {'_id': False}))

        if not like_nums:  # 첫 회원가입 또는 like 없는상태
            status = "unlike"
            return render_template('detail.html', exist_token=exist_token, cards=detail_cards, status=status)
        else:
            like_nums = like_nums[0]['like_list']

            if int(num_give) not in like_nums:
                status = "unlike"
                print(status)
                return render_template('detail.html', exist_token=exist_token, cards=detail_cards, status=status)
            else:
                status = "like"
                print(status)
                return render_template('detail.html', exist_token=exist_token, cards=detail_cards, status=status)

    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:

        return render_template("detail.html", cards=detail_cards, exist_token=exist_token)


'''
회원 API
'''

# 메인 페이지
@app.route('/main')
def main_member():
    # 쿠키(토큰) 요청
    token_receive = request.cookies.get('mytoken')

    try:
        # 토큰 decoding -> user_info
        user_info = get_user_info(token_receive)

        # project 전체
        all_cards = list(db.project.find({}, {'_id': False}))
        # default category = frontend
        fe_cards = list(db.project.find({'tech': 'Front-end'}, {'_id': False}))

        # 회원의 좋아요 list = [{user_id: user_id, like_list:[num, num, ...] }]
        like_nums = list(db.like.find({'user_id': user_info['id']}, {'_id': False}))

        if not like_nums:  # 좋아요 누른 프로젝트가 없다면
            return render_template('main_member.html', user_info=user_info, all_cards=all_cards,
                                   fe_cards=fe_cards)

        else:  # 좋아요 누른 프로젝트가 있다면
            like_nums = like_nums[0]['like_list']  # like_nums = [num,num,..]
            like_cards = []  # 좋아요 누른 프로젝트들의 list
            for like_num in like_nums:
                like_card = db.project.find_one({'num': like_num}, {'_id': False})
                like_cards.append(like_card)

            sorted_like_cards = sorted(like_cards, key=lambda like_card: like_card['like'], reverse=True)

            return render_template('main_member.html', user_info=user_info, like_cards=sorted_like_cards,
                                   fe_cards=fe_cards, like_nums=like_nums)

    except jwt.ExpiredSignatureError:  # exp 만료
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:  # 토큰 없음
        return redirect(url_for("main", msg="로그인 정보가 없습니다."))

# 메인 하단 카테고리별 분류
@app.route('/main/category')
def main_category():
    # get cookie -> userid
    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

    tech_receive = request.args['tech_give']
    id_receive = payload['id']
    tech_cards = list(db.project.find({'tech': tech_receive}, {'_id': False}))  # 선택한 카테고리의 프로젝트들
    like_cards = list(db.like.find({'user_id': id_receive}, {'_id': False}))  # 좋아요 누른 프로젝트 num의 list

    if not like_cards:  # 좋아요 누른 프로젝트가 없다면
        for tech_card in tech_cards:
            tech_card['status'] = 'unlike'
    else:  # 좋아요 누른 프로젝트가 있다면
        like_nums = like_cards[0]['like_list']  # like_nums = [num, num, ..]
        for tech_card in tech_cards:
            if tech_card['num'] in like_nums:
                tech_card['status'] = 'like'
            else:
                tech_card['status'] = 'unlike'

    return jsonify({'cards_category': tech_cards})


@app.route("/main", methods=["POST"])
def project_post():
    # 토큰 decoding -> user_info
    token_receive = request.cookies.get('mytoken')
    user_info = get_user_info(token_receive)

    user_name_receive = user_info['name']
    project_name_receive = request.form.get('project_name', False)  # 폼에서 전송하는 데이터 받는 형식
    tech_receive = request.form.get('tech', False)
    description_receive = request.form.get('description', False)
    project_img_receive = 'none'

    file = request.files['project_file']  # html에서 파일 가져오기

    if file.filename != 'project_file':
        file.save("./static/test_image/" + secure_filename(file.filename))  # 파일저장
        project_img_receive = file.filename

    project_list = list(db.project.find({}, {'_id': False}))

    num = len(project_list) + 1  # 게시물 번호 부여
    while len(list(db.project.find({'num': num}))) != 0:  # 게시물 확인
        num += 1

    doc = {
        'num': num,  # 게시물 번호
        'project_name': project_name_receive,  # 프로젝트 이름
        'user_name': user_name_receive,  # 게시물 작성자 이름
        'project_img': '../static/test_image/' + project_img_receive,  # 게시물 이미지
        'tech': tech_receive,  # 기술(fn,bn,ful)
        'description': description_receive,  # 상세 설명
        'like': 0  # 좋아요 초기값 0
    }
    print(doc['project_img'])
    db.project.insert_one(doc)  # db 추가

    return redirect(url_for("main_member"))


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

    db.user.insert_one({'id': id_receive, 'pw': pw_hash, 'name': name_receive})
    print('join|id: {}, name: {}, pw: {}'.format(id_receive, name_receive, pw_hash))

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

    if result is not None:
        payload = {
            'id': id_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        print(result)
        return jsonify({'result': 'success', 'token': token})

    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


'''
좋아요 API
'''


# 좋아요 기능
@app.route('/like', methods=['POST'])
def like():
    token_receive = request.cookies.get('mytoken')
    user_info = get_user_info(token_receive)

    id_receive = user_info['id']  # 회원 아이디
    print(id_receive)
    num_receive = int(request.form['num_give'])  # 게시물 num
    # like_receive = int(request.form['like_give'])  # 기존 좋아요 개수

    project = db.project.find_one({'num': num_receive})
    like_receive = project['like']

    like_list = list(db.like.find({'user_id': id_receive}, {'_id': False}))
    print(like_list)
    like_nums = []
    if not like_list:  # db.like에 정보가 없다면 (첫 좋아요 누르기) 새로운 db 생성
        doc = {
            'user_id': id_receive,
            'like_list': []
        }
        db.like.insert_one(doc)

        # db.like에 게시물 num 등록한다.
        like_nums.append(num_receive)
        db.like.update_one({'user_id': id_receive}, {'$set': {'like_list': like_nums}})

        # db.project에서 게시물의 like를 올려준다
        db.project.update_one({'num': num_receive}, {'$set': {'like': like_receive + 1}})

        return jsonify({'result': 'success', 'like': like_receive + 1})
        # db.project.update-> like += 1, db.like.update  / result: like up /
    else:
        like_nums = like_list[0]['like_list']  # [1,2,3]
        print(like_nums)
        # 좋아요가 안된 게시물이라면
        if num_receive not in like_nums:

            # db.like에 게시물 num 등록한다.
            like_nums.append(num_receive)

            db.like.update_one({'user_id': id_receive}, {'$set': {'like_list': like_nums}})

            # db.project에서 게시물의 like를 올려준다
            db.project.update_one({'num': num_receive}, {'$set': {'like': like_receive + 1}})

            return jsonify({'result': 'success', 'like': like_receive + 1})

        # 좋아요가 되어있는 게시물이라면
        else:
            # db.like에 게시물 num를 제외시킨다.
            like_nums.remove(num_receive)
            db.like.update_one({'user_id': id_receive}, {'$set': {'like_list': like_nums}})

            # db.project에서 게시물의 like를 내려준다
            db.project.update_one({'num': num_receive}, {'$set': {'like': like_receive - 1}})

            return jsonify({'result': 'success', 'like': like_receive - 1})



if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
