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
    eveIcons = Table('eveIcons',metadata)
    print("Importing Icons")
    print("Opening Yaml")
    with open(os.path.join(sourcePath,'icons.yaml'),'r', encoding='utf-8') as yamlstream:
        trans = connection.begin()
        icons=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for icon in icons:
            connection.execute(eveIcons.insert().values(
                            iconID=icon,
                            iconFile=icons[icon].get('iconFile',''),
                            description=''))  # Field removed from SDE
    trans.commit()