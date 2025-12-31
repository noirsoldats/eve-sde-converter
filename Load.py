from sqlalchemy import create_engine,Table
import warnings

import sys

warnings.filterwarnings('ignore', '^Unicode type received non-unicode bind param value')


if len(sys.argv)<2:
    print("Load.py destination")
    exit()


database=sys.argv[1]

# Check for --create-stripped flag
create_stripped = False
if '--create-stripped' in sys.argv:
    create_stripped = True
    # Remove the flag from argv to not interfere with language detection
    sys.argv = [arg for arg in sys.argv if arg != '--create-stripped']

if len(sys.argv)==3:
    language=sys.argv[2]
else:
    language='en'

import configparser, os
fileLocation = os.path.dirname(os.path.realpath(__file__))
inifile=fileLocation+'/sdeloader.cfg'
config = configparser.ConfigParser()
config.read(inifile)
destination=config.get('Database',database)
sourcePath=config.get('Files','sourcePath')

from tableloader.tableFunctions import *

print("connecting to DB")

engine = create_engine(destination)
connection = engine.connect()

from tableloader.tables import metadataCreator

schema=None
if database=="postgresschema":
    schema="evesde"

metadata=metadataCreator(schema)

print("Creating Tables (indexes will be created after data load)")

metadata.drop_all(engine,checkfirst=True)

# Store all indexes for later creation
saved_indexes = {}
for table in metadata.sorted_tables:
    if table.indexes:
        # Save the indexes
        saved_indexes[table.name] = list(table.indexes)
        # Temporarily remove indexes from table
        table.indexes.clear()

# Now create tables WITHOUT indexes for faster data loading
# This is especially important for MySQL where indexes slow down inserts dramatically
metadata.create_all(engine, checkfirst=True)

print("Tables created (without indexes)")


factions.importyaml(connection,metadata,sourcePath,language)
ancestries.importyaml(connection,metadata,sourcePath,language)
bloodlines.importyaml(connection,metadata,sourcePath,language)
npccorporations.importyaml(connection,metadata,sourcePath,language)
npcDivisions.importyaml(connection,metadata,sourcePath,language)
characterAttributes.importyaml(connection,metadata,sourcePath,language)
agents.importyaml(connection,metadata,sourcePath,language)
typeMaterials.importyaml(connection,metadata,sourcePath,language)
dogmaTypes.importyaml(connection,metadata,sourcePath,language)
dogmaEffects.importyaml(connection,metadata,sourcePath,language)
dogmaAttributes.importyaml(connection,metadata,sourcePath,language)
dogmaAttributeCategories.importyaml(connection,metadata,sourcePath,language)
blueprints.importyaml(connection,metadata,sourcePath)
marketGroups.importyaml(connection,metadata,sourcePath,language)
metaGroups.importyaml(connection,metadata,sourcePath,language)
controlTowerResources.importyaml(connection,metadata,sourcePath,language)
categories.importyaml(connection,metadata,sourcePath,language)
graphics.importyaml(connection,metadata,sourcePath)
groups.importyaml(connection,metadata,sourcePath,language)
# Certificates needs invGroups
certificates.importyaml(connection,metadata,sourcePath,language)

icons.importyaml(connection,metadata,sourcePath)
skins.importyaml(connection,metadata,sourcePath)
types.importyaml(connection,metadata,sourcePath,language)
typeBonus.importyaml(connection,metadata,sourcePath,language)
# Masteries needs Certificates and Types (implied typeID existence, though not FK enforced strictly)
masteries.importyaml(connection,metadata,sourcePath,language)

eveUnits.importyaml(connection,metadata,sourcePath,language)
planetary.importyaml(connection,metadata,sourcePath,language)
# bsdTables.importyaml(connection,metadata,sourcePath)
volumes.importVolumes(connection,metadata,sourcePath)
universe.importyaml(connection,metadata,sourcePath,language)
universe.buildJumps(connection,metadata)
stations.importyaml(connection,metadata,sourcePath,language)
universe.fixStationNames(connection,metadata)
invNames.importyaml(connection,metadata,sourcePath,language)
invItems.importyaml(connection,metadata,sourcePath,language)
rigAffectedProductGroups.importRigMappings(connection,metadata)

# Create indexes AFTER all data is loaded for significantly better performance
print("\n" + "="*60)
print("Creating Indexes (this may take several minutes)...")
print("="*60)

import time
start_time = time.time()
index_count = 0
error_count = 0

# Create indexes from the saved index definitions
for table_name, indexes in saved_indexes.items():
    if indexes:
        print(f"\nIndexing table: {table_name}")
        for index in indexes:
            try:
                index.create(engine)
                index_count += 1
                print(f"  ✓ Created index: {index.name}")
            except Exception as e:
                error_count += 1
                # Some indexes might fail for valid reasons
                print(f"  ⚠ Warning: Could not create index {index.name}: {e}")

