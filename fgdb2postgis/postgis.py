#-*- coding: UTF-8 -*-
##
 # postgis.py
 #
 # Description: Use ogr2ogr to convert file geodatabase to postgis
 #              Apply number of sql scripts to create indexes and foreign key constraints
 # Author: George Ioannou
 # Modified by:  Juan Carlos Méndez
 # Copyright: Cartologic 2017
 #
 ##
import sys, logging
import psycopg2
from os import path, system

class PostGIS:
	def __init__(self, host, port, user, password, dbname,a_srs, t_srs):
		self.dbname = dbname
		self.a_srs = a_srs
		self.t_srs = t_srs
		self.host = host
		self.port = port
		self.user = user
		self.password = password
		self.conn = None
		self.conn_string = (
			"dbname=%s host=%s port=%s user=%s password=%s" % (self.dbname, self.host, self.port, self.user, self.password)
		)

		self.info()

	def info(self):
		logging.debug(  'PostGIS Info:')
		logging.debug(  ' Database: %s (%s)' % (self.dbname, self.t_srs) )
		logging.debug(  ' Host: %s' % self.host  )
		logging.debug(  ' Port: %s' % self.port   )
		logging.debug(  ' User: %s' % self.user   )
		logging.debug(  ' Password: %s' % self.password  )
		self.create_database()

	def process(self, filegdb):
		self.connect()
		self.update_views()
		self.create_schemas(filegdb)
		self.load_database(filegdb)
		self.apply_sql(filegdb)
		self.disconnect()


	'''
	Create a new database 
	'''
	def create_database(self):
		logging.debug(  "create_database ...")
		try:
			conn = psycopg2.connect("dbname=%s host=%s port=%s user=%s password=%s" % ("postgres", self.host, self.port, self.user, self.password) )
			conn.set_isolation_level(0)
			cursor = conn.cursor()
			sql = " DROP DATABASE  IF EXISTS {} ; ".format(self.dbname)
			cursor.execute(sql)
			sql = " create DATABASE  {} ; ".format(self.dbname)
			cursor.execute(sql)
			cursor.close()

			conn = psycopg2.connect("dbname=%s host=%s port=%s user=%s password=%s" % (self.dbname, self.host, self.port, self.user, self.password) )
			conn.set_isolation_level(0)
			cursor = conn.cursor()
			sql = "GRANT USAGE, CREATE ON SCHEMA information_schema TO {} ;".format(self.user)
			cursor.execute(sql)
			sql = "GRANT SELECT ON ALL TABLES IN SCHEMA information_schema TO {}".format(self.user )
			cursor.execute(sql)
			cursor.close()

		except psycopg2.Error as err:
			logging.error(  str(err)  )
			logging.error(  'Unable to create database %s ...' % self.dbname )
			sys.exit(1)


	def connect(self):
		logging.debug(  "connect to database ...")
		try:
			self.conn = psycopg2.connect(self.conn_string)
			logging.debug(  'Connect to database ...' )
		except psycopg2.Error as err:
			logging.error(  str(err)  )
			logging.error(  'Unable to connect to database %s ...' % self.dbname )
			sys.exit(1)

	def disconnect(self):
		logging.debug(  "disconnect from database ...")
		if self.conn:
			self.conn.commit()
			self.conn.close()

		logging.debug(  "Disconnected from database." )


	'''
	Sometimes the automatic detection of geometry type doesn't work or it is needed
	to force a specific type (non 3d)
	https://gdal.org/programs/ogr2ogr.html#cmdoption-ogr2ogr-nlt
	'''
	def get_gdal_type(self, feat):
		shapeType = feat["shapeType"] 
		logging.debug(  shapeType)
		gdal_type = ""
		if shapeType == 'Polygon':
			gdal_type = "MULTIPOLYGON"
		elif shapeType == 'Polyline':
			gdal_type = "MULTILINESTRING"
		elif shapeType == 'Point':
			gdal_type = "POINT"
		elif shapeType == 'Multipoint':
			gdal_type = "MULTILINESTRING"

		return "  -nlt  {}  ".format(gdal_type)


	def load_database(self, filegdb):
		logging.debug(  "Loading database tables ...")

		gdal_cmd = 'ogr2ogr -f "PostgreSQL" "PG:{}"  {}  {}   -overwrite -progress -skipfailures -append \
			-a_srs {} 	-t_srs {} 	-lco launder=yes  -lco fid=id  	-lco GEOMETRY_NAME=geom -lco OVERWRITE=YES  \
			--config OGR_TRUNCATE YES -nln {} -lco SCHEMA={} --config PG_USE_COPY YES {}  '

		

		commands = []

		for domain in filegdb.domain_tables:
			#logging.debug( domain)
			c = gdal_cmd.format(  self.conn_string, filegdb.workspace, domain["feature"], self.a_srs, self.t_srs, domain["feature"].lower(), 
				domain["schema"] , ""  )
			commands.append(c)

		for feat in filegdb.standalone_features:
			logging.debug( feat)
		
		#logging.debug( filegdb.datasets )
		datasets = filegdb.datasets
		for d  in datasets:
			logging.debug( d )
			features = datasets[d] 
			for feat in features:
				logging.debug( feat)
				c = gdal_cmd.format(  self.conn_string, filegdb.workspace, feat["feature"], self.a_srs, self.t_srs, feat["feature"].lower(), 
					feat["schema"], self.get_gdal_type( feat )  )
				commands.append(c)

		for cmd in commands:
			logging.debug(cmd)
			system(cmd)


		# cmd = 'ogr2ogr -f "PostgreSQL" "PG:%s" 	-overwrite -progress -skipfailures -append \
		# 	-a_srs %s 	-t_srs %s 	-lco launder=yes  -lco fid=id  \
		# 	-lco geometry_name=geom -lco OVERWRITE=YES  \
		# 	--config OGR_TRUNCATE YES 	--config PG_USE_COPY YES \
		# 	%s' % (self.conn_string, self.a_srs, self.t_srs, filegdb.workspace)
		# logging.debug( cmd)
		# system(cmd)

	def update_views(self):
		

		logging.debug(  "Updating database views ..."  )
		sql_files = [
			'information_schema_views.sql',
			'foreign_key_constraints_vw.sql'
		]

		for sql_file in sql_files:
			sql_file = path.join(path.abspath(path.dirname(__file__)), 'sql_files/%s' % sql_file)
			self.execute_sql(sql_file)

	def create_schemas(self, filegdb):
		logging.debug(  "Creating schemas ..."  )

		sql_files = ['create_schemas.sql']
		for sql_file in sql_files:
			sql_file = path.join(filegdb.sqlfolder_path, sql_file)
			self.execute_sql(sql_file)

	def apply_sql(self, filegdb):
		logging.debug(  "Applying sql scripts ..." )
		sql_files = [
			'fix_data_errors.sql',
			'create_indexes.sql',
			'create_constraints.sql',
			'split_schemas.sql'
		]

		for sql_file in sql_files:
			sql_file = path.join(filegdb.sqlfolder_path, sql_file)
			self.execute_sql(sql_file)


	
	def execute(self, sql):
		cursor = self.conn.cursor()
		cursor.execute(sql)
		cursor.close()
		self.conn.commit()

	def execute_sql(self, sql_file):
		cursor = self.conn.cursor()

		if path.exists(sql_file):
			# logging.debug(  " %s" % sql_file )
			with open(sql_file, "r") as sql:
				code = sql.read()
				cursor.execute(code)
		else:
			logging.error(  " Unable to locate sql file:")
			logging.error(  sql_file )

		cursor.close()
		self.conn.commit()
