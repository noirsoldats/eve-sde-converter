# -*- coding: utf-8 -*-
import sys
import os
from sqlalchemy import Table

from yaml import load
try:
	from yaml import CSafeLoader as SafeLoader
	print("Using CSafeLoader")
except ImportError:
	from yaml import SafeLoader
	print("Using Python SafeLoader")


def importyaml(connection,metadata,sourcePath,language='en'):
    print("Importing character Attributes")
    chrAttributes = Table('chrAttributes',metadata)
    
    print("opening Yaml")
        
    trans = connection.begin()
    with open(os.path.join(sourcePath,'characterAttributes.yaml'),'r', encoding='utf-8') as yamlstream:
        print("importing")
        characterattributes=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for attributeid in characterattributes:
            connection.execute(chrAttributes.insert().values(
                            attributeID=attributeid,
                            attributeName=characterattributes[attributeid].get('name',{}).get(language,''),
                            description=characterattributes[attributeid].get('description',''),
                            iconID=characterattributes[attributeid].get('iconID',None),
                            notes=characterattributes[attributeid].get('notes',''),
                            shortDescription=characterattributes[attributeid].get('shortDescription',''),
                              )) 
    trans.commit()
