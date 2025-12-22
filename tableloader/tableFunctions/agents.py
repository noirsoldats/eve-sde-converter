# -*- coding: utf-8 -*-
from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

import os
from sqlalchemy import Table

def importyaml(connection,metadata,sourcePath,language='en'):
    agtAgents = Table('agtAgents',metadata)
    agtAgentsInSpace = Table('agtAgentsInSpace',metadata)
    agtResearchAgents = Table ('agtResearchAgents',metadata)
    agtAgentTypes = Table('agtAgentTypes',metadata)
    invNames = Table('invNames',metadata)

    def find_file(filename):
        # Helper to check standard locations
        candidates = [
            os.path.join(sourcePath, filename),
            os.path.join(sourcePath, 'fsd', filename),
            os.path.join(sourcePath, 'sde', 'fsd', filename)
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        print(f"ERROR: Could not find {filename} in {sourcePath} or subdirectories.")
        return None

    print("Importing Agents")
    targetPath = find_file('npcCharacters.yaml')
    if not targetPath:
        targetPath = find_file('agents.yaml')

    if targetPath:
        print(f"  Opening {targetPath}")
        with open(targetPath,'r', encoding='utf-8') as yamlstream:
            trans = connection.begin()
            npcCharacters=load(yamlstream,Loader=SafeLoader)
            print(f"  Processing {len(npcCharacters)} characters")
            for characterID in npcCharacters:
                # Only process NPCs that have agent data
                if 'agent' in npcCharacters[characterID]:
                    agent_data = npcCharacters[characterID]['agent']
                    connection.execute(agtAgents.insert().values(
                                    agentID=characterID,
                                    divisionID=agent_data.get('divisionID',None),
                                    corporationID=npcCharacters[characterID].get('corporationID',None),
                                    isLocator=agent_data.get('isLocator',None),
                                    level=agent_data.get('level',None),
                                    locationID=npcCharacters[characterID].get('locationID',None),
                                    agentTypeID=agent_data.get('agentTypeID',None),
                                      ))
                    # Insert into invNames
                    if 'name' in npcCharacters[characterID]:
                        raw_name = npcCharacters[characterID]['name']
                        name_str = raw_name.get(language, raw_name.get('en', '')) if isinstance(raw_name, dict) else raw_name
                        
                        connection.execute(invNames.insert().values(
                            itemID=characterID,
                            itemName=name_str
                        ))
        trans.commit()
        print("  Done")

    print("Importing AgentsInSpace")
    targetPath = find_file('agentsInSpace.yaml')
    if targetPath:
        print(f"  Opening {targetPath}")
        with open(targetPath,'r', encoding='utf-8') as yamlstream:
            trans = connection.begin()
            agents=load(yamlstream,Loader=SafeLoader)
            print(f"  Processing {len(agents)} agents")
            for agentid in agents:
                connection.execute(agtAgentsInSpace.insert().values(
                                agentID=agentid,
                                dungeonID=agents[agentid].get('dungeonID',None),
                                solarSystemID=agents[agentid].get('solarSystemID',None),
                                spawnPointID=agents[agentid].get('spawnPointID',None),
                                typeID=agents[agentid].get('typeID',None),
                                  ))
        trans.commit()
        print("  Done")

    print("Importing Research Agents")
    targetPath = find_file('npcCharacters.yaml')
    if targetPath:
        print(f"  Opening {targetPath}")
        with open(targetPath,'r', encoding='utf-8') as yamlstream:
            trans = connection.begin()
            npcCharacters=load(yamlstream,Loader=SafeLoader)
            print(f"  Processing {len(npcCharacters)} characters")
            for characterID in npcCharacters:
                # Filter for research agents (agentTypeID == 4) with skills
                if 'agent' in npcCharacters[characterID]:
                    if npcCharacters[characterID]['agent'].get('agentTypeID') == 4:
                        if 'skills' in npcCharacters[characterID]:
                            for skill in npcCharacters[characterID]['skills']:
                                connection.execute(agtResearchAgents.insert().values(
                                                agentID=characterID,
                                                typeID=skill.get('typeID',None),
                                              ))
        trans.commit()
        print("  Done")

    print("Importing Agent Types")
    targetPath = find_file('agentTypes.yaml')
    if targetPath:
        print(f"  Opening {targetPath}")
        with open(targetPath,'r', encoding='utf-8') as yamlstream:
            trans = connection.begin()
            agentTypes=load(yamlstream,Loader=SafeLoader)
            print(f"  Processing {len(agentTypes)} agent types")
            for agentTypeID in agentTypes:
                connection.execute(agtAgentTypes.insert().values(
                    agentTypeID=agentTypeID,
                    agentType=agentTypes[agentTypeID].get('name',None),
                  ))
        trans.commit()
        print("  Done")