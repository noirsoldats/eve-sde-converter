from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from sqlalchemy import Table
import os

def importyaml(connection, metadata, sourcePath, language='en'):
    print("Importing Masteries")

    targetPath = os.path.join(sourcePath, 'masteries.yaml')

    print(f"  Opening {targetPath}")
    with open(targetPath, 'r', encoding="utf8") as f:
        data = load(f, Loader=Loader)

    dgmMasteries = metadata.tables['dgmMasteries']
    dgmTypeMasteries = metadata.tables['dgmTypeMasteries']

    print(f"  Processing {len(data)} ship types")

    type_mastery_list = []
    mastery_list = []
    masteryID_counter = 1

    trans = connection.begin()
    try:
        # Data format: typeID -> { grade: [certID, certID...], ... }
        for typeID, grades in data.items():
            for grade, certIDs in grades.items():
                for certID in certIDs:
                    currentMasteryID = masteryID_counter
                    masteryID_counter += 1

                    mastery_list.append({
                        'masteryID': currentMasteryID,
                        'certificateID': certID,
                        'grade': grade
                    })

                    type_mastery_list.append({
                        'typeID': typeID,
                        'masteryID': currentMasteryID
                    })

        print(f"  Inserting {len(mastery_list)} mastery rules")

        if mastery_list:
            connection.execute(dgmMasteries.insert(), mastery_list)
        if type_mastery_list:
            connection.execute(dgmTypeMasteries.insert(), type_mastery_list)

        trans.commit()
        print("  Done")

    except Exception as e:
        trans.rollback()
        print(f"  Error: {e}")
        raise
