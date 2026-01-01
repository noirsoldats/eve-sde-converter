# -*- coding: utf-8 -*-
from sqlalchemy import Table, text

def importyaml(connection, metadata, sourcePath, language='en'):
    print("Importing Inventory Items")

    # Get dialect name to determine quoting strategy
    dialect_name = connection.engine.dialect.name

    # PostgreSQL and MSSQL need quoted identifiers for mixed-case tables
    if dialect_name in ('postgresql', 'mssql'):
        quote = '"'
    else:
        quote = ''

    print("  Inserting from mapDenormalize (celestials)")
    connection.execute(text(f"""
        INSERT INTO {quote}invItems{quote} ({quote}itemID{quote}, {quote}typeID{quote}, {quote}ownerID{quote}, {quote}locationID{quote}, {quote}flagID{quote}, {quote}quantity{quote})
        SELECT {quote}itemID{quote}, {quote}typeID{quote}, 1, {quote}solarSystemID{quote}, 0, 1
        FROM {quote}mapDenormalize{quote}
        WHERE {quote}solarSystemID{quote} IS NOT NULL
    """))

    print("  Inserting from staStations")
    connection.execute(text(f"""
        INSERT INTO {quote}invItems{quote} ({quote}itemID{quote}, {quote}typeID{quote}, {quote}ownerID{quote}, {quote}locationID{quote}, {quote}flagID{quote}, {quote}quantity{quote})
        SELECT {quote}stationID{quote}, {quote}stationTypeID{quote}, {quote}corporationID{quote}, {quote}solarSystemID{quote}, 0, 1
        FROM {quote}staStations{quote}
    """))

    print("  Done")
