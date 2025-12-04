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
    print("Importing character factions")
    chrFactions = Table('chrFactions',metadata)
    chrRaces = Table('chrRaces',metadata)
    
    print("opening Yaml")
        
    trans = connection.begin()
    with open(os.path.join(sourcePath,'factions.yaml'),'r') as yamlstream:
        print("importing")
        characterfactions=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for factionid in characterfactions:
            connection.execute(chrFactions.insert().values(
                            factionID=factionid,
                            factionName=characterfactions[factionid].get('name',{}).get(language,''),
                            description=characterfactions[factionid].get('description',{}).get(language,''),
                            iconID=characterfactions[factionid].get('iconID'),
                            raceIDs=characterfactions[factionid].get('memberRaces',[0])[0],
                            solarSystemID=characterfactions[factionid].get('solarSystemID'),
                            corporationID=characterfactions[factionid].get('corporationID'),
                            sizeFactor=characterfactions[factionid].get('sizeFactor'),
                            militiaCorporationID=characterfactions[factionid].get('militiaCorporationID'),
                      ))
    trans.commit()

    trans = connection.begin()
    with open(os.path.join(sourcePath,'races.yaml'),'r') as yamlstream:
        print("importing")
        characterRaces=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for raceID in characterRaces:
            connection.execute(chrRaces.insert().values(
                            raceID=raceID,
                            raceName=characterRaces[raceID].get('name',{}).get(language,''),
                            description=characterRaces[raceID].get('description',{}).get(language,''),
                            iconID=characterRaces[raceID].get('iconID'),
                            # Duplicate description for backwards compatability.
                            shortDescription=characterRaces[raceID].get('description',{}).get(language,''),
                      ))
    trans.commit()
