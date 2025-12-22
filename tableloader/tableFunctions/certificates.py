from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from sqlalchemy import Table
import os

def importyaml(connection, metadata, sourcePath, language='en'):
    print("Importing Certificates")

    targetPath = os.path.join(sourcePath, 'certificates.yaml')

    print(f"  Opening {targetPath}")
    with open(targetPath, 'r', encoding="utf8") as f:
        data = load(f, Loader=Loader)

    crtCertificates = metadata.tables['crtCertificates']
    crtClasses = metadata.tables['crtClasses']
    crtRecommendations = metadata.tables['crtRecommendations']
    crtRelationships = metadata.tables['crtRelationships']
    invGroups = metadata.tables['invGroups']

    print(f"  Processing {len(data)} certificates")

    cert_list = []
    class_list = []
    rec_list = []
    rel_list = []
    processed_classes = set()

    trans = connection.begin()
    try:
        for certID, certData in data.items():
            groupID = certData.get('groupID')
            classID = groupID

            # Handle localized description
            description = certData.get('description', '')
            if isinstance(description, dict):
                description = description.get(language, description.get('en', ''))

            # Handle localized name
            name = certData.get('name', '')
            if isinstance(name, dict):
                name = name.get(language, name.get('en', ''))
            if not name:
                name = f"Certificate {certID}"

            cert_list.append({
                'certificateID': certID,
                'groupID': groupID,
                'classID': classID,
                'grade': 1,
                'name': str(name)[:256],
                'description': str(description)[:500]
            })

            # Handle Class (one per groupID)
            if groupID not in processed_classes:
                try:
                    result = connection.execute(invGroups.select().where(invGroups.c.groupID == groupID)).first()
                    className = result.groupName if result else f"Unknown Group {groupID}"

                    class_list.append({
                        'classID': groupID,
                        'className': className,
                        'description': ""
                    })
                    processed_classes.add(groupID)
                except Exception as e:
                    print(f"  Warning: Failed to lookup group {groupID}: {e}")
            
            # Handle Recommendations
            if 'recommendedFor' in certData:
                for shipTypeID in certData['recommendedFor']:
                    rec_list.append({
                        'shipTypeID': shipTypeID,
                        'certificateID': certID,
                        'recommendationLevel': 1
                    })

            # Handle Skill Relationships
            if 'skillTypes' in certData:
                grade_map = {'basic': 1, 'standard': 2, 'improved': 3, 'advanced': 4, 'elite': 5}
                for skillID, grades in certData['skillTypes'].items():
                    for gradeName, level in grades.items():
                        g_int = grade_map.get(gradeName.lower())
                        if g_int:
                            rel_list.append({
                                'parentID': None,
                                'parentTypeID': skillID,
                                'parentLevel': level,
                                'childID': certID,
                                'grade': g_int
                            })

        # Bulk inserts
        if cert_list:
            connection.execute(crtCertificates.insert(), cert_list)
        if class_list:
            connection.execute(crtClasses.insert(), class_list)
        if rec_list:
            connection.execute(crtRecommendations.insert(), rec_list)
        if rel_list:
            connection.execute(crtRelationships.insert(), rel_list)

        trans.commit()
        print("  Done")

    except Exception as e:
        trans.rollback()
        print(f"  Error: {e}")
        raise
