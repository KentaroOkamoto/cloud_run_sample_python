#
# -*- encoding:UTF-8 -*-
'''
(C) Copyright 2021,2022
File Name:SharePointCal.py
@Author:Yasuhide Sato
History:
2022-Jan-19      start new EVT supporting;not completed yet
2022-Jan-05      add proxy method in the class
2021-Dec-24      separated data class file         
2021-Dec-23      SharepointCal class base initial
2021-Dec-20      data class file         
2021-Dec-16      Valid day from company holiday function test
--------  From SharePointAscDev.py 
2021-Oct-14      Cleanup Code
2021-Oct-13      Supporting Delete a Event Test
2021-Oct-12      Supporting Add a Event 
2021-Oct-08      Read Items and several testing 
2021-Oct-05      Initial code refered experiments version code (sp_login.py)

Install API library
pip install --proxy=http://USER:PWD@proxy.km.local:8080 Office365-REST-Python-Client
pip install --proxy=http://USER:PWD@proxy.km.local:8080 namedivider-python

Ref:https://github.com/vgrem/Office365-REST-Python-Client

会社休日site
https://kdcf.sharepoint.com/sites/kdc_schedule/Lists/holiday/calendar.aspx

'''
import os
import sys
import datetime as dt
import pytz
from tzlocal import get_localzone

import re
from pprint import pprint
from dateutil.rrule import rrule, DAILY

try: 
    from office365.runtime.auth.user_credential import UserCredential
    from office365.sharepoint.client_context import ClientContext

    import office365.sharepoint.userprofiles.peopleManager as pm

except:
    print("Need 'office365-REST-Python-Client' Module")
    print("Please install it by following instruction")
    print("pip install --proxy=http://USER:PWD@proxy.km.local:8080 Office365-REST-Python-Client")

try:
    from namedivider import NameDivider
except:
    print("Need 'NameDivider-python'")
    print("Please install it by following instruction")
    print("pip install --proxy=http://USER:PWD@proxy.km.local:8080 namedivider-python")
from SyurouCalClasses.SharePointData import EvtDate,EvtTime,EvtTeleWork,EvtPTO

### DEBUG SWITCH ###
DBG_FULL_SHOW = True
DBG_FULL_SHOW = False

DBG_SHOW = True
DBG_SHOW = False
if DBG_FULL_SHOW:DBG_SHOW = True


### ------------------ End of Configuration -------------------

