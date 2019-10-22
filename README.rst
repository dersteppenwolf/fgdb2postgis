====================================================
File Geodatabase to PostGIS converter (fgdb2postgis)
====================================================
The aim of this tool is to convert an ESRI file Geodatabase to a PostGIS database maintaining data, domains, subtypes and relationships.
The tool will copy over the feature classes as postgis layers and the tables as standard tables. The domains and subtypes will be converted to PostgreSQL lookup tables.
The tool will then create all necessary indexes and constraints to maintain the required relates between the layers, tables and lookup tables.
The tool creates materialized views of the tables including descriptions of the lookup tables suitable for the web publishing using  Geoserver.
To recreate the same experience of the domains and subtypes in QGIS using the output data, please install the plugin `Data Manager <https://github.com/cartologic/qgis-datamanager-plugin>`_.
Now you can have domain experience in QGIS that is stored in the database and not in the QGIS project.

.. note::
   This library requires GDAL/OGR libraries and ESRI ArcGIS to be installed in the system.

Installation
------------
This package should be installed only on windows systems because of ArcGIS (Arcpy) limitation.




Install required packages::

    pip install psycopg2>=2.6.2
    pip install pyyaml>=3.12
    pip install archook==1.1.0

Install fgdb2postgis::

    pip install fgdb2postgis

.. note::

  * This tool requires to have GDAL/OGR libraries and ArcGIS 10.3 or later installed.
  * ESRI Python packages usually under C:\Python27\ArcGIS10.* might not have pip included make sure to

    * Install pip if not already installed
    * Setup ESRI python and GDAL/OGR in windows path environment variable

Usage
-----

Command line options::

Show help: 

    fgdb2postgis -h

Generate the yml file and exit: 

  fgdb2postgis -yml --fgdb sample.gdb

Convert fgdb: 

    fgdb2postgis --fgdb mygdb.gdb  --database=migratetdb  --host=localhost  --port=5432  --user=user_migrate  --password=user_migrate --a_srs=EPSG:4686   --t_srs=EPSG:4686 --include_empty=False --lookup_tables_schema=mylookuptableschema




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

Schemas:
  The schemas to be created in the target postgis database.

FeatureDatasets:
  Mapping of the geodatabase's feature datasets to the schemas of the target postgis database

FeatureClasses:
  Mapping of the geodatabase's feature classes that do not belong to any feature dataset to the schemas of the target postgis database

Tables:
  Mapping of the geodatabase's tables to the schemas of target postgis database


Tip:
  * This tool is tested with PostgreSQL v 11 ,  PostGIS v 2.5, Arcgis desktop 10.6.1, gdal 2.4.0
  * Currently the tool support only Latin Name fields and suptypes, domain values can be in any   language, make sure to set the corresponding windows domain
  * DB user must be superuser :

    CREATE USER user_migrate  WITH PASSWORD 'xxxxx' LOGIN SUPERUSER INHERIT  CREATEDB CREATEROLE  NOREPLICATION;

  * if you want to drop the migration user use: 

    revoke all ON SCHEMA information_schema from user_migrate ;

    revoke all ON ALL TABLES IN SCHEMA information_schema from  user_migrate;
    
    drop user user_migrate;

Warning:
  * DO NOT apply this tool in a production postgis database!, insted use a staging database
  * The target postgis database is created by te program
  * The tool only includes Simple features (Polygons, polylines, and points representing objects or places that have area. See https://desktop.arcgis.com/es/arcmap/latest/analyze/arcpy-functions/featureclass-properties.htm  ) 
  * If you do not use the python distribution included in Arcgis Desktop you must have into account the  ArcGIS Desktop and Numpy compability (see https://support.esri.com/en/technical-article/000013224): 
    *  10.7.1 - Python 2.7.16 and NumPy 1.9.3
    *  10.7 - Python 2.7.15 and NumPy 1.9.3
    *  10.6.1 - Python 2.7.14 and NumPy 1.9.3
    *  10.6 - Python 2.7.14 and NumPy 1.9.3
    *  10.5.1 - Python 2.7.13 and NumPy 1.9.3
    *  10.5 - Python 2.7.12 and NumPy 1.9.3


Credits
-------

Credit goes to `James Ramm <ramshacklerecording@gmail.com>`_ who kindly developed and shared the archook package.

License
-------
GNU Public License (GPL) Version 3
