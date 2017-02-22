# -*- coding:utf8 -*-
from flask import session, url_for, redirect, request
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms import PasswordField
from wtforms import FileField
from wtforms import SubmitField
from wtforms.validators import DataRequired
from flask_wtf.file import FileRequired, FileAllowed
from werkzeug.contrib.cache import RedisCache
from functools import wraps
import datetime
import random

from uuid import uuid4
import base64
import urllib.request

import os

"""公用的函数和装饰器"""

cache = RedisCache()
WTF_CSRF_SECRET_KEY = os.urandom(24)


"""工具方法和类定义开始"""


def get_img_csrf():
    """生成一个img_csrf"""
    aid = get_only_id()
    val = uuid4().hex
    cache.set(aid, val, timeout=60)
    return {"id": aid, "val": val}


def check_img_csrf(atr):
    """比对img_csrf"""
    temp = atr.split("|")
    aid = temp[0]
    val = temp[1]
    new_val = cache.get(aid)
    if new_val is None or val != new_val:
        flag = False
    else:
        flag = True
    cache.delete(aid)
    return flag


def check_img_code(token, img_code):
    """检查验证码的方法，正确返回True,token是csrf_token"""
    if img_code == cache.get(token):
        return True
    else:
        return False


def set_user_login_info(my_session, user_id, user_password, user_img_url, user_level):
    """用户注册或登录成功后，把用户信息加入缓存"""
    my_session["user_id"] = user_id
    my_session["user_password"] = user_password
    my_session["user_img_url"] = user_img_url
    my_session["user_level"] = user_level
    cache.set(user_id, user_password, timeout=0)


def set_admin_login_info(my_session, admin_id, admin_password):
    """管理员注册或登录成功后，把管理员信息加入缓存"""
    admin_id = str(admin_id)
    my_session["admin_id"] = admin_id
    my_session["admin_password"] = admin_password
    cache.set(admin_id, admin_password, timeout=0)


class PhotoForm(FlaskForm):
    """文件上传的子类"""
    photo = FileField('photo',validators=[FileRequired(),
                                          FileAllowed(['png','jpg', 'jpeg'], "只能上传图片")])
    submit_img_button = SubmitField("submit_img_button")


def current_datetime():
    """获取当前的日期和时间，以字符串类型返回，格式为：2016-12-19 14:33:03"""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


class SubmitLoginForm(FlaskForm):
    """自定义一个Form的子类，为flask-wtf服务，用作提交问题"""
    question_txt = StringField("问题", validators=[DataRequired()])


class SearchLoginForm(FlaskForm):
    """自定义一个Form的子类，为flask-wtf服务，用作搜索"""
    # search_txt = StringField("关键词", validators=[DataRequired()])
    """注销是为了允许客户搜索空字符串"""


class RequestLoginForm(FlaskForm):
    """自定义一个Form的子类，为flask-wtf服务，用作后台检测"""
    def generate_csrf_token(self, csrf_context=None):
        """
        重写此方法的原因是 flask-wtf 0.14 版本没有generate_csrf_tokengenerate_csrf_token这个方法。
        注意重载父类的方法。
        1. 必须方法名和参数都一直，否则会报错。
        2. 注意用super调用父类方法的方式，第一个参数是自身的类型名。第二个参数是self
        """
        try:
            value = super(RequestLoginForm, self).generate_csrf_token(csrf_context)
        except AttributeError:
            value = self.csrf_token.current_token
        return value


class AdminLoginForm(FlaskForm):
    """自定义一个Form的子类，为flask-wtf服务，用作管理登录检测"""
    admin_name = StringField('账户', validators=[DataRequired()])
    admin_password = PasswordField('密码', validators=[DataRequired()])


class UserLoginForm(FlaskForm):
    """自定义一个Form的子类，为flask-wtf服务，用作用户登录检测"""
    phone = StringField('手机', validators=[DataRequired()])
    user_password = PasswordField('密码', validators=[DataRequired()])
    # img_code = StringField('图形验证码', validators=[DataRequired()])


class UserRegForm(FlaskForm):
    """自定义一个Form的子类，为flask-wtf服务，用作注册检测"""
    phone = StringField('手机', validators=[DataRequired()])
    user_password = PasswordField('密码', validators=[DataRequired()])
    # sms_code = StringField('验证码', validators=[DataRequired()])


def get_arg(req, arg, default_value=''):
    """
    flask的request获取参数的简化方法，可以获取get和post的参数。共有三个参数
    1.req  当前的请求。一般都是传入当前上下文的request
    2.arg  参数名称
    3.default_value  未获取到参数时的默认值。默认情况下是空字符
    return 获取到的参数(字符串或默认值)
    """
    return (default_value if req.form.get(arg) is None else req.form.get(arg)) if req.args.get(
        arg) is None else req.args.get(arg)


