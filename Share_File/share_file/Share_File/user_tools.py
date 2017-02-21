# -*- coding:utf8 -*-
import my_db


"""用户管理类"""

check_arg = my_db.validate_arg


def check_info(user_name, user_password):
    """检查用户登录"""
    message = {"message": "success"}
    if check_arg(user_name, "_") and check_arg(user_password):
        sql = "select user_password from user_info where user_status=1 " \
              "and user_name='{}'".format(user_name)
        ses = my_db.sql_session()
        proxy = ses.execute(sql)
        result = proxy.fetchone()
        ses.close()
        if result is None:
            message['message'] = '用户不存在'
        else:
            old_pw = result[0]
            if user_password.lower() == old_pw.lower():
                pass
            else:
                message['message'] = '密码错误'
    else:
        message['message'] = '参数验证失败'
    return message


print(check_info('xlj', 'e10adc3949ba59abbe56e057f20f883e'))