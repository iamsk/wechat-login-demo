import uuid
import requests
from flask import Flask, request, jsonify
from flask_mongoengine import MongoEngine

from config import APP_ID, APP_SECRET

db = MongoEngine()
app = Flask(__name__)
app.config['MONGODB_SETTINGS'] = {'DB': 'bike'}
db.init_app(app)

dict_filter = lambda x, y: dict([(i, x[i]) for i in x if i in set(y)])


class User(db.Document):
    openid = db.StringField(unique=True)
    access_token = db.DictField()
    user_info = db.DictField()
    uid = db.StringField(unique=True)

    def __unicode__(self):
        return self.uid


def get_access_token_by_code(code):
    oauth_url = 'https://api.weixin.qq.com/sns/oauth2/access_token?appid={app_id}&secret={app_secret}&code={code}&grant_type=authorization_code'
    ret = requests.get(oauth_url.format(app_id=APP_ID, app_secret=APP_SECRET, code=code))
    return ret.json()


def get_user_info(token, openid):
    user_info_url = 'https://api.weixin.qq.com/sns/userinfo?access_token={token}&openid={openid}'
    ret = requests.get(user_info_url.format(token=token, openid=openid))
    return ret.json()


@app.route("/login_wechat")
def login():
    code = request.form.get('code', '')
    if not code:
        return jsonify({})
    access_token = get_access_token_by_code(code)
    openid = access_token['openid']
    user_info = get_user_info(access_token['access_token'], access_token['openid'])
    user = User.objects.get(openid=openid)
    if user:
        user.access_token = access_token
        user.user_info = user_info
        uid = user.uid
    else:
        uid = uuid.uuid5('bike', openid)
        user = User(openid=openid, access_token=access_token, user_info=user_info, uid=uid)
    user.save()
    return jsonify({'uid': uid})


@app.route("/self")
def get_user():
    uid = request.args.get('uid', '') or request.form.get('uid', '')
    if not uid:
        return jsonify({})
    user = User.objects.get(uid=uid)
    if not user:
        return jsonify({})
    wanted_keys = ('province', 'openid', 'headimgurl', 'city', 'country', 'nickname', 'sex')
    profile = dict_filter(user.data, wanted_keys)
    profile['uid'] = uid
    profile['phone'] = ''
    profile['email'] = ''
    profile['cycling_count'] = ''
    profile['cycling_miles'] = ''
    profile['cycling_time'] = ''
    profile['equipment'] = ''
    profile['headline'] = ''
    profile['background'] = ''
    return jsonify(profile)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8998, debug=True)
