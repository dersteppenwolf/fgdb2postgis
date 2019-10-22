#-*- coding: UTF-8 -*-

##
 # filegdb.py
 #
 # Description: Read file geodatabase, create tables for subtypes and domains
 #              Prepare sql scripts for indexes and foreign key constraints
 # Author: George Ioannou
 # Modified by:  Juan Carlos Méndez
 # Copyright: Cartologic 2017
 #
 ##
import os, logging, sys, traceback
# import yaml
from ruamel.yaml import YAML

from os import path

# locate and import arcpy
try:
	import archook
	archook.get_arcpy()
	import arcpy
except ImportError:
	logging.debug( "Unable to locate arcpy module...")
	exit(1)

yaml = YAML()

class FileGDB:
	def __init__(self, workspace, include_empty, lookup_tables_schema):
		self.workspace = workspace
		self.include_empty = include_empty
		self.lookup_tables_schema = lookup_tables_schema
		self.workspace_path = ""
		self.sqlfolder_path = ""
		self.yamlfile_path = ""
		self.schemas = []
		self.feature_datasets = {}
		self.feature_classes = {}
		self.tables = {}
		self.indexes = []
		self.constraints = []
		self.datasets = []

		self.lookup_prefix = "lut_"

		self.info()
		self.init_paths()
		self.setenv()
		self.parse_yaml()
		self.datasets = {} 
		ds = self.get_feature_datasets()
		for d in ds:
			self.datasets[d] = self.get_feature_classes(d) 

		self.tables_list = self.get_tables()
		self.standalone_features = self.get_feature_classes(None) 
		self.domain_tables = []

		logging.debug("tables_list: {} ".format(  self.tables_list ) )
		logging.debug("datasets: {} ".format(  self.datasets ) )
		
		

	#-------------------------------------------------------------------------------
	# Initialize file geodatabase environment
	#
	def init_paths(self):
		# workspace path
		workspace_path = path.join(os.getcwd(), self.workspace)
		workspace_dir = path.dirname(workspace_path)
		workspace_base = path.basename(workspace_path)

		# sqlfolder, yamlfile path
		sqlfolder_base = "%s.sql" % workspace_base
		yamlfile_base = "%s.yml" % workspace_base
		sqlfolder_path = path.join(workspace_dir, sqlfolder_base)
		yamlfile_path = path.join(workspace_dir, yamlfile_base)

		# set current object instance props
		self.workspace_path = workspace_path
		self.sqlfolder_path = sqlfolder_path
		self.yamlfile_path = yamlfile_path


	def info(self):
		logging.debug( "FileGDB Info:" )
		logging.debug( " Workspace: %s " % (self.workspace_path) )
		logging.debug( " Sqlfolder: %s" % self.sqlfolder_path )
		logging.debug( " Yamlfile: %s" % self.yamlfile_path )

	def setenv(self):
		logging.debug( "Setting arcpy environment ..." )
		arcpy.env.workspace = self.workspace
		arcpy.env.overwriteOutput = True

	def process(self):
		try:
			self.open_files()
			self.process_domains()
			self.process_subtypes()
			self.process_relations()
			self.process_schemas()
			self.close_files()
		except Exception as e:
			logging.error(e)
			tb = sys.exc_info()[2]
			tbinfo = traceback.format_tb(tb)[0]
			logging.error( tbinfo )

	#-------------------------------------------------------------------------------
	# Parse the yaml file and map data to schemas
	#
	def parse_yaml(self):
		logging.debug( "parse_yaml..." )
		# parse yaml file and map datasets, feature classes, tables to schemas
		if not path.exists(self.yamlfile_path):
			logging.debug( "Creating default YAML file ..." )
			self.create_yaml()

		with open(self.yamlfile_path, 'r') as ymlfile:
			data_map = yaml.load(ymlfile)

			for key_type, value_items in data_map.items():
				if (key_type == "Schemas"):
					self.schemas = value_items
				elif (key_type == "FeatureDatasets"):
					self.feature_datasets = value_items
				elif (key_type == "FeatureClasses"):
					self.feature_classes = value_items
				elif (key_type == "Tables"):
					self.tables = value_items
			
		# lookup_tables is a default schema and it will host subtypes, domains
		if self.lookup_tables_schema not in self.schemas:
			self.schemas.append(self.lookup_tables_schema)

	#-------------------------------------------------------------------------------
	# Open sql files
	#
	def open_files(self):
		logging.debug( "Initializing sql files ..." )

		if not path.exists(self.sqlfolder_path):
			os.mkdir(self.sqlfolder_path)

		self.f_create_schemas = open(path.join(self.sqlfolder_path, "create_schemas.sql"), "w")
		self.f_split_schemas = open(path.join(self.sqlfolder_path, "split_schemas.sql"), "w")
		self.f_create_indexes = open(path.join(self.sqlfolder_path, "create_indexes.sql"), "w")
		self.f_create_constraints = open(path.join(self.sqlfolder_path, "create_constraints.sql"), "w")
		self.f_find_data_errors = open(path.join(self.sqlfolder_path, "find_data_errors.sql"), "w")
		self.f_fix_data_errors = open(path.join(self.sqlfolder_path, "fix_data_errors.sql"), "w")

		self.write_headers()

	#-------------------------------------------------------------------------------
	# close sql files
	#
	def close_files(self):
		logging.debug( "Closing sql files ...")
		self.f_create_schemas.close()
		self.f_split_schemas.close()
		self.f_create_indexes.close()
		self.f_create_constraints.close()
		self.f_find_data_errors.close()
		self.f_fix_data_errors.close()

	#-------------------------------------------------------------------------------
	# Process domains
	# Convert domains to tables
	#
	def process_domains(self):
		logging.debug( "***********************************************************")
		logging.debug( "Processing domains ...")

		self.write_it(self.f_create_indexes, "\n-- Domains")
		self.write_it(self.f_create_constraints, "\n-- Domains")
		self.write_it(self.f_split_schemas, "\n-- Domains")

		## create table for each domain
		domains_list = arcpy.da.ListDomains(self.workspace)
		for domain in domains_list:
			self.create_domain_table(domain)

		logging.debug( "create fk constraints for data tables referencing domain tables ...")
		for table in self.tables_list:
			self.create_constraints_referencing_domains(table)


		logging.debug( "stand-alone feature classes ...")
		for fc in self.standalone_features:
			self.create_constraints_referencing_domains(fc)

		logging.debug( "features inside datasets...")
		logging.debug( self.datasets)
		for fds in self.datasets:
			logging.debug( "fds : {} ".format(fds) )
			fc_list = self.datasets[fds] 
			for f in fc_list:
				self.create_constraints_referencing_domains(f)
		logging.debug( "***********************************************************")


	#-------------------------------------------------------------------------------
	# Create domain table (list of values)
	#
	def create_domain_table(self, domain):
		domain_name = domain.name.replace(" ", "")
		logging.debug( "create_domain_table: {} ".format(domain_name))
		domain_table = "{}{}".format(self.lookup_prefix , domain_name.lower() ) 

		domain_field = "Code"
		domain_field_desc = "Description"

		logging.debug( " %s" % domain_table )

		if not arcpy.Exists(domain_table):
			arcpy.DomainToTable_management(self.workspace, domain.name, domain_table, domain_field, domain_field_desc)

		# create index
		dom = { "feature":domain_table,  "type": "table" , "schema" : self.lookup_tables_schema   }
		self.domain_tables.append( dom ) 
		self.create_index(domain_table, domain_field)
		self.split_schemas(dom, self.lookup_tables_schema)

	#-------------------------------------------------------------------------------
	# Create foraign key constraints to tables referencing domain tables
	#
	def create_constraints_referencing_domains(self, fc):
		layer = fc["feature"]
		logging.debug( "create_constraints_referencing_domains: {} ".format(layer))
		dmcode = "Code"
		dmcode_desc = "Description"

		subtypes = arcpy.da.ListSubtypes(layer)

		for stcode, v1 in subtypes.iteritems():
			for k2, v2 in v1.iteritems():
				if k2 == 'Default':
					stdefault = v2

				elif k2 == 'Name':
					stname = v2

				elif k2 == 'SubtypeField':
					if v2 != '':
						stfield = v2
						sttable = "{}{}{}".format(self.lookup_prefix , layer, stfield ) 
					else:
						stfield = '--'
						sttable = '--'

				elif k2 == 'FieldValues':
					for dmfield, v3 in v2.iteritems():
						if v3[1] is not None:
							dmtable = self.lookup_prefix + v3[1].name
							self.create_foreign_key_constraint(layer, dmfield, dmtable, dmcode)


	#-------------------------------------------------------------------------------
	# Process subtypes
	# Convert subtypes to tables
	#
	def process_subtypes(self):
		logging.debug( "Processing subtypes ...")

		self.write_it(self.f_create_indexes, "\n-- Subtypes")
		self.write_it(self.f_create_constraints, "\n-- Subtypes")
		self.write_it(self.f_split_schemas, "\n-- Subtypes")

		# create subtypes table for tables
		for table in self.tables_list:
			self.create_subtypes_table(  { "feature":table,  "type": "table"   }   )

		# create subtypes table for stand-alone featureclasses
		for fc in self.standalone_features:
			self.create_subtypes_table(fc)

		# create subtypes table for featureclasses in datasets
		for fds in self.datasets:
			fc_list = self.datasets[fds] 
			for f in fc_list:
				self.create_subtypes_table(f)

	#-------------------------------------------------------------------------------
	# Create subtypes table for layer/field and insert records (list of values)
	#
	def create_subtypes_table(self, fc):
		logging.debug("create_subtypes_table : {}".format(fc) )
		layer = fc["feature"]
		subtypes_dict = arcpy.da.ListSubtypes(layer)

		subtype_fields = {key: value['SubtypeField'] for key, value in subtypes_dict.iteritems()}
		subtype_values = {key: value['Name'] for key, value in subtypes_dict.iteritems()}

		key, field = subtype_fields.items()[0]

		if len(field) > 0:

			# find subtype field type
			field_type = None
			for f in arcpy.ListFields(layer):
				if f.name == field:
					field_type = f.type

			# convert field to upper case and try again if not found
			if field_type == None:	
				field = field.upper()
				for f in arcpy.ListFields(layer):
					if f.name.upper() == field:
						field_type = f.type

			subtypes_table = "{}{}_{}".format(self.lookup_prefix, layer, field).lower()
			logging.debug( " %s" % subtypes_table) 

			if not arcpy.Exists(subtypes_table):
				# create subtypes table
				arcpy.CreateTable_management(self.workspace, subtypes_table)
				arcpy.AddField_management(subtypes_table, field, field_type)
				arcpy.AddField_management(subtypes_table, "Description", "String")

				# insert records (list of values)
				cur = arcpy.da.InsertCursor(subtypes_table, "*")
				oid = 1
				for code, desc in subtype_values.iteritems():
					# print "  %s %s" % (code, desc)
					cur.insertRow([oid, code, desc])
					oid += 1

				del cur

			subt = { "feature":subtypes_table,  "type": "table" , "schema" : self.lookup_tables_schema   }
			self.domain_tables.append(subt)
			
			self.create_index(subtypes_table, field)
			self.create_foreign_key_constraint(layer, field, subtypes_table, field)
			self.split_schemas(subt, self.lookup_tables_schema)


	#-------------------------------------------------------------------------------
	# Process relations
	# Create necessary indexes and foreign key constraints to support each relation
	#
	def process_relations(self):
		logging.debug( "Processing relations ..." )

		self.write_it(self.f_create_indexes, "\n-- Relations (tables and feature classes)")
		self.write_it(self.f_create_constraints, "\n-- Relations (tables and feature classes)")

		relClassSet = self.get_relationship_classes()

		for relClass in relClassSet:
			rel = arcpy.Describe(relClass)
			if rel.isAttachmentRelationship:
				continue
			
			rel_origin_table = rel.originClassNames[0]
			rel_destination_table = rel.destinationClassNames[0]

			logging.debug( " rel_origin_table : {} , rel_destination_table : {}".format(rel_origin_table, rel_destination_table) )


			desc_destination = arcpy.Describe(rel_destination_table)
			logging.debug(desc_destination.dataType)
			if desc_destination.dataType in ('FeatureClass'):
				feature_type = desc_destination.featureType
				logging.debug(feature_type)
				# ignore annotations 
				if feature_type != 'Simple':
					continue
			
			rel_primary_key = "id"
			rel_foreign_key = rel.originClassKeys[1][0]

			# convert primary/foreign key to uppercase if not found
			# if rel_primary_key not in [field.name for field in arcpy.ListFields(rel_origin_table)]:
			# 	rel_primary_key = rel.originClassKeys[0][0].upper()

			# if rel_foreign_key not in [field.name for field in arcpy.ListFields(rel_destination_table)]:
			# 	rel_foreign_key = rel.originClassKeys[1][0].upper()

			logging.debug( " %s" % rel.name )
			# print " %s -> %s" % (rel_origin_table, rel_destination_table)

			self.create_index(rel_origin_table, rel_primary_key)
			self.create_foreign_key_constraint(rel_destination_table, rel_foreign_key, rel_origin_table, rel_primary_key)

			# prcess data errors (fk)
			str_data_errors_fk = '\\echo %s (%s) -> %s (%s);' % (rel_destination_table, rel_foreign_key, rel_origin_table, rel_primary_key)
			self.write_it(self.f_find_data_errors, str_data_errors_fk)

			str_data_errors = 'SELECT COUNT(*) FROM "%s" dest WHERE NOT EXISTS (SELECT 1 FROM "%s" orig WHERE dest."%s" = orig."%s");'
			str_data_errors = str_data_errors % (rel_destination_table, rel_origin_table, rel_foreign_key, rel_primary_key)
			str_data_errors = str_data_errors.lower()

			self.write_it(self.f_find_data_errors, str_data_errors)

			str_fix_errors_1 = 'INSERT INTO "%s" ("%s")' % (rel_origin_table, rel_primary_key)
			str_fix_errors_1 = str_fix_errors_1.lower()
			str_fix_errors_2 = 'SELECT DISTINCT detail."%s" \n  FROM "%s" AS detail \n LEFT JOIN "%s" AS master ON detail."%s" = master."%s" \n WHERE master.id IS NULL;\n'
			str_fix_errors_2 = str_fix_errors_2 % (rel_foreign_key, rel_destination_table, rel_origin_table, rel_foreign_key, rel_primary_key)
			str_fix_errors_2 = str_fix_errors_2.lower()

			self.write_it(self.f_fix_data_errors, str_fix_errors_1)
			self.write_it(self.f_fix_data_errors, str_fix_errors_2)

	#-------------------------------------------------------------------------------
	# Create relationship classes Set and return it to the calling routine
	#
	def get_relationship_classes(self):

		# # get featureclasses outside of datasets
		# fc_list = self.standalone_features		

		# # get featureclasses within datasets
		# for fds in self.datasets:
		# 	features = self.datasets[fds] 
		# 	fc_list.extend(features)

		# create relationship classes set
		relClasses = set()
		for i, fc in enumerate(self.tables_list):
			#logging.debug(fc)
			desc = arcpy.Describe(fc)
			#logging.debug(desc.dataType)
			dataType = desc.dataType
			# ignore annotations 
			if dataType in ('FeatureClass', 'Table'):
				for j,rel in enumerate(desc.relationshipClassNames):
					relClasses.add(rel)

		return relClasses

	#-------------------------------------------------------------------------------
	# Process Schemas
	# Prepare sql to split Tables and Feature Classes in Schemas
	#
	def process_schemas(self):
		logging.debug(  "Processing schemas ..." )

		# create extension postgis
		str_create_extension = "\nCREATE EXTENSION IF NOT EXISTS postgis;"
		self.write_it(self.f_create_schemas, str_create_extension)

		# create schemas
		for schema in self.schemas:
			schema = schema.lower()
			logging.debug("schema: {}  ".format(schema) )
			if schema == 'public':
				continue

			str_drop_schema = '\nDROP SCHEMA IF EXISTS \"%s\" CASCADE;' % schema
			str_create_schema = 'CREATE SCHEMA \"%s\";' % schema
			self.write_it(self.f_create_schemas, str_drop_schema)
			self.write_it(self.f_create_schemas, str_create_schema)

		# split feature classes within feature datasets to schemas
		self.write_it(self.f_split_schemas, "\n-- FeatureDatasets:")
		logging.debug( " FeatureDatasets" )
		for dataset, schema  in self.feature_datasets.items():
			logging.debug("schema: {} , dataset: {} ".format(schema, dataset) )
			schema = schema[0].lower()
			logging.debug("schema: {} , dataset: {} ".format(schema, dataset) )
			if schema == 'public':
				continue
			
			fc_list =self.datasets[dataset] 
			for fc in fc_list:
				logging.debug("fc: {} , schema: {} ".format(fc, schema) )
				fc["schema"] = schema
				self.split_schemas(fc, schema)

		# split feature classes outside of feature datasets to schemas
		self.write_it(self.f_split_schemas, "\n-- FeatureClasses:")
		logging.debug( " FeatureClasses" )
		for schema, fcs in self.feature_classes.items():
			if schema == 'public':
				continue

			for fc in fcs:
				if arcpy.Exists(fc):
					feat = [x for x in self.standalone_features if x["feature"] == fc][0]
					feat["schema"] = schema
					self.split_schemas(fc, schema)

		# split tables to schemas
		self.write_it(self.f_split_schemas, "\n-- Tables:")
		logging.debug( " Tables" )
		for schema, tables in self.tables.items():
			if schema == 'public':
				continue

			for table in tables:
				if arcpy.Exists(table):
					self.split_schemas(table, schema)

	#-------------------------------------------------------------------------------
	# Compose and write sql to alter the schema of a table
	#
	def split_schemas(self, fc, schema):
		logging.debug(fc)
		table = fc["feature"]
		str_split_schemas = "ALTER TABLE \"%s\" SET SCHEMA \"%s\";" % (table.lower(), schema.lower())
		self.write_it(self.f_split_schemas, str_split_schemas)

	#-------------------------------------------------------------------------------
	# Create indexes
	#
	def create_index(self, table, field):
		idx_name = ( "%s_%s_idx" % (table, field) ).lower()

		if idx_name not in self.indexes:
			self.indexes.append(idx_name)
			str_index = "CREATE UNIQUE INDEX \"%s\" ON \"%s\" (\"%s\"); \n" % (idx_name, table.lower(), field.lower())
			self.write_it(self.f_create_indexes, str_index)

	#-------------------------------------------------------------------------------
	# Create foreign key constraints
	#
	def create_foreign_key_constraint(self, table_details, fkey, table_master, pkey):
		logging.debug( "create_foreign_key_constraint: table_details : {} ".format(table_details))

		fkey_name = ( "%s_%s_%s_fkey" % (table_details, fkey, table_master) ).lower()
		logging.debug( "fkey_name:  {} ".format(fkey_name))

		if fkey_name not in self.constraints:
			self.constraints.append(fkey_name)
			str_constraint = 'ALTER TABLE "%s" ADD CONSTRAINT "%s" FOREIGN KEY ("%s") REFERENCES "%s" ("%s") NOT VALID; \n'
			str_constraint = str_constraint % (table_details.lower(), fkey_name, fkey.lower(), table_master.lower(), pkey.lower())
			self.write_it(self.f_create_constraints, str_constraint)

	#-------------------------------------------------------------------------------
	# Write headers to sql files
	#
	def write_headers(self):
		str_message = "SET client_min_messages TO warning;"

		self.write_it(self.f_create_schemas, str_message)
		self.write_it(self.f_create_indexes, str_message)
		self.write_it(self.f_create_constraints, str_message)
		self.write_it(self.f_split_schemas, str_message)
		self.write_it(self.f_fix_data_errors, str_message)

	#-------------------------------------------------------------------------------
	# Write string to given open file
	#
	def write_it(self, out_file, string):
		out_file.write(string + "\n")

	def create_yaml(self):
		# initialize dictionaries
		schemasdict = {}
		fdsdict = {'FeatureDatasets': {}}
		fcdict = {'FeatureClasses': {}}
		tablesdict = {'Tables': {}}

		# feature datasets
		fdslist = self.get_feature_datasets()
		if fdslist != None:
			fdslist.sort()
			for fds in fdslist:
				fdsdict['FeatureDatasets'].update({fds: [fds]})

		# featureclasses in root
		fclist =[]
		for f in self.standalone_features:
			fclist.append(f["feature"])
		fcdict['FeatureClasses'].update({'public': fclist})

		# tables
		tablesdict['Tables'].update({'public': self.tables_list})

		# schemas
		schemasdict.update({'Schemas': fdslist})

		with open(self.yamlfile_path, 'w') as outfile:
			yaml.dump(schemasdict, outfile)

		with open(self.yamlfile_path, 'a') as outfile:
			yaml.dump(fdsdict, outfile)

		with open(self.yamlfile_path, 'a') as outfile:
			yaml.dump(fcdict, outfile)

		with open(self.yamlfile_path, 'a') as outfile:
			yaml.dump(tablesdict, outfile)

	'''

	'''
	def get_feature_datasets(self):
		logging.debug("get_feature_datasets")
		fdslist = arcpy.ListDatasets("*", "Feature")
		fdslist.sort()
		logging.debug(fdslist )
		return fdslist

	'''
	Includes only  Simple Features
	'''
	def get_feature_classes(self, fds):
		logging.debug("get_feature_classes")
		fclist = arcpy.ListFeatureClasses("*", "", fds)
		features = []
		for f in fclist:
			feature_desc = arcpy.Describe(f)	
			feature_type = feature_desc.featureType
			shapeType =  feature_desc.shapeType
			result = arcpy.GetCount_management(f)
			count = int(result.getOutput(0))
			#logging.debug("Feature: {} , Count: {}, feature_type: {}, shapeType: {}  ".format(  f, count , feature_type , shapeType))

			if count == 0 and not  self.include_empty:
				continue

			if feature_type != 'Simple':
				continue
			
			feat = { "feature":f, "count": count, "feature_type":feature_type, "shapeType" :shapeType , "type": "feature_class", "dataset": fds   }
			#logging.debug(feat)
			features.append(feat)

		features.sort(key=lambda x: x["feature"] )
		logging.debug(features )
		return features

	'''

	'''
	def get_tables(self):
		logging.debug("get_tables")
		tableslist = arcpy.ListTables("*")
		tables = []
		for t in tableslist:
			result = arcpy.GetCount_management(t)
			count = int(result.getOutput(0))
			#logging.debug("Table: {} , Count: {} ".format( t, count  ))
			if t.startswith(self.lookup_prefix):
				continue
			if count == 0 and not  self.include_empty:
				continue
			feat = { "feature":t, "count": count,  "type": "table"   }
			tables.append(t)

		tables.sort(key=lambda x: x["feature"] )
		logging.debug(tables )
		return tables


	'''

	'''
	def cleanup(self):
		logging.debug("Cleanup temporary lookup tables...")
		lutslist = arcpy.ListTables(self.lookup_prefix+"*")
		for lut in lutslist:
			arcpy.Delete_management(lut)