elapsed_time = time.time() - start_time
print("\n" + "="*60)
print(f"Index creation complete!")
print(f"  Indexes created: {index_count}")
if error_count > 0:
    print(f"  Warnings: {error_count}")
print(f"  Time taken: {elapsed_time:.2f} seconds")
print("="*60 + "\n")

# Close connections before file operations
connection.close()
engine.dispose()

def create_stripped_database(source_db_path='eve.db', dest_db_path='eve-stripped.db'):
    """
    Create a stripped-down version of the database containing only essential tables.

    Uses copy + DROP approach for efficiency and accuracy.
    """
    import shutil
    import sqlite3

    # Tables to keep in stripped database
    TABLES_TO_KEEP = {
        'invTypes', 'invGroups', 'invCategories', 'invMetaTypes', 'invVolumes',
        'industryActivityMaterials', 'industryActivityProducts', 'industryActivity',
        'industryActivityProbabilities', 'industryActivitySkills',
        'dgmTypeAttributes', 'dgmAttributeTypes', 'dgmTypeEffects', 'dgmEffects',
        'dgmAttributeCategories', 'dgmExpressions',
        'mapRegions', 'mapSolarSystems', 'staStations',
        'invTypeMaterials', 'invMarketGroups', 'industryBlueprints',
        'planetSchematics', 'planetSchematicsPinMap', 'planetSchematicsTypeMap',
        'invTypeReactions',
        'rigAffectedProductGroups', 'rigIndustryModifierSources'
    }

    # Check source exists
    if not os.path.exists(source_db_path):
        print(f"Error: Source database not found: {source_db_path}")
        return False

    # Warn if destination exists
    if os.path.exists(dest_db_path):
        print(f"Warning: {dest_db_path} already exists and will be overwritten")

    try:
        print(f"\nCreating stripped database: {dest_db_path}")

        # Step 1: Copy the entire database
        print(f"  Copying {source_db_path}...")
        shutil.copy2(source_db_path, dest_db_path)

        # Step 2: Connect and get all tables
        conn = sqlite3.connect(dest_db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        all_tables = [row[0] for row in cursor.fetchall()]

        # Step 3: Drop unwanted tables
        tables_to_drop = [t for t in all_tables if t not in TABLES_TO_KEEP]

        print(f"  Removing {len(tables_to_drop)} unnecessary tables...")
        for table in tables_to_drop:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")

        # Step 4: VACUUM to reclaim space
        print("  Optimizing database (VACUUM)...")
        conn.commit()
        cursor.execute("VACUUM")

        conn.close()

        # Step 5: Report results
        original_size = os.path.getsize(source_db_path) / (1024*1024)
        stripped_size = os.path.getsize(dest_db_path) / (1024*1024)

        print(f"\n  Stripped database created successfully!")
        print(f"  Original size: {original_size:.2f} MB")
        print(f"  Stripped size: {stripped_size:.2f} MB")
        print(f"  Space saved: {original_size - stripped_size:.2f} MB ({(1-stripped_size/original_size)*100:.1f}%)")
        print(f"  Tables kept: {len(TABLES_TO_KEEP)}")

        # Validation
        conn = sqlite3.connect(dest_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        final_tables = set(row[0] for row in cursor.fetchall())
        conn.close()

        if final_tables == TABLES_TO_KEEP:
            print(f"  Validation: All {len(TABLES_TO_KEEP)} expected tables present")
        else:
            print(f"  Warning: Table mismatch detected")
            missing = TABLES_TO_KEEP - final_tables
            extra = final_tables - TABLES_TO_KEEP
            if missing:
                print(f"    Missing tables: {missing}")
            if extra:
                print(f"    Extra tables: {extra}")

        return True

    except Exception as e:
        print(f"Error creating stripped database: {e}")
        # Clean up partial file on error
        if os.path.exists(dest_db_path):
            try:
                os.remove(dest_db_path)
                print(f"  Cleaned up partial file: {dest_db_path}")
            except:
                pass
        return False

# Create stripped database if requested
if create_stripped:
    # Only create stripped DB for SQLite databases
    if database == 'sqlite':
        create_stripped_database('eve.db', 'eve-stripped.db')
    else:
        print("\nWarning: Stripped database creation is only supported for SQLite databases")
        print(f"  Current database type: {database}")

# invTypes, invGroups, invCategories, invMetaTypes, invVolumes, industryActivityMaterials, industryActivityProducts, industryActivity, industryActivityProbabilities, industryActivitySkills, dgmTypeAttributes, dgmAttributeTypes, mapRegions, mapSolarSystems, staStations, invTypeMaterials, invMarketGroups, industryBlueprints, planetSchematics, planetSchematicsPinMap, planetSchematicsTypeMap, invTypeReactions