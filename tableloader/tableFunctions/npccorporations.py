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
    print("Importing NPC corporations")
    crpNPCCorporations = Table('crpNPCCorporations',metadata)
    invNames =  Table('invNames', metadata) 
    print("opening Yaml")
        
    trans = connection.begin()
    with open(os.path.join(sourcePath,'npcCorporations.yaml'),'r', encoding='utf-8') as yamlstream:
        print("importing")
        npccorps=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for corpid in npccorps:
            connection.execute(crpNPCCorporations.insert().values(
                            corporationID=corpid,
                            corporationName=npccorps[corpid].get('name', {}).get(language, ''),
                            description=npccorps[corpid].get('description',{}).get(language,''),
                            iconID=npccorps[corpid].get('iconID'),
                            enemyID=npccorps[corpid].get('enemyID'),
                            factionID=npccorps[corpid].get('factionID'),
                            friendID=npccorps[corpid].get('friendID'),
                            initialPrice=npccorps[corpid].get('initialPrice'),
                            minSecurity=npccorps[corpid].get('minSecurity'),
                            publicShares=npccorps[corpid].get('shares'),
                            size=npccorps[corpid].get('size'),
                            solarSystemID=npccorps[corpid].get('solarSystemID'),
                            extent=npccorps[corpid].get('extent'),
                      ))
#            connection.execute(invNames.insert(),
#                           itemID=corpid,
#                           itemName=npccorps[corpid].get('name',{}).get(language,'').decode('utf-8'),
#                          )
    trans.commit()
