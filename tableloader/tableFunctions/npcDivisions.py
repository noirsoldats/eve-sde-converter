import os
from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

def importyaml(connection, metadata, sourcePath, language='en'):
    print("Importing NPC Divisions")

    # Check multiple possible paths
    targetPath = os.path.join(sourcePath, 'npcCorporationDivisions.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'npcCorporationDivisions.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'npcCorporationDivisions.yaml')

    if not os.path.exists(targetPath):
        print("  Warning: npcCorporationDivisions.yaml not found")
        return

    print(f"  Opening {targetPath}")
    frames = load(open(targetPath, 'r', encoding="utf8"), Loader=SafeLoader)

    crpNPCDivisions = metadata.tables['crpNPCDivisions']

    print(f"  Processing {len(frames)} divisions")

    trans = connection.begin()
    try:
        for id, data in frames.items():
            # Handle localized name
            if 'name' in data and language in data['name']:
                divisionName = data['name'][language]
            elif 'name' in data and 'en' in data['name']:
                divisionName = data['name']['en']
            elif 'displayName' in data:
                divisionName = data['displayName']
            else:
                divisionName = "Unknown Division"

            # Handle localized leader title
            if 'leaderTypeName' in data and language in data['leaderTypeName']:
                leaderType = data['leaderTypeName'][language]
            elif 'leaderTypeName' in data and 'en' in data['leaderTypeName']:
                leaderType = data['leaderTypeName']['en']
            else:
                leaderType = None

            # Handle localized description
            description = ''
            if 'description' in data:
                if isinstance(data['description'], dict):
                    description = data['description'].get(language, data['description'].get('en', ''))
                else:
                    description = str(data['description'])

            connection.execute(crpNPCDivisions.insert().values(
                divisionID=id,
                divisionName=divisionName,
                description=description,
                leaderType=leaderType
            ))
        trans.commit()
        print("  Done")
    except Exception as e:
        trans.rollback()
        print(f"  Error: {e}")
        raise
