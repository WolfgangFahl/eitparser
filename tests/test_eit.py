'''
Created on 2020-11-09

@author: wf
'''
import unittest
import os
from eit.eitparser import EitList

class TestEitParser(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def testEitParser(self):
        '''
        test the Event Information Table parser
        '''
        home = os.path.expanduser("~")
        eitdir= home+"/movies/eit"
        EitList.readeit(eitdir)
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()