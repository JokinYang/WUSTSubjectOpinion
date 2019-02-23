import random
import re
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from log import logger
from ocr import predict


class Jwc:
    def __init__(self, usr=None, pwd=None):
        self.usr = usr
        self.pwd = pwd or usr
        self.session = requests.session()
        self.session.headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip,deflate',
            'Accept-Language': 'zh - Hans - CN, zh - Hans',
            'Connection': 'Keep-Alive',
            'User-Agent': 'Mozilla / 5.0(Windows NT 10.0;WOW64;Trident/7.0; rv11.0) like Gecko',
            'Referer': 'http://jwxt.wust.edu.cn/whkjdx/framework/main.jsp',
        }
        # 初始化cookies
        self.session.get('http://jwxt.wust.edu.cn/whkjdx/framework/main.jsp')
        self.scriptSessionId = None
        self.menus: list = None
        self.isLogin = False
        self.MAX_TIME = 3

    def login(self, usr=None, pwd=None):
        self.usr = usr or self.usr
        self.pwd = pwd or self.pwd
        login_url = 'http://jwxt.wust.edu.cn/whkjdx/Logon.do?method=logon'
        data = {
            'USERNAME': self.usr,
            'PASSWORD': self.pwd,
            'useDogCode': '',
            'useDogCode': '',
            'RANDOMCODE': predict(self._get_verify_code()),
            'x': random.randrange(1, 74),
            'y': random.randrange(1, 22),
        }
        response = self.session.post(url=login_url, data=data)
        if 'window.location.href=' not in response.text:
            bs = BeautifulSoup(response.text, 'lxml')
            self.isLogin = False
            return bs.find(id='errorinfo').text
        # 必须要使用SSO登录 要不然会显示无法创建对象
        loginBySSO_url = 'http://jwxt.wust.edu.cn/whkjdx/Logon.do?method=logonBySSO'
        m = self.session.post(loginBySSO_url)
        self.menus = self.xml2dict(str(m.content, encoding='gb2312'))['Level2Menus']
        self.isLogin = True
        logger.info('用户:{}登录成功'.format(self.usr))
        return True

    def check_login(self):
        try:
            while not self.isLogin and self.MAX_TIME:
                self.login()
                self.MAX_TIME -= 1
                url = 'http://jwxt.wust.edu.cn/whkjdx/framework/grxx_edit.jsp'
                response = self.session.get(url)
                if '登录帐号：' in response.text:
                    self.isLogin = True
                    break
                else:
                    errorkey = re.compile("var errorKey = '(.*)';").findall(response.text)
                    logger.warning('用户登录失败 errorkey:' + str(errorkey))
                    logger.info('将会进行第{}次重试，共3次'.format(3 - self.MAX_TIME))
                    self.isLogin = False
        except Exception as e:
            logger.error(e)
        finally:
            # 确保MAX_TIME能够被重置
            self.MAX_TIME = 3

    def logout(self):
        url = 'http://jwxt.wust.edu.cn/whkjdx/Logon.do?method=logout'
        self.session.get(url, allow_redirects=False)

    # 用来获取scriptSessionId，但是目前并没有用处
    def _get_scriptSessionId(self):
        url = 'http://jwxt.wust.edu.cn/whkjdx/dwr/engine.js'
        response = self.session.get(url).text
        oss_re = re.compile('dwr.engine._origScriptSessionId = "(.*)";')
        origScriptSessionId = oss_re.findall(response)[0]
        scriptSessionId = origScriptSessionId + str(int(random.random() * 1000))
        self.scriptSessionId = scriptSessionId

    # 教评
    def subject_opinion(self):
        self.check_login()
        if not self.isLogin:
            logger.info('用户{}登录失败'.format(self.usr))
            return False
        # so_url = list(filter(lambda x: x['title'] == '教学评价', self.menus))[0]['path']

        so_url = 'http://jwxt.wust.edu.cn/whkjdx/jiaowu/jxpj/jxpjgl_queryxs.jsp'
        response = self.session.get(so_url)

        bs = BeautifulSoup(response.text, 'lxml')
        default_xnxq = None
        # 学年学期
        xnxq: Tag = bs.find_all('select', attrs={'name': 'xnxq'})[0]
        # 评价批次
        pjpc: Tag = bs.find_all('select', attrs={'name': 'pjpc'})[0]
        # 评价课程
        pjkc: Tag = bs.find_all('select', attrs={'name': 'pjkc'})[0]
        xnxq_list = []
        default_pjpc_list = []
        default_pjkc_list = []
        for x in xnxq.children:
            if not x['value']:
                continue
            if 'selected' in x.attrs:
                default_xnxq = {'value': x['value'], 'text': x.text}

            xnxq_list.append({'value': x['value'], 'text': x.text})
        for x in pjpc.children:
            if not x['value']:
                continue
            default_pjpc_list.append({'value': x['value'],
                                      'text': x.text})
        for x in pjkc.children:
            if not x['value']:
                continue
            default_pjkc_list.append({'value': x['value'],
                                      'text': x.text})

        # useless
        # 获取教学评价的描述
        def get_pj_desctipe(pjpc_input):
            url = 'http://jwxt.wust.edu.cn/whkjdx/jxpjgl.do?method=queryJxlbsm&type=xs&pjid={}'.format(
                pjpc_input['value'])
            r = self.session.get(url)
            b = BeautifulSoup(r.text, 'lxml')
            return b.find_all('nobr')[0].text.replace('\t', '')

        logger.info('默认教学评价学期:' + default_xnxq['text'])

        # 返回包含所有教学评价的页面
        def queryJxpj(xnxq, pjpc, pjkc):
            url = 'http://jwxt.wust.edu.cn/whkjdx/jxpjgl.do?method=queryJxpj&type=xs'
            data = {
                'xnxq': xnxq,
                'pjkc': pjkc,
                'pjpc': pjpc,
                'sfxsyjzb': 0,
                'cmdok': '查询',
                'zbnrstring': '',
                'ok': ''
            }
            return self.session.post(url=url, data=data).text

        # 通过queryJxpj返回的html来寻找单个科目的教学评价链接
        def search_pj(html: str) -> list:
            pj = BeautifulSoup(html, 'lxml')
            p = pj.find_all('a', attrs={'href': 'javascript:void(0);'})
            pj_list = []
            for x in p:
                if x.text == '查看':
                    continue
                pj_list.append('http://jwxt.wust.edu.cn' +
                               re.match(r"javascript:JsMods\('(.*)',(?:.*)", x['onclick'].replace(' ', '')).groups()[0])
            return pj_list

        # 通过URL来填写教评并提交
        def doit(url):
            r = self.session.get(url)
            last = BeautifulSoup(r.text, 'lxml')
            form = last.find(name='form', attrs={'name': 'Form1'})
            hidden_input = form.find_all('input', attrs={'type': 'hidden'})
            radio = form.find_all('input', attrs={'type': 'radio'})
            textarea = form.find_all('textarea')

            # 最后要post的数据
            data = {}
            for x in hidden_input:
                data[x['name']] = x['value']
            data['type'] = 2

            # 从这里开始到下一个空行(不包含get_value函数之后的)是用来获取radio1...的值
            # 通过radio（1-5）的位置和选项（0,4）的位置来获取radio的value
            def get_value(radio, index):
                '''从五个值中选出'''
                for x in radio_list:
                    if x['name'] == radio and x['radioxh'] == str(index):
                        return x['value']

            radio_data = {}
            radio_list = []
            for y in radio:
                radio_list.append(y)
            radio_name = ['radio1', 'radio2', 'radio3', 'radio4', 'radio5']

            # zero = random.choice(radio_name)
            # radio_name.remove(zero)
            # radio_data[zero] = get_value(zero, 0)
            # 0,1代表评价等级0-4分数依次变低
            # 加上注释之后可得满分
            # one = random.choice(radio_name)
            # radio_name.remove(one)
            # radio_data[one] = get_value(one, 1)

            for x in radio_name:
                radio_data[x] = get_value(x, 0)
            # radio_data[x] = get_value(x, random.choice([0, 1]))

            for text in textarea:
                data[text['name']] = ''

            data.update(radio_data)
            val = '*'.join([radio_data[x] for x in ['radio1', 'radio2', 'radio3', 'radio4', 'radio5']])
            # post 数据准备完毕 准备提交
            final_url = 'http://jwxt.wust.edu.cn/whkjdx/jxpjgl.do?method=savePj&tjfs=2&val={}'.format(val)
            final_response = self.session.post(url=final_url, data=data)
            if "alert('保存成功!');" in final_response.text:
                return True
            else:
                return final_response.text

        for temp_pjkc in default_pjkc_list:
            for temp_pjpc in default_pjpc_list:
                logger.info('正在评价{},{}'.format(temp_pjpc['text'], temp_pjkc['text']))
                h = queryJxpj(xnxq=default_xnxq['value'], pjpc=temp_pjpc['value'], pjkc=temp_pjkc['value'])
                for x in search_pj(h):
                    ans = doit(x)
                    logger.info('评论结果:' + str(ans))
        logger.info('{}教评完成 '.format(self.usr))
        return True

    def _get_verify_code(self):
        url = 'http://jwxt.wust.edu.cn/whkjdx/verifycode.servlet?{}'.format(random.random())
        return self.session.get(url).content

    @staticmethod
    def xml2dict(xml: str) -> dict:
        ans = {}
        et = ET.fromstring(xml)
        for x in et.getchildren():
            ans[x.tag] = [z.attrib for z in x]
        return ans

    def main(self):
        url = 'http://httpbin.org/headers'
        self.login('201502112039', '13237191721')
        self.subject_opinion()


if __name__ == '__main__':
    for x in range(201502112046, 201502112060):
        x = 201502112060
        pwd = '123456789'
        try:
            jwc = Jwc(x, pwd)
            jwc.login()
            jwc.subject_opinion()
        except Exception as e:
            print('-' * 5, e)
        break
# [print(x) for x in jwc.menus]
