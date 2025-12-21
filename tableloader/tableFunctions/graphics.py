# -*- coding: utf-8 -*-
from yaml import load, dump
try:
	from yaml import CSafeLoader as SafeLoader
	print("Using CSafeLoader")
except ImportError:
	from yaml import SafeLoader
	print("Using Python SafeLoader")

import os
import sys
from sqlalchemy import Table

def importyaml(connection,metadata,sourcePath):
    eveGraphics = Table('eveGraphics',metadata)
    print("Importing Graphics")
    print("opening Yaml")
    with open(os.path.join(sourcePath,'graphics.yaml'),'r', encoding='utf-8') as yamlstream:
        print("importing")
        trans = connection.begin()
        graphics=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for graphic in graphics:
            connection.execute(eveGraphics.insert().values(
                            graphicID=graphic,
                            sofFactionName=graphics[graphic].get('sofFactionName',''),
                            graphicFile=graphics[graphic].get('graphicFile',''),
                            sofHullName=graphics[graphic].get('sofHullName',''),
                            sofRaceName=graphics[graphic].get('sofRaceName',''),
                            description=''))  # Field removed from SDE
    trans.commit()
