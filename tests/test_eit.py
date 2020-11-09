'''
Created on 2020-11-09

@author: wf
'''
import unittest
import os
import getpass
from eit.eitparser import EitList


class TestEitParser(unittest.TestCase):
    '''
    test the standalone EIT Parser
    '''


    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testEitParser(self):
        '''
        test the Event Information Table parser
        '''
        if getpass.getuser()=="wfs":
            home = os.path.expanduser("~")
            eitdir= home+"/movies/eit"
        else:
            eitdir=os.path.dirname(os.path.abspath(__file__))
        EitList.readeit(eitdir,debug=False)
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()