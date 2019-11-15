# File Geodatabase to PostGIS converter (fgdb2postgis)

The aim of this tool is to convert an ESRI file Geodatabase to a PostGIS database maintaining data, domains, subtypes and relationships.

- [File Geodatabase to PostGIS converter (fgdb2postgis)](#file-geodatabase-to-postgis-converter-fgdb2postgis)
  - [Description](#description)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Materialized views](#materialized-views)
  - [Credits](#credits)
  - [License](#license)

## Description

The tool will copy over the feature classes as postgis layers and the tables as standard tables. The domains and subtypes will be converted to PostgreSQL lookup tables.

The tool will then create all necessary indexes and constraints to maintain the required relates between the layers, tables and lookup tables.

The tool creates materialized views of the tables including descriptions of the lookup tables suitable for  web publishing.

To recreate the same experience of the domains and subtypes in QGIS using the output data, please install the plugin `Data Manager <https://github.com/cartologic/qgis-datamanager-plugin>`_.

Now you can have domain experience in QGIS that is stored in the database and not in the QGIS project.


## Installation

This library requires GDAL/OGR libraries and ESRI ArcGIS to be installed in the system.

This package should be installed only on windows systems because of ArcGIS (Arcpy) limitation.

This tool has been  tested with PostgreSQL 11 ,  PostGIS 2.5, Arcgis Desktop 10.6.1 and  gdal 2.4.0


Install required packages::

```bash
    pip install psycopg2>=2.6.2
    pip install pyyaml>=3.12
    pip install archook==1.1.0
```

Install fgdb2postgis::

```bash
git clone https://github.com/dersteppenwolf/fgdb2postgis.git
cd fgdb2postgis
python setup.py install
```

__Note:__

  * This tool requires to have GDAL/OGR libraries and ArcGIS 10.3 or later installed.
  * ESRI Python packages usually under C:\Python27\ArcGIS10.* might not have pip included make sure to

    * Install pip if not already installed
    * Setup ESRI python and GDAL/OGR in windows path environment variable

## Usage


```bash

usage: fgdb2postgis [-h] [-v] [-yml] [--fgdb [FGDB]] [--database [DATABASE]]
                    [--host [HOST]] [--port [PORT]] [--user [USER]]
                    [--password [PASSWORD]] [--include_empty [INCLUDE_EMPTY]]
                    [--lookup_tables_schema [LOOKUP_TABLES_SCHEMA]]
                    [--a_srs [A_SRS]] [--t_srs [T_SRS]]

Convert a Filegeodatabase to Postgis.

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         Program version
  -yml, --yml           Create .yml and exit
  --fgdb [FGDB]         Name of the filegeodatabase for conversion
  --database [DATABASE]
                        Name of the postgis database to be created for
                        conversion
  --host [HOST]         Database host
  --port [PORT]         Postgresql port
  --user [USER]         database user
  --password [PASSWORD]
                        database password
  --include_empty [INCLUDE_EMPTY]
                        Include empty tables and features. Default False
  --lookup_tables_schema [LOOKUP_TABLES_SCHEMA]
                        Name of the schema for lookup tables.
                        Default:lookup_tables
  --a_srs [A_SRS]       Assign an output SRS.
  --t_srs [T_SRS]       Reproject/transform to this SRS on output.
```

Command line options::

Show help: 

```bash
    fgdb2postgis -h
```

Generate the yml file and exit: 

```bash
  fgdb2postgis -yml --fgdb sample.gdb
```

Convert fgdb: 

```bash
    fgdb2postgis --fgdb mygdb.gdb  --database=migratetdb  --host=localhost  --port=5432  --user=user_migrate  --password=user_migrate --a_srs=EPSG:4686   --t_srs=EPSG:4686 --include_empty=False --lookup_tables_schema=mylookuptableschema
```



Create a yaml file mapping the file geodatabase's feature datasets, 
feature classes and tables to postgresql's schemas. It is required that the yaml file have the same 
name with the file geodatabase with the extension .yaml

Example::

    filegdb: sample.gdb
       yaml: sample.gdb.yaml

.. note::
  The Yaml file should be located in the same folder with the file geodatabase.
  If run without the yaml file will convert the full database and load it into the public schema.
  The schema lookup_tables will always be created regardless of the yaml file.

Yaml file example::

```yaml
    Schemas:
      - Administrative
      - Epidemiology
      - Radioactivity
      - Seismic
    FeatureDatasets:
      Epidemiology:
        - Epidemiology
      Radioactivity:
        - Radioactivity
      Seismic:
        - Seismic
    FeatureClasses:
      Administrative:
        - sectors
        - governorates
        - sub_sectors
    Tables:
      Epidemiology:
        - EpidemiologyTS
        - EpidemiologyTST
      Radioactivity:
        - RadiationTS
        - RadiationTST
      Seismic:
        - EarthquakeTS
        - SeismicTST
```

__Schemas:__
  The schemas to be created in the target postgis database.

__FeatureDatasets:__
  Mapping of the geodatabase's feature datasets to the schemas of the target postgis database

__FeatureClasses:__
  Mapping of the geodatabase's feature classes that do not belong to any feature dataset to the schemas of the target postgis database

__Tables:__
  Mapping of the geodatabase's tables to the schemas of target postgis database


__Tips:__

  * Currently the tool support only Latin Name fields and suptypes, domain values can be in any   language, make sure to set the corresponding windows domain
  
  * DB user must be superuser :

```sql
    CREATE USER user_migrate  WITH PASSWORD 'xxxxx' LOGIN SUPERUSER INHERIT  CREATEDB CREATEROLE  NOREPLICATION;
```

  * if you want to drop the migration user use: 

```sql
    revoke all ON SCHEMA information_schema from user_migrate ;

    revoke all ON ALL TABLES IN SCHEMA information_schema from  user_migrate;
    
    drop user user_migrate;
```

__Warnings:__

  * DO NOT apply this tool in a production postgis database!.  Insted use a staging database.
  
  * The target postgis database is created by the program
  
  * The tool only includes Simple features (Polygons, polylines, and points representing objects or places. See https://desktop.arcgis.com/es/arcmap/latest/analyze/arcpy-functions/featureclass-properties.htm  ) 
  
  * At this moment only the following geometry type conversions are supported:
  
|  Esri Type |    GDAL Type    |
|:----------:|:---------------:|
| Polygon    | MULTIPOLYGON    |
| Polyline   | MULTILINESTRING |
| Point      | POINT           |
| Multipoint | MULTIPOINT      |
  
  * If you do not use the python distribution included in Arcgis Desktop you must have into account the  ArcGIS Desktop and Numpy compability (see https://support.esri.com/en/technical-article/000013224): 

      *  10.7.1 - Python 2.7.16 and NumPy 1.9.3
      *  10.7 - Python 2.7.15 and NumPy 1.9.3
      *  10.6.1 - Python 2.7.14 and NumPy 1.9.3
      *  10.6 - Python 2.7.14 and NumPy 1.9.3
      *  10.5.1 - Python 2.7.13 and NumPy 1.9.3
      *  10.5 - Python 2.7.12 and NumPy 1.9.3

## Materialized views

The tool creates a materialized view for each postgis table  including the descriptions (label) of the related lookup tables. Such materialized view can be used for web mapping using software like Geoserver.

Example:
```sql
-- Feature
CREATE MATERIALIZED VIEW cartografia_100k.hito_limite_mv AS 
 select t.*    , ft0.description as ruleid_label  , ft1.description as symbol_label    
 from cartografia_100k.hito_limite as t  left join cartografia_100k.lut_hito_limite_rep_rules as ft0 on ( t.ruleid = ft0.code )  left join cartografia_100k.lut_dom_gen_plts as ft1 on ( t.symbol = ft1.code )  
 WITH  DATA;
```


## Credits


Credit goes to `James Ramm <ramshacklerecording@gmail.com>`_ who kindly developed and shared the archook package.

Refactored by Juan Carlos Méndez https://github.com/dersteppenwolf

## License

GNU Public License (GPL) Version 3
