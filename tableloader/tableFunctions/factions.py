# -*- coding: utf-8 -*-
import os
from sqlalchemy import Table

from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader


def importyaml(connection,metadata,sourcePath,language='en'):
    print("Importing Factions")
    chrFactions = Table('chrFactions',metadata)
    chrRaces = Table('chrRaces',metadata)

    targetPath = os.path.join(sourcePath, 'factions.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'factions.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'factions.yaml')

    print(f"  Opening {targetPath}")
        
    trans = connection.begin()
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        characterfactions=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(characterfactions)} factions")

        # Build bulk insert list
        faction_rows = []

        for factionid in characterfactions:
            faction_rows.append({
                'factionID': factionid,
                'factionName': characterfactions[factionid].get('name',{}).get(language,''),
                'description': characterfactions[factionid].get('description',{}).get(language,''),
                'iconID': characterfactions[factionid].get('iconID'),
                'raceIDs': characterfactions[factionid].get('memberRaces',[0])[0],
                'solarSystemID': characterfactions[factionid].get('solarSystemID'),
                'corporationID': characterfactions[factionid].get('corporationID'),
                'sizeFactor': characterfactions[factionid].get('sizeFactor'),
                'militiaCorporationID': characterfactions[factionid].get('militiaCorporationID')
            })

        # BULK INSERT
        if faction_rows:
            connection.execute(chrFactions.insert(), faction_rows)
            print(f"  Inserted {len(faction_rows)} factions")

    trans.commit()
    print("  Done")

    print("Importing Races")
    targetPath = os.path.join(sourcePath, 'races.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'races.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'races.yaml')

    print(f"  Opening {targetPath}")

    trans = connection.begin()
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        characterRaces=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(characterRaces)} races")

        # Build bulk insert list
        race_rows = []

        for raceID in characterRaces:
            race_rows.append({
                'raceID': raceID,
                'raceName': characterRaces[raceID].get('name',{}).get(language,''),
                'description': characterRaces[raceID].get('description',{}).get(language,''),
                'iconID': characterRaces[raceID].get('iconID'),
                'shortDescription': characterRaces[raceID].get('description',{}).get(language,'')
            })

        # BULK INSERT
        if race_rows:
            connection.execute(chrRaces.insert(), race_rows)
            print(f"  Inserted {len(race_rows)} races")

    trans.commit()
    print("  Done")