class SharepointCal:
    ''' description in sharepoint calendar to distinguish '''
    TELWORK_KEYWORD = "[TW by the Tools]"
    PTO_KEYWORD = "[PTO by the Tools]"

    def __init__(self):
        ### share point login site
        tenant_prefix = "kdcf"
        site = "kdc-mmr"
        self.site_url = f"https://{tenant_prefix}.sharepoint.com/sites/{site}"

        self.listname = ''     # you should change to access other list on sharepoint                 
        self.username = ''               # login user name
        self.pwd = ''                    # login password
        self.usrcred = None

        self.usrTitle = ''
        self.usrDescription = ''         # not used yet
        self.usrLocation = ''            # not used yet


        cal_site = "kdc_schedule"   # 全社スケジュール
        self.cal_siteUrl = f"https://{tenant_prefix}.sharepoint.com/sites/{cal_site}"

        self.calListName = "会社休日"    # you should change to access other list on sharepoint                 


    @property
    def listName(self):
        return self.listname

    @listName.setter
    def listName(self,listname):
        self.listname = listname

    @property
    def usrName(self):
        return self.username

    @usrName.setter
    def usrName(self,usr):
        self.username = usr

    @property
    def password(self):
        return self.pwd

    @password.setter
    def password(self,pwd):
        self.pwd = pwd

    '''
    def setListName(self,listname):
        ###  name of access list 
        self.listname = listname     # you should change to access other list on sharepoint                 

    def setUserPwd(self,usr,pwd):
        self.username = usr
        self.pwd = pwd
    '''

    def setUserTitle(self,title):
        self.usrTitle = title

    def __cnvDateTimeFromUtcStr0(self,timeUtcStr):
        ''' datetime from Sharepoint event time '''
        dt = timeUtcStr.split('T')
        dateStrList = dt[0].split('-');
        year = int(dateStrList[0]);month = int(dateStrList[1]);day = int(dateStrList[2])
        timeStrList = dt[1].rstrip('Z').split(':')
        hour = int(timeStrList[0]);min = int(timeStrList[1])
        timeUtc = dt.datetime(year,month, day, hour, min, tzinfo=dt.timezone.utc)
        timeOnZone = timeUtc.astimezone()
        return timeOnZone


    def _cnvDateTimeFromUtcStr(self,timeUtcStr):
        tmpDate =  dt.datetime.fromisoformat(timeUtcStr.rstrip('Z'))
        localzn = tmpDate.replace(tzinfo=pytz.utc).astimezone(get_localzone())
        return dt.datetime.combine(localzn.date(),localzn.time())


    def pickSurnameFromProperty(self,title):
        ''' Yamada, Taro(山田太郎) toro.yamada@xxx.com '''
        ''' return Yamada,山田                         '''
        splitName = title.split('(')    # split en-name and jp-name
        name_jp = ""
        if len(splitName) == 2:                            # Is jp-name
            fullname_jp = splitName[1].split(')')[0]       # pick jp-name
        else:
            fullname_jp = ""
        name = re.split('[\s，]',splitName[0])    
        name_in = f"{name[1][0]}.{name[0][0]}"
        name_en = name[0]                            # pick en-name
        if DBG_SHOW and fullname_jp != "":print(name_en,fullname_jp)
        sname = ""
        if fullname_jp != "":
                divNameObj = NameDivider()
                name_jp = str(divNameObj.divide_name(fullname_jp)).split()[0]
        return name_en,name_jp,name_in



    def loginSharepoint(self): ###
        self.usrcred = UserCredential(self.username,self.pwd)
        self.ctx = ClientContext(self.site_url).with_credentials(self.usrcred)
        ## error test case
        #self.ctx = ClientContext(site_url).with_credentials(UserCredential(sharepoint_username,"hoho"))
        ## error check if ctx
        # check sharepoint user
        ### login email Address でチェック
        userFilter = f"Email eq '{self.username}'"

        if hasattr(self.ctx.web,"siteUsers"):         ## O365 version の違い
            siteUsers = self.ctx.web.siteUsers
        elif hasattr(self.ctx.web,"site_users"):
            siteUsers = self.ctx.web.site_users
        try:
            users = siteUsers.filter(userFilter).get().execute_query()  # specific user ( login user) 
        except:
            return False
        if len(users) != 1:   # login user is not unique error
            print("user error")
            return False
        user = users[0]   # get Author ID
        surname_en,surname_jp,name_in = self.pickSurnameFromProperty(user.properties['Title'])
        if DBG_SHOW:
            print(f"User Name:{user.properties['Title']} email:{user.properties['Email']} AuthorId:{user.properties['Id']}")
            print(surname_en,surname_jp)
        self.loginInf = {'AuthorId':user.properties['Id'],'UserName':user.properties['Title'],
                         'Surname':{'en':surname_en,'ja':surname_jp},'Initial':name_in}
        return True

    def _getList(self): #### 
        ''' '''
        if self.listName is None:return None
        lists = self.ctx.web.lists.filter(f"Title eq '{self.listName}'").get().execute_query()
        if len(lists) != 1:
            print("No List ERROR:{self.listName}")
            return None
        return lists[0]

    def _getEmptyEventProperty(self):
        evtProperties = {
            'Title':None,'EventDate':None,'EndDate':None,
            'fAllDayEvent':False,'Category':None,'Location':None,
            'Description':None,'Location':None }
        return evtProperties


    def __getValidDates(self,startDate:dt.date,endDate:dt.date,chkholidays=True)->list:

        if endDate < startDate:   # check date
            print("DateError:",startDate,endDate)
            sys.exit()
            return []   # or None for Error
        '''
        ## rrule による実装確認 
        for dt in rrule(DAILY,dtstart=startDate,until=endDate):
            print(dt, type(dt),dt.date(),type(dt.date()))
        ## 内包定義でもできる
        dateList1 = [dt.date() for dt in rrule(DAILY,dtstart=startDate,until=endDate)]
        print(dateList1)
        '''
        oneDay = dt.timedelta(days=1)
        eventDateList = [startDate + i*oneDay for i in range((endDate-startDate).days + 1)]

        if not chkholidays:return eventDateList        #ignore company holidays 

        #print(dateList)
        # check company holidays #
        mrgnOfHolidays = 10       # 休み期間の途中からだと検知できないのでマージン 例えば日曜を開始にするなど
        chkStartDate=startDate - mrgnOfHolidays*oneDay
        chkEndDate=endDate + mrgnOfHolidays*oneDay

        tz = dt.timezone.utc   # time zone
        df = '%Y-%m-%dT%H:%M:%SZ'    # date, time format
        evtDate = dt.datetime.combine(chkStartDate,dt.time(0,0)).astimezone(tz).strftime(df)
        evtEndDate = dt.datetime.combine(chkEndDate,dt.time(23,59)).astimezone(tz).strftime(df)

        filter = f"EventDate ge '{evtDate}' and EndDate le '{evtEndDate}'"
        #### Campany Calendar ＜print(self.cal_siteUrl)
        cal_ctx = ClientContext(self.cal_siteUrl).with_credentials(self.usrcred)
        campanyHolidays = cal_ctx.web.lists.get_by_title(self.calListName).items.filter(filter).get().execute_query()
        holidaysList = []
        for item in campanyHolidays:
            if item.properties['Title'] == "会社休日":    # pick-up company holidays
                if DBG_SHOW:print(item.properties['Title'],item.properties['EventDate'],item.properties['EndDate'])
                y,m,d = (int(i) for i in item.properties['EventDate'].split('T')[0].split('-'))  # get EventDay in INT
                sDate=dt.date(y,m,d)
                y,m,d = (int(i) for i in item.properties['EndDate'].split('T')[0].split('-'))
                eDate=dt.date(y,m,d)
                daysList = [sDate + i*oneDay for i in range((eDate-sDate).days + 1)]             # holidays in a Event
                holidaysList += daysList                                                         # marged holidays
        if DBG_SHOW:print("Company Holidays ----------");print(holidaysList)
        # get Dates without holidays
        validDate = sorted(list(set(eventDateList).difference(holidaysList)))
        if DBG_SHOW:print("Valid event days");print(validDate)
        return validDate

        
    def __getEvtDateList(self,event):
        startDate = event.startDate.date()   # pick up start date as dt.date Obj
        endDate = event.endDate.date()       # pick up end date
        validDatesList = self.__getValidDates(startDate,endDate)
        return validDatesList


    def __PTO_Evt(self,event):
        ''' Not implement yet '''
        # 'fAllDayEvent' True にすると 2021/9/5は UTC で以下となるので検索注意
        #  'EventDate': '2021-09-05T00:00:00Z', 'EndDate': '2021-09-05T23:59:00Z'
        pass
        return True

    def __teleWorkEvt(self,event):    ######
        ''' converto to TelworkClass to sharepoint Event Data''' 

        if event.category == "在宅勤務":
            return self.__addTelworkEvt(event)
        elif event.category == "----":
            return self.__rmTeleworkEvt(event)


    def __addTelworkEvt(self,event):
        ''' '''
        evtList = self._getList()
        if evtList == None:return False  # check List avalable
        evtDateList = self.__getEvtDateList(event)
        if len(evtDateList) == 0:return None    
        oneH = dt.timedelta(hours=1)
        oneM = dt.timedelta(minutes=1)
        workTime = 8*oneH + 45*oneM   # 8:45 = 7:45 + 1:00
        workStartTime = event.shiftTime.time()
        workEndTime = (dt.datetime.combine(event.startDate.date(),workStartTime) + workTime).time()
        if self.usrTitle != '':                # is there user defined Title ?
            title = self.usrTitle   # yes; use it
        else:
            sn = self.loginInf['Surname']
            surname = sn['ja'] if  len(sn['ja']) > 0 else sn['en']
            title = f"{surname}:在宅"
            title = f"KK Test by {surname}"
        print("Title:",title)
        tz = dt.timezone.utc   # time zone
        df = '%Y-%m-%dT%H:%M:%SZ'    # date, time format
        for date in evtDateList:
            ev_dt = dt.datetime.combine(date,workStartTime).astimezone(tz).strftime(df)
            end_dt = dt.datetime.combine(date,workEndTime).astimezone(tz).strftime(df)
            ## setup a event property 
            evntProp = self._getEmptyEventProperty()
            evntProp['Title']= title
            evntProp['EventDate']=ev_dt;evntProp['EndDate']=end_dt
            evntProp['fAllDayEvent'] = False
            # for test
            evntProp['Description']=self.usrDescription + self.TELWORK_KEYWORD
            #evntProp['Location']="自宅"
            #pprint(evntProp)
            newEvntItem = evtList.add_item(evntProp)
            self.ctx.execute_batch()
        return True

    def __rmTeleworkEvt(self,event):
        ### 0:00 - 23-59 で検索 こと
        tz = dt.timezone.utc   # time zone
        df = '%Y-%m-%dT%H:%M:%SZ'    # date, time format
        localStartDate = event.startDate.date()
        localEndDate = event.endDate.date()
        evtDate = dt.datetime.combine(localStartDate,dt.time(0,0)).astimezone(tz).strftime(df)
        evtEndDate = dt.datetime.combine(localEndDate,dt.time(23,59)).astimezone(tz).strftime(df)
        filter = f"AuthorId eq {self.loginInf['AuthorId']} and EventDate ge '{evtDate}' and EndDate le '{evtEndDate}'"
        #filter = f"EventDate ge '{evtDate}' and EndDate le '{evtEndDate}'"  # ignore Author for debug
        # get items btw datetime in UTC
        items = self.ctx.web.lists.get_by_title(self.listName).items.filter(filter).get().execute_query()
        for item in items:
            itemDate = self._cnvDateTimeFromUtcStr(item.properties['EventDate']).date()
            #print(item.properties)
            #print(localStartDate,itemDate,localEndDate)
            if localStartDate <= itemDate <=localEndDate:   # within localdate
                if type(item.properties['Description']) is str and \
                   self.TELWORK_KEYWORD in item.properties['Description']:  # Is this items added by this program ?
                    # Option 1: remove a list item (with an option to restore from a recycle bin)
                    #item.recycle().execute_query()      
                    # Option 2: Permanently remove a list item
                    item.delete_object().execute_query() 
        return True

    def __shiftWorkEvt(self,event):
        ''' '''
        # not implement now
        pass

    def __cancelPTO_Evt(self,event):
        # not implement now
        pass 

    def reqEvent(self,event):    #### 
        ''' '''
        ret = self.loginSharepoint()         # login sharepoint here to avoid timeout
        if not ret:
            print("Sharepoint Login Error")
            return False

        ## 辞書定義できる？かな
        ''' dispatch event '''
        if type(event) is EvtTeleWork:         # 在宅勤務申請 
            print("Detect TelWork")
            return self.__teleWorkEvt(event)
        elif type(event) is EnvtPTO:           # 有給申請(Not implement yet: only sample entry)
            return self.__PTO_Evt(event)
        elif type(event) is EvtShiftWork:      # 時差勤務申請(Not implement yet: only sample entry)
            return self.__shiftWorkEvt(event)
        elif type(event) is EvtCancelPTO:      # 休暇取消申請(Not implement yet: only sample entry)
            return self.__cancelPTO_Evt(event)
        else:
            print("Unsuported DataClass",type(event))
            return False
        return True


    def setupProxy(self,proxy=None,proxy_port=8080,proxy_usr=None,proxy_pwd=None):
        ''' Proxy '''
        if proxy is not None: 
            if proxy_usr is not None:   # need proxy setup ?
                proxy_http= f'http://{proxy_usr}:{proxy_pwd}@{proxy}:{proxy_port}'
            else:
                proxy_http= f'http://{proxy}:{proxy_port}'
            ##print(proxy)
            os.environ['http_proxy'] = os.environ['https_proxy'] = proxy_http


