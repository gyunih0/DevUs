from pymongo import MongoClient
import certifi



ca = certifi.where()
client = MongoClient('mongodb+srv://test:sparta@cluster0.7y6m3.mongodb.net/myFirstDatabase?retryWrites=true&w=majority', tlsCAFile=ca)
db = client.devus

# 여기서 데이터 조작
def add_project():
    doc = {
        'num': 2,
        'user_name': "master",
        'project_img': "./test_image/testimg2.png",
        'tech': "Front-end",
        'description': "이것은 test num 2 입니다.",
        'like': 100
    }

    db.project.insert_one(doc)


def delete_project(num):
    db.project.delete_one({'num': int(num)})


def add_like_list():
    doc = {
        'user_id': 'master',
        'like_list': [1,2]
    }
    db.like.insert_one(doc)


def delete_like_list(user_id):
    db.like.delete_one({'user_id': user_id})


# 여기서 db조작
add_like_list()
