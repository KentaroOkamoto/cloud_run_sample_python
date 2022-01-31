#
# -*- encoding:UTF-8 -*-
'''
(C) Copyright 2021,2022 
File Name:SyurouAcs.py
@Author:Yasuhide Sato
History:
2022-Jan-24      Test Server connection option
2022-Jan-6       Login Error
2021-Dec         Cleanup Code
2021-Dec         Class化
2021-Oct-15      Cleanup Code

ToDo: Error検知、タイムアウト処理
'''
import os
import sys

import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning
urllib3.disable_warnings(InsecureRequestWarning)

from collections import OrderedDict
#from flask import Flask,request,send_file, Response
from flask import Flask, request, Response
import flask


from threading import Thread
import webbrowser
import time
import urllib.parse

if "SyurouAcs.py" in __file__:
    import SyurouCalClasses.SharePointCal as spcal
else:
    import SyurouCalClasses.SharePointCalDev as spcal

import SyurouCalClasses.SharePointData as dc       # data class for sharepoint access

## TestMode   申請手前でPostしない
DBG_TEST=False       # 正式版 申請もする
#DBG_TEST=True        # テスト(Sharepoint登録のみ)

### Login に就労
LOGIN = False
##LOGIN = True   未完成 設計中

### Browser を開く(Local単体テストのみ有効)
AUTO_BROWSER_OPEN=True
AUTO_BROWSER_OPEN=False

#debug MSG
if "SyurouAcs.py" in __file__:
    DBG_MSG = False         # disabled
else:
    DBG_MSG = True
    #DBG_MSG = False

class SyurouCore:
    def __init__(self):
        self.login_cookies = None
        self.url = None
        self.loginParams = None
        self.rootUrl = None

    def setLoginParams(self,userId,password):
        self.loginParams = {
            '@SID':'','@SN':'null','@FN':'259963950','@FS':'I',
            'uid':userId,'pwd':password,
            'Login':'ログイン','@TMZ_MIN': '540'
        }

    def login(self):
        res = requests.post(self.url, params=self.loginParams, verify=False)
        if res.status_code == 200:
            self.login_cookies = res.cookies   
            return res
        else:
            print("Login Fail");sys.exit()

    def requestPost(self,Params):
        res = requests.post(self.url, cookies=self.login_cookies,params=Params, verify=False)
        return res

    def requestGet(self,Params):
        res = requests.get(self.url, cookies=self.login_cookies, verify=False)
        return res 

    def checkKeyWord(self, res, keyList):
        ''' レスポンスの内容にKeyword があるかチェック '''
        ''' 画面が遷移したときなどに活用               '''
        keyResult = {}
        content = urllib.parse.unquote(res.content.decode())
        for key in keyList:
            keyResult[key] = True if content.find(key) > 0 else False
        return keyResult

    def checkAfterLoginDisplay(self,res):
        ## login 成功？  Keywordで調べる
        keyword = ["個人情報メニュー","チャレンジ目標 / 評価"]
        list = self.checkKeyWord(res,keyword)
        ret = False if False in list.values() else True  
        return ret

    #property

    def setUrl(self,url):
        self.url = url

    def getUrl(self):
        return self.url

    @property
    def Cookie(self):
        return self.login_cookies

    # will be removed soon
    #def getCookie(self):
    #    return self.login_cookies

#-------------------------------------------------------------------
class EndpointAction(object):

    def __init__(self, action):
        self.action = action
        #self.response = flask.Response(status=200, headers={})

    def __call__(self, *args, **kwargs):
        # check function args
        funcParams = self.action.__code__.co_varnames[:self.action.__code__.co_argcount]
        #print(args,kwargs,funcParams)
        params = [ kwargs[kw] for kw in funcParams if kw != 'self']
        #print("PARAMS:",params)
        # Perform the action
        if len(params) != 0:
            answer = self.action(*params)  # with params function
        else:
            answer = self.action()
        return answer

