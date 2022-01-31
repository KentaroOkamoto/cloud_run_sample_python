#
# -*- encoding:UTF-8 -*-
'''
(C) Copyright 2021,2022
File Name:SharePointData.py
@Author:Yasuhide Sato

Jan-19-2022  Add new data class for new Evt
Dec-15-2021  Initial Data Class
'''
import os
import sys
import datetime
from dataclasses import dataclass
## 型制限付けた方がいい？
## pydantic https://memoribuka-lab.com/?p=3840
@dataclass
class EvtDate:
    year:int
    month:int
    day:int
    def date(self):
        return datetime.date(self.year,self.month,self.day)
@dataclass
class EvtTime:
    hour:int
    minute:int
    def time(self):
        return datetime.time(self.hour,self.minute)


# 在宅勤務
@dataclass
class EvtTeleWork:
    startDate:EvtDate       # 開始日
    endDate:EvtDate         # 終了日
    shiftTime:EvtTime       # シフト
    category:str = ''       # 勤務区分
    remarks:str = ''        # 備考
    usrTitle:str = ''

# 有給休暇申請
@dataclass
class EvtPTO():
    startDate:EvtDate       # 開始日
    endDate:EvtDate         # 終了日
    typePTO:str = ''        # 休暇名称
    typeTime:str = ''       # 時間帯
    reason:str = ''         # 休暇申請事由
    remarks:str = ''        # 備考
    usrTitle:str = ''

# 休暇取消
@dataclass
class EvtCancelPTO():
    startDate:EvtDate       # 休暇予定日
    endDate:EvtDate         # 終了日
    remarks:str = ''        # 取消理由
    usrTitle:str = ''


#時差勤務申請
@dataclass
class EvtShiftWork:
    startDate:EvtDate       # 開始日
    endDate:EvtDate         # 終了日
    shiftTime:EvtTime       # シフト
    remarks:str = ''        # 変更理由
    usrTitle:str = ''
