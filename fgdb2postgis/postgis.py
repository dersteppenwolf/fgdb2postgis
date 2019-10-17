##
 # postgis.py
 #
 # Description: Use ogr2ogr to convert file geodatabase to postgis
 #              Apply number of sql scripts to create indexes and foreign key constraints
 # Author: George Ioannou
 # Copyright: Cartologic 2017
 #
 ##
import sys, logging
import psycopg2
from os import path, system

class PostGIS:
	def __init__(self, host, port, user, password, dbname, t_srs):
		self.dbname = dbname
		self.t_srs = t_srs
		self.host = host
		self.port = port
		self.user = user
		self.password = password
		self.conn = None
		self.conn_string = (
			"dbname=%s host=%s port=%s user=%s password=%s" % (self.dbname, self.host, self.port, self.user, self.password)
		)

	def info(self):
		logging.debug(  'PostGIS Info:')
		logging.debug(  ' Database: %s (%s)' % (self.dbname, self.t_srs) )
		logging.debug(  ' Host: %s' % self.host  )
		logging.debug(  ' Port: %s' % self.port   )
		logging.debug(  ' User: %s' % self.user   )
		logging.debug(  ' Password: %s' % self.password  )

	def connect(self):
		try:
			self.conn = psycopg2.connect(self.conn_string)
			logging.debug(  'Connect to database ...' )
		except psycopg2.Error as err:
			logging.error(  str(err)  )
			logging.error(  'Unable to connect to database %s ...' % self.dbname )
			sys.exit(1)

	def disconnect(self):
		if self.conn:
			self.conn.commit()
			self.conn.close()

		logging.debug(  "Disconnect from database ..." )

	def load_database(self, filegdb):

		logging.debug(  "Loading database tables ...")

		cmd = 'ogr2ogr -f "PostgreSQL" "PG:%s" \
			-overwrite -progress -skipfailures -append \
			-a_srs %s 	-t_srs %s \
			-lco fid=id \
			-lco launder=yes \
			-lco geometry_name=geom -lco OVERWRITE=YES  \
			--config OGR_TRUNCATE YES \
			--config PG_USE_COPY YES \
			%s' % (self.conn_string, filegdb.a_srs, self.t_srs, filegdb.workspace)

		# ogr2ogr   "G:/500k_24_04_2016.gdb"  Administrativo_P  
		#     -lco SCHEMA=cartografia_500k    
		# -nlt  POINT -nln  administrativo_p
		
		logging.debug( cmd)

		system(cmd)

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