#-------------------------------------------------------------------
class SyurouFlaskApp(object):
    app = None

    def __init__(self, name,tsrvr=False):
        self.app = Flask(name)
        self.__all_endpoint()

        self.syuObj = SyurouCore()
        if tsrvr:
            print("就労管理テストサーバ接続: working 9:00-18:00")
            self.baseUrl = "http://cws-ap-ccms-test.km.local:17100"  # test server 
        else:
            print("就労管理サーバ接続")
            self.baseUrl = "https://comedge10.km.local"

        self.reqUrl = self.baseUrl + "/cws/cws"
        self.syuObj.setUrl(self.reqUrl) 
        self.spObj = spcal.SharepointCal()

        PROXY = "proxy.km.local"
        PROXY_PORT = 8080
        PROXY_USR = "skype"                                    
        PROXY_PWD = "skype"                                    

        self.spObj.setupProxy(PROXY,PROXY_PORT,PROXY_USR,PROXY_PWD)
        self.action  = ''

        self.spObj.usrName = self.spObj.password = ''
        ##自動で取得できないかねー sharepoint login 前か...
        self.listnames= ["SD24技術部","SD242課1係","SD242課2係","SD243課1係","SD243課2係"]

        self.ReqDic = OrderedDict({"在宅勤務申請/取消":self.__mvTeleworkPage})
        
        self.pageMsg = ''' 在宅勤務申請システム(Sharepontカレンダー自動登録付)'''

    def run(self):
        self.app.run()

    def __all_endpoint(self):
        ''' endpoing 設定不安 いらない？'''
        self.app.add_url_rule('/images/<path:img_file>', endpoint='/images/<path:img_file>', view_func=EndpointAction(self.__images),methods=['GET',])
        self.app.add_url_rule('/scripts/<path:script_file>', endpoint='/scripts/<path:script_file>', view_func=EndpointAction(self.__script),methods=['GET',])
        self.app.add_url_rule('/cssdir/<path:cssdir_file>', endpoint='/cssdir/<path:cssdir_file>', view_func=EndpointAction(self.__cssdir),methods=['GET',])
        self.app.add_url_rule('/css/<path:css_file>', endpoint='/css/<path:css_file>', view_func=EndpointAction(self.__css),methods=['GET',])
        self.app.add_url_rule('/js/<path:js_file>', endpoint='/js/<path:js_file>', view_func=EndpointAction(self.__js),methods=['GET',])
        self.app.add_url_rule('/ace', endpoint='/ace', view_func=EndpointAction(self.__ace),methods=['POST',])
        self.app.add_url_rule('/navigation.css', endpoint='/navigation.css', view_func=EndpointAction(self.__naviGet),methods=['GET',])
        self.app.add_url_rule('/cws', endpoint='/cws', view_func=EndpointAction(self.__cws),methods=['GET','POST'])
        #self.app.add_url_rule('/cws', endpoint='/cws', view_func=EndpointAction(self.__cws),methods=['POST',])
        self.app.add_url_rule('/', endpoint='/', view_func=EndpointAction(self.__root),methods=['GET','POST'])

    def __getFile(self,imgUrl): ### initial version : not use now
        for i in range(5):   # retry 5 times if status 500
            res = requests.get(imgUrl,verify=False,stream=True,cookies=self.syuObj.Cookie)
            if res.status_code==200:break    # 500 リトライ
            time.sleep(1)
        return res

    def __getFile2(self,imgUrl,dir):
        for i in range(5):   # retry 5 times if status 500
            res = requests.get(imgUrl,verify=False,stream=True,cookies=self.syuObj.Cookie)
            if res.status_code==200:break    # 500 リトライ
            time.sleep(1)
        if res.status_code==200:
            # save to local  memory_tmpfile 使える？
            file = dir + "/"+ imgUrl.split('/')[-1].split('?')[0]
            with open(file,'wb') as f:
                f.write(res.content)
            return res,file
        else:
            print("<<<<<<< ERROR >>>>>>>")
            print(imgUrl,res.status_code)
            return res,None

    def __getQuery(self):
        ''' '''
        query = ""
        if len(request.args) > 0:   ####
            sep = '?'               # initial sep
            for i in request.args:  # get key
                query += (sep + i + '=' +  request.args[i]) # gen key=value with sep
                sep = '&'           # change sep
        return query

    def __replaceResponse(self,res, mode = False):  ## modeいらない たぶん
        ''' 申請 画面パッチ   '''
        content = urllib.parse.unquote(res.content.decode())
        ### URL変更
    
        ##content = content.replace("src=\"..","src=\"https://comedge10.km.local")   
        ##content = content.replace("href=\"..","href=\"https://comedge10.km.local")
    
        pos = content.find(self.action) 
        strLen = len(self.action)
        if content.find(self.action) > 0:
            ''' 1つ目はTitleのようなので2つ目を変更 '''
            c = content.count(self.action)
            if c > 1:
                pos = content[pos+strLen:].find(self.action) 
            content = content[:pos]+ content[pos:].replace(self.action,
                                    f'<div style="color:green;">Sharepoint {self.spObj.listName}カレンダー登録付 </div>{self.action}',1)
            #'<div style="color:green;">Sharepoint登録付</div > 在宅勤務（兼 在宅勤務取消）申請]')
            ''' Ignore "一時保存" '''
            ignoreLink = ["就労メインページ","トップページ","ログアウト","予定申請"]
            idx = content.find("一時保存")
            sidx = content[:idx].rfind("<")
            eidx = content[idx:].find(">")
            #content = content.replace(content[sidx:idx+eidx+1],"")
            ignoreLink.append(content[sidx:idx+eidx+1])
            #
            for i in ignoreLink:
                content = content.replace(i,"")
        content = urllib.parse.unquote(content).encode()
        return content


    def __mvTeleworkPage(self):
        ''' 在宅申請画面に移動'''
        self.action = "在宅勤務（兼 在宅勤務取消）申請"
        self.datacls = self.__getTeleworkDataCls    # function of the data class 
        req_params = {
            '@SID':'',
            '@SUB':'root.cws.shuro.application.srw_app_absence04',
            '@SN':'root.cws.shuro.application.srw_app_absence04',
            '@FN':'form_srw_app',
            '@ACTION_LOG_TXT':self.action,
            '@TMZ_MIN': '540'
        }
        return self.syuObj.requestPost(req_params)

    def __mvPTO_Page(self):
        ''' 有給休暇画面に移動'''
        self.action = "有給休暇申請（全日/半日）"
        self.datacls = self.__getPTO_DataCls
        req_params = {
            '@SID':'',
            '@SUB':'root.cws.shuro.application.app_vacation.srw_app_paidvacation_jiyu02',
            '@SN':'root.cws.shuro.application.app_vacation.srw_app_paidvacation_jiyu02',
            '@FN':'form_srw_ap',
            '@ACTION_LOG_TXT':self.action,
            '@TMZ_MIN': '540'
        }
        return self.syuObj.requestPost(req_params)

    def __mvCancelPTO_Page(self):
        ''' 有給休暇取消 画面に移動'''
        self.action = "有給休暇取消"
        self.datacls = self.__getCancelPTO_DataCls
        req_params = {
            '@SID':'',
            '@SUB':'root.cws.shuro.application.app_vacation.srw_app_cancel_vacation',
            '@SN':'root.cws.shuro.application.app_vacation.srw_app_cancel_vacation',
            '@FN':'form_srw_app',
            '@ACTION_LOG_TXT':self.action,
            '@TMZ_MIN': '540'
        }
        return self.syuObj.requestPost(req_params)

    def __mvPTOTime_Page(self):
        ''' 有給休暇申請（時間単位）画面に移動'''
        self.action = "有給休暇申請（時間単位）"
        self.datacls = self.__getPTOTime_DataCls
        req_params = {
            '@SID':'',
            '@SUB':'root.cws.shuro.application.app_vacation.srw_app_vc0',
            '@SN':'root.cws.shuro.application.app_vacation.srw_app_vc0',
            '@FN':'form_srw_app',
            '@ACTION_LOG_TXT':self.action,
            '@TMZ_MIN': '540'
        }
        return self.syuObj.requestPost(req_params)

    def __mvShiftTimePage(self):
        ''' 時差勤務申請画面に移動'''
        self.action = "時差勤務申請"
        self.datacls = self.__getShiftTimeDataCls
        req_params = {
            '@SID':'',
            '@SUB':'root.cws.shuro.application.srw_app_absence01',
            '@SN':'root.cws.shuro.application.srw_app_absence01',
            '@FN':'form_srw_app',
            '@ACTION_LOG_TXT':self.action,
            '@TMZ_MIN': '540'
        }
        return self.syuObj.requestPost(req_params)

    def __getDates(self,reqParams):
        ''' 開始,終了日をEvtDate Data Classとして得る'''
        sy = int(reqParams['sdate_date_yyyy'])
        sm = int(reqParams['sdate_date_mm'])
        sd = int(reqParams['sdate_date_dd'])
        sDate = dc.EvtDate(sy,sm,sd)
        try:
            ey = int(reqParams['edate_date_yyyy'])
            em = int(reqParams['edate_date_mm'])
            ed = int(reqParams['edate_date_dd'])
            eDate = dc.EvtDate(ey,em,ed)
        except:
            eDate = dc.EvtDate(sy,sm,sd)    # edateが未指定なのでsdateと同じにする
        return sDate,eDate

    ##----------------- 各申請のデータクラス---------------------------------
    def __getTeleworkDataCls(self,reqParams):
        ''' EvtTeleWork Data classを作成して返す'''
        sDate,eDate = self.__getDates(reqParams)
        h = int(reqParams['kinmu_cd'][:-2])
        m = int(reqParams['kinmu_cd'][-2:])
        shiftTime = dc.EvtTime(h,m)
        ctgry = ["----","在宅勤務"][int(reqParams['gi1_10'])]
        #remarks = self.reqParamsSend['reason'] # 備考
        #usrTitle = ''
        reqDataCls = dc.EvtTeleWork(sDate,eDate,shiftTime,ctgry)
        if DBG_MSG:print(reqDataCls)
        return reqDataCls


    def __getPTO_DataCls(self,reqParams):
        ''' '''
        print("PTO")
        print(reqParams)
        sys.exit()
        sDate,eDate = self.__getDates(reqParams)
        typeTimeDic = {'0':'全休','1':'前半日休暇','2':'後半日休暇'}
        typeResonDic = {'00':'私事都合','10': '体調不良','11':'通院','21':'産前',
                        '81':'9連続休暇','82':'リフレッシュ休暇','83':'多目的休暇',
                        '84':'一斉有休取得','85':'KMJ夏期連続休暇','99':'その他'}
        typeTime = typeTimeDic[reqParams['kyuka_time_kb']]
        typeReason = typeResonDic[reqParams['kyuka_jiyu_cd']]
        namePTO = '年次有給休暇'
        #usrTitle = ''
        #remarks = self.reqParamsSend['reason'] # 備考        
        '''
        startDate:EvtDate
        endDate:EvtDate
        typePTO:str = ''
        typeTime:str = ''
        reason:str = ''
        remarks:str = ''
        '''
        reqDataCls = dc.EvtPTO(sDate,eDate,namePTO,typeTime,typeReason)
        if DBG_MSG:print(reqDataCls)
        return reqDataCls

    def __getCancelPTO_DataCls(self,reqParams):
        print("CancelPTO")
        print(reqParams)
        pass
        sys.exit()
        #reqDataCls = dc.
        #if DBG_MSG:print(reqDataCls)
        #return reqDataCls

    def __getPTOTime_DataCls(self,reqParams):
        print("PTO Time")
        print(reqParams)
        pass
        sys.exit()
        #reqDataCls = dc.
        #if DBG_MSG:print(reqDataCls)
        #return reqDataCls

    def __getShiftTimeDataCls(self,reqParams):
        print(reqParams)
        pass
        sys.exit()
        sDate,eDate = self.__getDates(reqParams)
        h = int(reqParams['kinmu_cd'][:-2])
        m = int(reqParams['kinmu_cd'][-2:])
        shiftTime = dc.EvtTime(h,m)
        #remarks = self.reqParamsSend['reason'] # 備考
        #usrTitle = ''
        reqDataCls = dc.EvtTeleWork(sDate,eDate,shiftTime,ctgry)
        if DBG_MSG:print(reqDataCls)
        return reqDataCls

    ##-----------------------------------------
    def __reqSharepoint(self,reqParams):
        ''' Sharepoint へ登録 '''
        reqDataCls = self.datacls(reqParams)
        #reqDataCls = self.__getTeleworkDataCls(reqParams)
        ## 遲い Thread + MSG Queue ?
        self.spObj.reqEvent(reqDataCls)
    
    def _proxy(self,*args, **kwargs):
        ''' Test Proxy '''
        if DBG_MSG:print(f"=======_proxy======={request.host_url}============================")
        query = self.__getQuery()
        resp = requests.request(
            method=request.method,
            url=request.url.replace(request.host_url, self.baseUrl + '/') + query,
            headers={key: value for (key, value) in request.headers if key != 'Host'},
            data=request.get_data(),
            cookies=self.syuObj.Cookie,
            allow_redirects=False,verify=False)
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]
        response = flask.Response(resp.content, resp.status_code, headers)
        return response

    #@app.route('/images/<path:img_file>')
    def __images(self,img_file):
        query = self.__getQuery()
        if DBG_MSG:print(f"=======Image File======={img_file}===================================")
        imgReqUrl = self.baseUrl + "/images/" + img_file + query
        url=request.url.replace(request.host_url, self.baseUrl + '/'),
        res,filePath = self.__getFile2(imgReqUrl,"images")
        return flask.send_file(filePath,mimetype="image/gif")

    #@app.route('/scripts/<path:script_file>')
    def __script(self,script_file):
        query = self.__getQuery()
        if DBG_MSG:print(f"=======script File======={script_file}===================================")
        scriptReqUrl = self.baseUrl + "/scripts/" + script_file + query
        if DBG_MSG:print(scriptReqUrl)
        res,filePath = self.__getFile2(scriptReqUrl,"scriptTmp")
        if ".css" in script_file:
            mtype = 'text/css'
        if ".js" in script_file:
            mtype = 'text/javascript'
        return flask.send_file(filePath, mimetype=mtype)

    #@app.route('/cssdir/<path:cssdir_file>')
    def __cssdir(self,cssdir_file):
        query = self.__getQuery()
        if DBG_MSG:print(f"=======CSSDIR File======={cssdir_file}===================================")
        cssReqUrl = self.baseUrl + "/cssdir/" + cssdir_file + query
        res,filePath = self.__getFile2(cssReqUrl,"cssTmp")
        return flask.send_file(filePath, mimetype='text/css')

    #@app.route('/css/<path:css_file>')
    def __css(self,css_file):
        if DBG_MSG:print(f"=======CSS File======={css_file}===================================")
        cssReqUrl = self.baseUrl + "/css/" + css_file
        res,filePath = self.__getFile2(cssReqUrl,"cssTmp")
        return flask.send_file(filePath, mimetype='text/css')

    #@app.route('/js/<path:js_file>')
    def __js(self,js_file):
        if DBG_MSG:print(f"=======JS File======={js_file}===================================")
        jsReqUrl = self.baseUrl + "/js/" + js_file
        res,filePath = self.__getFile2(jsReqUrl,"jsTmp")
        return flask.send_file(filePath, mimetype='text/javascript')

    #@app.route('/ace',methods=['POST'])
    def __ace(self):
        query = self.__getQuery()
        if DBG_MSG:print(f"-------------POST--ACE----------")
        formParams = request.form.to_dict()
        #'Content-Length'
        cwsUrl = self.baseUrl + "/cws/ace" + query
        res = requests.post(cwsUrl, cookies= self.syuObj.Cookie, params=formParams,verify=False)
        if res.status_code == 200:
            content = self.__replaceResponse(res)
            return content

    #@app.route('/navigation.css',methods=['GET'])
    def __naviGet(self):
        if DBG_MSG:print("-------------GET--navigation.css------------------")
        res = self._proxy()
        return res

    #@app.route('/cws',methods=['GET'])
    def __cwsGet(self):
        if DBG_MSG:print("-------------GET--CWS------------------")
        res = self._proxy()
        return res

    #@app.route('/cws',methods=['POST','GET'])
    def __cws(self):
        if request.method == 'GET':
            return self.__cwsGet()
        elif request.method == 'POST':
            return self.__cwsPost()
        else:
            res = self._proxy()
            return res
            
    #@app.route('/cws',methods=['POST'])
    def __cwsPost(self):
        if DBG_MSG:print(f"-------------POST--CWS---{request.form['@FN']}-------")
        ## need query parm ?
        #query = self.__getQuery()
        sharepointReq = False
        req_params = request.form.to_dict()
        if DBG_MSG:print(req_params)
    
        if '@FN' in request.form:
            if DBG_MSG:print("@FN",request.form['@FN']) #'root.cws.shuro.application.srw_app_absence04'
            if LOGIN and request.form['@FN'] == '259963950':  ## Login画面 実験
                if request.form['Login'] == 'ログイン':
                    self.syuObj.setLoginParams(request.form['uid'],request.form['pwd']) 
                    res = self.syuObj.login()                               # login 
                    if self.syuObj.checkAfterLoginDisplay(res) == False:
                        content = self.__replaceResponse(res)
                        return content
                    ###### Req で切替or 
                    res = self.__mvTeleworkPage()
                    content = self.__replaceResponse(res)
                    return content
        # dictで判定
        if '@SN' in request.form:
            if DBG_MSG:print('@SN',request.form['@SN']) #'root.cws.shuro.application.srw_app_absence04'
        if '@SUB' in request.form:
            if DBG_MSG:print('@SUB',request.form['@SUB']) #

            if request.form['@SUB'] == '次 へ':   # 【入力】画面からのReqest ?
                # 送信でパラメータ拾えないケースではここでキープ
                self.reqParamsSend = request.form.to_dict() # keep it to send sharepoint after
                if DBG_MSG:print("次 へ",req_params)
                self.reqParamsSend['Reqested'] = False
            elif request.form['@SUB'] == '送 信': # 【確認】画面からのReqest ?
                # ここでパラメータ拾えない　
                req_params = request.form.to_dict()   # already converted !!!!
                ### 送信 Callback to sharepoint
                print("送信",req_params)
                # 送信 変換なし？
                if DBG_TEST:
                    if DBG_MSG:print("デバッグなので修正")
                    req_params['@SUB'] = '修正'  # for Debug 
                sharepointReq = True
            else:
                pass
                #'Content-Length'
        # 就労システムにPOST
        res = requests.post(self.reqUrl, cookies= self.syuObj.Cookie, params=req_params,verify=False)
        content = self.__replaceResponse(res)
        if res.status_code == 200:
            #if req_params['@SUB'] == '送 信': # 【完了】画面か？ (【確認】画面からの遷移)
            if DBG_TEST or req_params['@SUB'] == '送 信': # DBG Code 【完了】画面か？ (【確認】画面からの遷移)
                #check 在宅申請送信成功したか？content チェック【完了】’でチェックでいい？
                ## check no error
                if sharepointReq:
                    print("Sharepoint Calendar")
                    print(self.reqParamsSend)
                    self.__reqSharepoint(self.reqParamsSend)
                    self.reqParamsSend = None        
                else:
                    # error 時 そのままでいい？
                    pass
                if not DBG_TEST:
                    self.reqParamsSend = None  ## if req_params['@SUB'] == '送 信':のみの場合エラーでしりき直し
        return content

    def __root(self):
        if request.method == 'GET':
            return self.__rootGet()
        elif request.method == 'POST':
            return self.__rootPost()
        else:
            print("Not Support '/':",request.method)

    # 初期画面からのPOST
    #@app.route('/',methods=['POST'])
    def __rootPost(self):
        if DBG_MSG:print("------------- ROOT POST----------------------")
        req_params = request.form.to_dict()
        if 'pp_username' in req_params:
            self.spObj.usrName =  req_params['pp_username']   # set Powerpoint userName and Password
            self.spObj.password = req_params['pp_password']   # 
            self.spObj.listName = req_params['list']          # set list name in sharepoint calender on mmrc

        ### need sharepoint login test
        if not self.spObj.loginSharepoint():
            print("<<<<<<<<<<<<<<<<<< Sharepoint Login ERROR >>>>>>>>>>>>>>>>>>>>>>")
            self.spObj.usrName = self.spObj.password = '' # reset
            return flask.render_template("index.html",message = self.pageMsg,
                                         errMsg='Sharepoint Login Fail:ユーザーID、パスワードが違います',
                                         listnamesList = self.listnames,
                                         pp_uname=self.spObj.usrName, 
                                         pp_pwd = self.spObj.password,
                                         reqNamesList=list(self.ReqDic.keys()) )
            
        # error MSG  + index.html
        if req_params['REQ'] in self.ReqDic.keys() and (not LOGIN):
            return self.autologin(req_params['username'],req_params['password'],req_params['REQ'])
        else:
            return self.mnlLogin()

    # 初期画面
    #@app.route('/',methods=['GET'])
    def __rootGet(self):
        if DBG_MSG:print("/ GET:",request.args,"==========================================")
        return flask.render_template("index.html",message = self.pageMsg,
                                     listnamesList = self.listnames,
                                     pp_uname=self.spObj.usrName, 
                                     pp_pwd = self.spObj.password,
                                     reqNamesList=list(self.ReqDic.keys()) )

    def mnlLogin(self):
        ''' マニュアルlogin:就労システムのLogin Page '''
        if DBG_MSG:print("--------------GET--User Login Manually------------------")
        res = requests.get(self.reqUrl, verify=False)
        #self.req_text = 'xxxxxx' # for login
        content = self.__replaceResponse(res)
        return content     # show login


        if self.syuObj.checkAfterLoginDisplay(res) == False:
            content = self.__replaceResponse(res)
            return content
        ## move 在宅勤務（兼+在宅勤務取消）申請 メニュー
        res = self.ReqDic[req]()
        content = self.__replaceResponse(res)
        return content

    def autologin(self,userId,password,req): # 暫定
        try:
            if LOGIN:  # 就労login 
                return self.mnlLogin()
            if DBG_MSG:print("--------------GET--User Login------------------")
            ## AutoLogin
            self.syuObj.setLoginParams(userId,password)
            res = self.syuObj.login()       
            ## login 成功？  Keywordで調べる
            if self.syuObj.checkAfterLoginDisplay(res) == False:
                print("<<<<<<<<<<<<<<<<<< 就労Login ERROR >>>>>>>>>>>>>>>>>>>>>>")
                return flask.render_template("index.html",message = self.pageMsg,
                                             errMsg='就労管理Login Fail:ユーザーID、パスワードが違います',
                                             listnamesList = self.listnames,
                                             pp_uname=self.spObj.usrName, 
                                             pp_pwd = self.spObj.password,
                                             reqNamesList=list(self.ReqDic.keys()) )
            ## move 在宅勤務（兼+在宅勤務取消）申請 メニュー
            res = self.ReqDic[req]()
            content = self.__replaceResponse(res)
            return content
        except Exception as e:
            print("------Exception------")
            return str(e)

# Thread Base起動実験
def runFlask():
    #app.run(debug=True,threaded=True)
    #app.run(host='0.0.0.0',port=80)
    app.run()

'''  Flask '''
if __name__ == "__main__":
    SFApp = SyurouFlaskApp("TestApp")
    SFApp.run()
    sys.exit()
    #thread1 = Thread(target=runFlask)
    #thread1.start()

    #app.run()
    time.sleep(1)  # wait start up Flask
    flaskUrl = "http://127.0.0.1:5000"
    if AUTO_BROWSER_OPEN:
        webbrowser.open(flaskUrl, autoraise=1)
    sys.exit()


