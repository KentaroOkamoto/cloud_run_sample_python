#
# -*- encoding:UTF-8 -*-
'''
(C) Copyright 2021,2022 
File Name:SyurouCal.py
@Author:Yasuhide Sato
History:
2022-Jan-21      support args
2022-Jan-06      Initial
'''
import sys
import os
#import argparse as agp

#try:
import SyurouCalClasses.SyurouAcs as sa
#except:
#    import SyurouCalClasses.SyurouAcsDev as sa

__ver__="0.4.2"
__date__="2022-Feb-02"
'''  gunicorn で起動するときのWebApp へのargs指定わからん！！ Feb/2/2022 Y.Sato
#parser = agp.ArgumentParser("python " + __file__)
#parser.add_argument('-t','--tserver', help='就労管理テストサーバ', action='store_true')
#try:
#    args = parser.parse_args()
#except:
#    sys.exit()
'''
SFApp = sa.SyurouFlaskApp(name="KK_App",tsrvr=True)  #就労管理テストサーバ
#SFApp = sa.SyurouFlaskApp(name="KK_App")            #就労管理サーバ
app = SFApp.app

