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
    print("Importing marketGroups")
    planetSchematics = Table('planetSchematics',metadata)
    planetSchematicsPinMap = Table('planetSchematicsPinMap',metadata)
    planetSchematicsTypeMap = Table('planetSchematicsTypeMap',metadata)
    
    print("opening Yaml")
        
    trans = connection.begin()
    with open(os.path.join(sourcePath,'planetSchematics.yaml'),'r', encoding='utf-8') as yamlstream:
        print("importing")
        schematics=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for schematicid in schematics:
            connection.execute(planetSchematics.insert().values(
                            schematicID=schematicid,
                            schematicName=schematics[schematicid].get('name',{}).get(language,''),
                            cycleTime=schematics[schematicid].get('cycleTime'),
            ))
            for pin in schematics[schematicid].get('pins',{}):
                connection.execute(planetSchematicsPinMap.insert().values(
                                schematicID=schematicid,
                                pinTypeID=pin,
                ))

            for typeid in schematics[schematicid].get('types',{}):
                connection.execute(planetSchematicsTypeMap.insert().values(
                                schematicID=schematicid,
                                typeID=typeid,
                                quantity=schematics[schematicid]['types'][typeid].get('quantity',0),
                                isInput=schematics[schematicid]['types'][typeid].get('isInput',False),
                ))
 
    trans.commit()
