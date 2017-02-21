# -*- coding:utf8 -*-
from flask import Flask, abort, render_template, send_file, send_from_directory
from flask_uploads import UploadSet, IMAGES, configure_uploads
from wtforms import Form
from wtforms import FileField
from flask_session import Session
from werkzeug.utils import secure_filename
import sys
import shutil
import user_tools
import json
from my_tools import *
import mimetypes


port = 5667
app = Flask(__name__)

"""上传文件相关配置"""
upload_dir_path = sys.path[0] + os.sep + "static" + os.sep + 'upload'
if not os.path.exists(upload_dir_path):
    os.makedirs(upload_dir_path)
UPLOAD_FOLDER = upload_dir_path  # 后台上传图片上传的路径
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = ('png', 'jpg', 'jpeg', 'gif', 'zip')  # 允许上传的图片后缀

"""主程序基础配置部分"""
session_key = os.urandom(24)
app.config.update({
    'SESSION_PERMANENT': False,  # 配置会话的生命期不是永久有效
    'USE_X_SENDFILE': False,
    "SECRET_KEY": session_key  # 配置session的密钥
})
SESSION_TYPE = 'redis'  # flask-session使用redis，注意必须安装redis数据库和对应的redis模块
app.config.from_object(__name__)  # flask-session相关
Session(app)  # flask-session相关


def allowed_file(filename):
    """检查上传文件类型"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def get_arg_dict(req):
    """取出一次请求的所有参数，返回字典，req是request对象"""
    the_form = req.form
    a_dict = {key: the_form[key] for key in the_form.keys()}
    return a_dict


def login_required_user(f):
    """检测是否登录的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_name = session.get("user_name")  # 检测session中的account
        user_password = session.get("user_password")  # 检测session中的password
        if user_name is None or user_password is None:  # 会话检测失败
            return redirect(url_for("login_page"))
        else:
            result = user_tools.check_info(user_name, user_password)
            if result['message'] != "success":
                try:
                    session.pop("user_name")
                    session.pop("user_password")
                except KeyError:
                    pass
                return redirect(url_for("login_page"))
            else:
                pass
        return f(*args, **kwargs)

    return decorated_function


@app.route("/login", methods=['post', 'get'])
def login_page():
    """用户登录"""
    if request.method.lower() == "get":
        return render_template("login.html")
    else:
        user_name = get_arg(request, 'user_name')
        user_password = get_arg(request, 'user_password')
        result = user_tools.check_info(user_name, user_password)
        if result['message'] == 'success':
            session['user_name'] = user_name
            session['user_password'] = user_password
        else:
            try:
                session.pop("user_name")
                session.pop("user_password")
            except KeyError:
                pass
        return json.dumps(result)


@app.route("/edit_file", methods=['post'])
@login_required_user
def edit_file():
    """对文件和目录的操作：删除，改名"""
    arg_dict = get_arg_dict(request)
    the_type = arg_dict.pop("the_type")
    message = {"message": "success"}
    if the_type == "rename":
        old_name = arg_dict['old_name']
        new_name = arg_dict['new_name']
        dir_path = arg_dict['path']
        user_name = arg_dict['user_name']
        old_path = os.path.join(app.config['UPLOAD_FOLDER'], user_name, dir_path, old_name)
        new_path = os.path.join(app.config['UPLOAD_FOLDER'], user_name, dir_path, new_name)

        try:
            os.rename(old_path, new_path)
        except OSError:
            message['message'] = "文件名修改失败"

    elif the_type == "delete":
        file_name = arg_dict['file_name']
        dir_path = arg_dict['path']
        user_name = arg_dict['user_name']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], user_name, dir_path, file_name)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except IOError:
                message['message'] = "文件删除失败"
        elif os.path.isdir(file_path):
            try:
                shutil.rmtree(file_path)
            except Exception:
                message['message'] = "文件夹删除失败"

    elif the_type == "new_dir":
        file_name = arg_dict['file_name']
        dir_path = arg_dict['path']
        user_name = arg_dict['user_name']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], user_name, dir_path, file_name)
        if os.path.exists(file_path):
            message['message'] = '文件夹已存在'
        else:
            try:
                os.makedirs(file_path)
            except IOError:
                message['message'] = '文件夹创建失败'

    return json.dumps(message)


@app.route("/download/<user_name>/")
@login_required_user
def download(user_name):
    """用户下载文件"""
    try:
        ses_name = session['user_name']
    except KeyError:
        ses_name = ""

    if ses_name and user_name == ses_name:
        path = get_arg(request, "path")
        file_name = get_arg(request, "file_name")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], user_name, path, file_name)
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                return send_from_directory(file_path, file_name, as_attachment=True)
            elif os.path.isfile(file_path):
                return send_file(file_path, as_attachment=True)
            else:
                abort(404)
        else:
            return "你下载的文件不存在", 404
    else:
        abort(403)


@app.route('/user_upload_simple', methods=('GET', 'POST'))
@login_required_user
def user_upload_simple():
    """用户上传图片"""
    file = request.files['file']
    dir_path = request.referrer.split("/uploads/")[-1]  # 取用户路径/用户名
    file_name = file.filename
    if file and allowed_file(file_name):
        """注销是因为安全文件名不支持中文"""
        # file_name = secure_filename(file_name)  # 取文件类型
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], dir_path + os.sep + file_name))
        return "ok"

    else:
        abort(403)


@app.route('/uploads/<dir_01>')
@login_required_user
def hello_world(dir_01):
    """用户一级目录页面"""
    current_user_name = dir_01
    """探测用户目录是否存在"""
    user_path = UPLOAD_FOLDER + os.sep + current_user_name
    if not os.path.exists(user_path):
        os.makedirs(user_path)
    """探测目录下的目录和文件"""
    temp_list = os.listdir(user_path)
    dir_list = list()
    file_list = list()
    for x in temp_list:
        temp_url = user_path + os.sep + x
        if os.path.isdir(temp_url):
            dir_list.append(x)
        else:
            file_list.append(x)

    return render_template("uploads.html", current_path="/", dir_list=dir_list,
                           file_list=file_list, current_user_name=current_user_name)


@app.route('/uploads/<dir_01>/<dir_02>')
@login_required_user
def hello_world2(dir_01, dir_02):
    """用户二级目录页面"""
    current_user_name = dir_01
    current_dir = dir_02
    """探测用户目录是否存在"""
    user_path = os.path.join(UPLOAD_FOLDER, current_user_name, current_dir)
    if not os.path.exists(user_path):
        os.makedirs(user_path)
    """探测目录下的目录和文件"""
    temp_list = os.listdir(user_path)
    dir_list = list()
    file_list = list()
    for x in temp_list:
        temp_url = user_path + os.sep + x
        if os.path.isdir(temp_url):
            dir_list.append(x)
        else:
            file_list.append(x)

    return render_template("uploads.html", current_path="/" + dir_02, dir_list=dir_list,
                           file_list=file_list, current_user_name=current_user_name)


@app.route("/")
def index():
    return "hello world"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True, threaded=True)
