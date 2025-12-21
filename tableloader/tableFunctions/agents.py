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

def importyaml(connection,metadata,sourcePath,language='en'):
    agtAgents = Table('agtAgents',metadata)
    agtAgentsInSpace = Table('agtAgentsInSpace',metadata)
    agtResearchAgents = Table ('agtResearchAgents',metadata)
    agtAgentTypes = Table('agtAgentTypes',metadata)
    print("Importing Agents")
    print("opening Yaml")
    with open(os.path.join(sourcePath,'npcCharacters.yaml'),'r', encoding='utf-8') as yamlstream:
        trans = connection.begin()
        npcCharacters=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
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
    trans.commit()
    print("Importing AgentsInSpace")
    print("opening Yaml")
    with open(os.path.join(sourcePath,'agentsInSpace.yaml'),'r', encoding='utf-8') as yamlstream:
        trans = connection.begin()
        agents=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for agentid in agents:
            connection.execute(agtAgentsInSpace.insert().values(
                            agentID=agentid,
                            dungeonID=agents[agentid].get('dungeonID',None),
                            solarSystemID=agents[agentid].get('solarSystemID',None),
                            spawnPointID=agents[agentid].get('spawnPointID',None),
                            typeID=agents[agentid].get('typeID',None),
                              ))
    trans.commit()
    print("Importing research agents")
    print("opening Yaml")
    with open(os.path.join(sourcePath,'npcCharacters.yaml'),'r', encoding='utf-8') as yamlstream:
        trans = connection.begin()
        npcCharacters=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
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

    print("Importing agent types")
    print("opening Yaml")
    with open(os.path.join(sourcePath,'agentTypes.yaml'),'r', encoding='utf-8') as yamlstream:
        trans = connection.begin()
        agentTypes=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for agentTypeID in agentTypes:
            connection.execute(agtAgentTypes.insert().values(
                agentTypeID=agentTypeID,
                agentType=agentTypes[agentTypeID].get('name',None),
              ))
    trans.commit()