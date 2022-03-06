# -*- coding: utf-8 -*-
import os

from log import logger
from main import Jwc


def subject_opinion(usr=None, pwd=None):
    if not usr:
        # logger.warning('请输入正确的学号')
        return False
    try:
        jwc = Jwc(usr=usr, pwd=pwd)
        jwc.subject_opinion()
    except Exception as e:
        logger.warning('{}未评价成功'.format(usr))
        logger.error(e)
    finally:
        jwc.logout()


so_type = '1'

while True:
    os.system('cls||clear')
    if so_type not in ['1', '2', '3', '']:
        print(' 输入有误，请输入1,2,3之中的一个数字')

    print(' 1-> 单人教评 (输入学号，密码 如不输入密码默认与学号相同) \n '
          ' 2-> 班级教评 （输入学号范围,修改过密码的同学会被跳过） \n '
          ' 3-> 通过文件输入学号和密码')

    so_type = input(' \n请输入教评模式(默认为1):')
    if so_type in ['1', '2', '3', '']:
        break

if so_type == '1' or '':
    t = input('请输入学号,密码(与学号相同可省略):')
    i = list(filter(lambda x: x is not '', t.split(' ')))
    subject_opinion(*i)

if so_type == '2':
    r = input('请输入学号范围:')
    i = list(filter(lambda x: x is not '', r.split(' ')))
    i = sorted(i)
    print(i)
    if len(i) is not 2:
        print('输入有误!')
    m = i[0]
    n = i[1]
    for x in range(m, int(n) + 1):
        subject_opinion(x)

if so_type == '3':
    f = input('请输入文件路径(可输入相对路径或绝对路径):')
    if not os.path.isfile(f):
        print('请输入正确的文件地址')
    with open(f, 'r') as t:
        lines = t.readlines()
    for x in lines:
        i = list(filter(lambda x: x is not '', x.split(' ')))
        subject_opinion(*i)

input('请按任意键退出')
