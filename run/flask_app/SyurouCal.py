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
import argparse as agp

try:
    import SyurouCalClasses.SyurouAcs as sa
except:
    import SyurouCalClasses.SyurouAcsDev as sa

__ver__="0.4.3"
__date__="2022-Feb-08"

parser = agp.ArgumentParser("python " + __file__)
parser.add_argument('-t','--tserver', help='就労管理テストサーバ', action='store_true')
try:
    args = parser.parse_args()
except:
    sys.exit()
SFApp = sa.SyurouFlaskApp(name="KK_App",tsrvr=args.tserver)
SFApp.run()
sys.exit()
