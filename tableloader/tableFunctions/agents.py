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

            # Build bulk insert lists
            agent_rows = []
            name_rows = []

            for characterID in npcCharacters:
                # Only process NPCs that have agent data
                if 'agent' in npcCharacters[characterID]:
                    agent_data = npcCharacters[characterID]['agent']
                    agent_rows.append({
                        'agentID': characterID,
                        'divisionID': agent_data.get('divisionID',None),
                        'corporationID': npcCharacters[characterID].get('corporationID',None),
                        'isLocator': agent_data.get('isLocator',None),
                        'level': agent_data.get('level',None),
                        'locationID': npcCharacters[characterID].get('locationID',None),
                        'agentTypeID': agent_data.get('agentTypeID',None)
                    })

                    # Insert into invNames
                    if 'name' in npcCharacters[characterID]:
                        raw_name = npcCharacters[characterID]['name']
                        name_str = raw_name.get(language, raw_name.get('en', '')) if isinstance(raw_name, dict) else raw_name

                        name_rows.append({
                            'itemID': characterID,
                            'itemName': name_str
                        })

            # BULK INSERTS
            if agent_rows:
                connection.execute(agtAgents.insert(), agent_rows)
                print(f"  Inserted {len(agent_rows)} agents")

            if name_rows:
                connection.execute(invNames.insert(), name_rows)
                print(f"  Inserted {len(name_rows)} agent names")

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

            # Build bulk insert list
            space_rows = []

            for agentid in agents:
                space_rows.append({
                    'agentID': agentid,
                    'dungeonID': agents[agentid].get('dungeonID',None),
                    'solarSystemID': agents[agentid].get('solarSystemID',None),
                    'spawnPointID': agents[agentid].get('spawnPointID',None),
                    'typeID': agents[agentid].get('typeID',None)
                })

            # BULK INSERT
            if space_rows:
                connection.execute(agtAgentsInSpace.insert(), space_rows)
                print(f"  Inserted {len(space_rows)} agents in space")

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

            # Build bulk insert list
            research_rows = []

            for characterID in npcCharacters:
                # Filter for research agents (agentTypeID == 4) with skills
                if 'agent' in npcCharacters[characterID]:
                    if npcCharacters[characterID]['agent'].get('agentTypeID') == 4:
                        if 'skills' in npcCharacters[characterID]:
                            for skill in npcCharacters[characterID]['skills']:
                                research_rows.append({
                                    'agentID': characterID,
                                    'typeID': skill.get('typeID',None)
                                })

            # BULK INSERT
            if research_rows:
                connection.execute(agtResearchAgents.insert(), research_rows)
                print(f"  Inserted {len(research_rows)} research agents")

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

            # Build bulk insert list
            type_rows = []

            for agentTypeID in agentTypes:
                type_rows.append({
                    'agentTypeID': agentTypeID,
                    'agentType': agentTypes[agentTypeID].get('name',None)
                })

            # BULK INSERT
            if type_rows:
                connection.execute(agtAgentTypes.insert(), type_rows)
                print(f"  Inserted {len(type_rows)} agent types")

        trans.commit()
        print("  Done")