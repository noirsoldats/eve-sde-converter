# -*- coding: utf-8 -*-
from sqlalchemy import Table, text

def importyaml(connection, metadata, sourcePath, language='en'):
    print("Importing Inventory Names")

    # Get dialect name to determine quoting strategy
    dialect_name = connection.engine.dialect.name

    # PostgreSQL and MSSQL need quoted identifiers for mixed-case tables
    if dialect_name in ('postgresql', 'mssql'):
        quote = '"'
    else:
        quote = ''

    # Aggregate names from various tables via SQL
    print("  Inserting from invTypes")
    connection.execute(text(f'INSERT INTO {quote}invNames{quote} ({quote}itemID{quote}, {quote}itemName{quote}) SELECT {quote}typeID{quote}, {quote}typeName{quote} FROM {quote}invTypes{quote}'))

    print("  Inserting from chrFactions")
    connection.execute(text(f'INSERT INTO {quote}invNames{quote} ({quote}itemID{quote}, {quote}itemName{quote}) SELECT {quote}factionID{quote}, {quote}factionName{quote} FROM {quote}chrFactions{quote}'))

    print("  Inserting from crpNPCCorporations")
    connection.execute(text(f'INSERT INTO {quote}invNames{quote} ({quote}itemID{quote}, {quote}itemName{quote}) SELECT {quote}corporationID{quote}, {quote}corporationName{quote} FROM {quote}crpNPCCorporations{quote}'))

    print("  Inserting from mapRegions")
    connection.execute(text(f'INSERT INTO {quote}invNames{quote} ({quote}itemID{quote}, {quote}itemName{quote}) SELECT {quote}regionID{quote}, {quote}regionName{quote} FROM {quote}mapRegions{quote}'))

    print("  Inserting from mapConstellations")
    connection.execute(text(f'INSERT INTO {quote}invNames{quote} ({quote}itemID{quote}, {quote}itemName{quote}) SELECT {quote}constellationID{quote}, {quote}constellationName{quote} FROM {quote}mapConstellations{quote}'))

    print("  Inserting from mapSolarSystems")
    connection.execute(text(f'INSERT INTO {quote}invNames{quote} ({quote}itemID{quote}, {quote}itemName{quote}) SELECT {quote}solarSystemID{quote}, {quote}solarSystemName{quote} FROM {quote}mapSolarSystems{quote}'))

    print("  Inserting from staStations")
    connection.execute(text(f'INSERT INTO {quote}invNames{quote} ({quote}itemID{quote}, {quote}itemName{quote}) SELECT {quote}stationID{quote}, {quote}stationName{quote} FROM {quote}staStations{quote}'))

    print("  Inserting from mapDenormalize (celestials)")
    # Use database-agnostic string concatenation
    # MySQL uses CONCAT(), MSSQL uses +, SQLite/PostgreSQL use ||
    if dialect_name == 'mysql':
        concat_sql = f"CONCAT(t.{quote}typeName{quote}, ' ', CAST(d.{quote}itemID{quote} AS CHAR))"
    elif dialect_name == 'mssql':
        concat_sql = f"t.{quote}typeName{quote} + ' ' + CAST(d.{quote}itemID{quote} AS VARCHAR)"
    else:  # PostgreSQL, SQLite
        concat_sql = f"t.{quote}typeName{quote} || ' ' || d.{quote}itemID{quote}"

    connection.execute(text(f"""
        INSERT INTO {quote}invNames{quote} ({quote}itemID{quote}, {quote}itemName{quote})
        SELECT d.{quote}itemID{quote}, {concat_sql}
        FROM {quote}mapDenormalize{quote} d
        JOIN {quote}invTypes{quote} t ON d.{quote}typeID{quote} = t.{quote}typeID{quote}
        LEFT JOIN {quote}invNames{quote} n ON d.{quote}itemID{quote} = n.{quote}itemID{quote}
        WHERE n.{quote}itemID{quote} IS NULL
    """))

    print("  Done")