if __name__ == '__main__':

    ## local base simple testing 
    ## network proxy
    PROXY = "10.181.210.177"
    PROXY_PORT = 8080
    PROXY_USR = "skype"  #<<-- your user name for a porxy
    PROXY_PWD = "skype"  #<<--

    ### share point login user/password
    sharepoint_username = "xxxxx@dc.kyocera.com" # <<-- your email address
    sharepoint_password = "xxxxx"                # <<-- same as PC login password




    PROXY_USR = "skype"                                    
    PROXY_PWD = "skype"                                    

    list_name = 'SD243課2係'     # you should change to access other list on sharepoint                 
    list_name = 'SD24技術部'     # you should change to access other list on sharepoint                 

    
    spcObj = SharepointCal()                    # get a instance
    ### network proxy settings
    spcObj.setupProxy(PROXY,PROXY_PORT,PROXY_USR,PROXY_PWD)

    spcObj.usrName = sharepoint_username        # set userName and Password
    spcObj.password = sharepoint_password       # set List Name on sharepoint calender 
    spcObj.listName = list_name                 # set list name in sharepoint calender on mmrc

    ## setup data from 就労管理から設定する
    ## userTitle  
    sDate = EvtDate(2021,9,10)
    eDate = EvtDate(2021,9,15)
    shiftTime = EvtTime(6,15)
    ctgry = "在宅勤務"
    ctgry = "----"      # 削除
    reqDataCls = EvtTeleWork(sDate,eDate,shiftTime,ctgry)
    #print(reqDataCls)
    spcObj.reqEvent(reqDataCls)

    sys.exit()

    ''' Test Code to access list'''
    evntList = spcObj._getList()   # check List Existance            
    if list is None:
        print("List is not exist")
    print("Count:",evntList.item_count)  
    if True or DBG_FULL_SHOW:
        evntItems = evntList.items.top(evntList.item_count).get().execute_query() # get All items
        print("event Item:",len(evntItems))
        #print(evntItems[0].properties.keys())  # check Item properties that sharepoint calendar has
        ''' all of sharepoint properties keys
    'FileSystemObjectType', 'Id', 'ServerRedirectedEmbedUri', 'ServerRedirectedEmbedUrl', 'ID',
    'ContentTypeId', 'Title', 'Modified', 'Created', 'AuthorId', 'EditorId', 'OData__UIVersionString',
    'Attachments', 'GUID', 'ComplianceAssetId', 'Location', 'Geolocation', 'EventDate', 'EndDate', 
    'Description', 'fAllDayEvent', 'fRecurrence', 'ParticipantsPickerId', 'ParticipantsPickerStringId', 
    'Category', 'FreeBusy', 'Overbook', 'BannerUrl', 'BannerImageUrl']
        '''
        # Show Items for debug 
        for idx,evItem in enumerate(evntItems):
            if idx > 1800:    # showing index for debug
                print(idx,evItem.properties['EventDate'],evItem.properties['Title'],evItem.properties['AuthorId'])
                pass
            pass
    sys.exit()