def get_real_ip(req):
    """
    获取当前请求的真实ip。参数只有一个：
    1.req  当前的请求。一般都是传入当前上下文的request
    return ip地址(字符串格式)
    """
    try:
        ip = req.headers["X-Forwarded-For"].split(":")[0]
    except KeyError as e:
        ip = req.remote_addr  # 注意：tornado是 remote_ip
    return ip


def allow_cross_domain(resp):
    """
    处理跨域请求的方法，传入一个response，返回一个跨域的response
    1.resp  当前上下文的respponse对象
    return 进行跨域处理后的response对象
    """
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'PUT,GET,POST,DELETE'
    allow_headers = "Referer,Accept,Origin,User-Agent"
    resp.headers['Access-Control-Allow-Headers'] = allow_headers
    return resp


# 获取唯一id的方法
class OnlyID:
    """一个获取唯一id的类，单例模式，使用方式有两种：
    1. 创建一个类实例，然用使用这个实例调用get_id方法返回一个唯一id。
    2. 直接使用类的静态方法:OnlyID.get() 返回一个唯一的id。
    return: 一个长度为20的字符串格式的id（纯数字组成的字符串）
    """

    def __init__(self):
        pass

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'instance'):
            obj = super(OnlyID, cls).__new__(cls)
            obj.id_list = []
            cls.instance = obj
            cls.instance.fill()
        return cls.instance

    def get_id(self):
        """返回一个唯一的id """
        if len(self.id_list) < 2:
            self.fill()
        else:
            pass
        # 2位数的年份的日期，格式化到毫秒
        str1 = datetime.datetime.now().strftime('%y%m%d%H%M%S%f')
        str2 = self.id_list.pop()
        return str1 + str(str2)

    @staticmethod
    def get():
        """静态方法，返回一个唯一的id ,这是暴露给外界使用的获取并使用此id的方法，
        此id将会被从待用id序列中被剔除"""
        return OnlyID().get_id()

    @staticmethod
    def check_next():
        """
        静态方法，获取一个id但并不从待用id序列中取走
        """
        obj = OnlyID()
        if len(obj.id_list) < 2:
            obj.fill()
        else:
            pass
        # 2位数的年份的日期，格式化到毫秒
        str1 = datetime.datetime.now().strftime('%y%m%d%H%M%S%f')
        str2 = obj.id_list[-1]
        return str1 + str(str2)

    def fill(self):
        """重新填充备用的id"""
        while len(self.id_list) < 20:  # 最大备用id数设置
            temp = random.randint(10, 99)
            if temp not in self.id_list:
                self.id_list.append(temp)


def current_only_id():
    """查看当前可用的id"""
    return OnlyID.check_next()


def get_only_id():
    """获取当前id并把此id从待用序列中剔除"""
    return OnlyID.get()



"""工具方法定义结束"""

"""装饰器定义"""


# def login_required_user(f):
#     """检测用户是否登录的装饰器"""
#
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         user_id = session.get("user_id")  # 检测session中的account
#         user_password = session.get("user_password")  # 检测session中的password
#         """登录完毕后会跳转会这个地址"""
#         host_url = request.host_url
#         referrer = request.base_url
#         referrer = referrer.replace(host_url, "/").rstrip()
#         # 对网址路径进行加密
#         referrer = base64.b64encode(referrer.encode("utf8"))
#
#         if user_id is None or user_password is None:  # 会话检测失败
#             """方案1，自行拼接url"""
#             """必须要进行url编码，否则某些不合法的字符可能会导致错误"""
#             """safe="=" 是不对等号进行编码"""
#             referrer = urllib.request.quote(referrer.decode("utf8"), safe="=", encoding="utf8")
#             return redirect(url_for("my_login", ref=referrer))
#             #return redirect(url_for("login")+"?ref={}".format(str(referrer)))
#         else:
#             result = user.check_id(user_id, user_password)
#             if result['message'] != "success":
#                 """方案2 利用url_for，url_for有传入参数的功能,会附加在url的尾部，推荐第二种"""
#                 return redirect(url_for("my_login", ref=referrer))
#
#         return f(*args, **kwargs)
#
#     return decorated_function


# def login_required_admin(f):
#     """检测管理员是否登录的装饰器"""
#
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         admin_id = session.get("admin_id")  # 检测session中的account
#         admin_password = session.get("admin_password")  # 检测session中的password
#         if admin_password is None or admin_id is None:  # 会话检测失败
#             return redirect(url_for("admin_login_page"))
#         else:
#             result = admin.check_admin_id(admin_id, admin_password)
#             if result['message'] != "success":
#                 return redirect(url_for("admin_login_page"))
#         return f(*args, **kwargs)
#
#     return decorated_function


"""装饰器定义结束"""




