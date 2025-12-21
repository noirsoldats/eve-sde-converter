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
    print("Importing character Ancestries")
    chrAncestries = Table('chrAncestries',metadata)
    
    print("opening Yaml")
        
    trans = connection.begin()
    with open(os.path.join(sourcePath,'ancestries.yaml'),'r', encoding='utf-8') as yamlstream:
        print("importing")
        characterancestries=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for ancestryid in characterancestries:
            connection.execute(chrAncestries.insert().values(
                            ancestryID=ancestryid,
                            ancestryName=characterancestries[ancestryid].get('name',{}).get(language,''),
                            description=characterancestries[ancestryid].get('description',{}).get(language,''),
                            iconID=characterancestries[ancestryid].get('iconID'),
                            bloodlineID=characterancestries[ancestryid].get('bloodlineID'),
                            charisma=characterancestries[ancestryid].get('charisma'),
                            intelligence=characterancestries[ancestryid].get('intelligence'),
                            memory=characterancestries[ancestryid].get('memory'),
                            perception=characterancestries[ancestryid].get('perception'),
                            willpower=characterancestries[ancestryid].get('willpower'),
                            shortDescription=characterancestries[ancestryid].get('shortDescription'),
                              )) 
    trans.commit()
