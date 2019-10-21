##
 # __main__.py
 #
 # Description: Export, Transform and load data from ESRI File Geodatabase to PostGIS
 # Author: George Ioannou
 # Copyright: Cartologic 2017
 #
 ##
import getopt, sys, logging , traceback
from .filegdb import FileGDB
from .postgis import PostGIS
from .version import get_version

def show_version():
	print "Version: %s"%(get_version()) 
	sys.exit(1)

def printError(e):
    logging.error("****************************************************************************************************************")
    logging.error(e)
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    logging.error( tbinfo )
    logging.error("****************************************************************************************************************")
    
def show_usage():
	print "Usage:"
	print "  fgdb2postgis.py -v"
	print "  fgdb2postgis.py -h"
	print "  fgdb2postgis.py -f filegdb"
	print "                  --database=database name"
	print "                  --a_srs=a_srs"
	print "                  --t_srs=t_srs"
	print "                  --host=host"
	print "                  --port=port"
	print "                  --user=user"
	print "                  --password=password"
	print "                  --include_empty=False/True"

	sys.exit(1)


print(sys.argv)
print(len(sys.argv) )
if len(sys.argv) < 10:
	show_usage()
else:
	try:
		options, remainder = getopt.getopt(sys.argv[1:], 'hvf:p:', ['fgdb=', 'database=', 'a_srs=', 't_srs=', 'host=', 'port=', 'user=', 'password=', 'include_empty='])
	except getopt.GetoptError as err:
		print str(err)
		show_usage()

for opt, arg in options:
	if opt == '-h':
		show_usage()
	elif opt == '-v':
		show_version()
	elif opt in ('-f'):
		fgdb = arg
	elif opt in ('--database'):
		database = arg
	elif opt in ('--a_srs'):
		a_srs = arg
	elif opt in ('--t_srs'):
		t_srs = arg
	elif opt in ('--host'):
		host = arg
	elif opt in ('--port'):
		port = arg
	elif opt in ('--user'):
		user = arg
	elif opt in ('--password'):
		password = arg
	
	if opt in ('--include_empty'):
		include_empty = arg
	else:
		include_empty = False

#-------------------------------------------------------------------------------
# Main - Instantiate the required database objects and perform the conversion
#
def main():
	logFormat = '%(asctime)-15s %(name)-12s %(levelname)-8s %(message)s'
	logfile = "output.log"
	logging.basicConfig(level=logging.DEBUG, format=logFormat, filename=logfile,  filemode='w' )
	logging.getLogger().addHandler(logging.StreamHandler())
	logging.debug("***********************************")
	logging.debug("Begin Program....")
	logging.debug("***********************************")
	try: 
		logging.debug("fgdb:{},  include_empty:{}  ".format(   fgdb, a_srs, include_empty          ))
		logging.debug("host:{},  port:{},  user:{} ,  password:{},  database:{}, a_srs:{},   t_srs:{}  ".format(   host, port, user, password, database, a_srs,  t_srs  ))


		logging.debug("Begin Program....")
		filegdb = FileGDB(fgdb, include_empty)
		postgis = PostGIS(host, port, user, password, database, a_srs,  t_srs)

		filegdb.info()
		postgis.info()

		filegdb.open_files()
		filegdb.process_domains()
		filegdb.process_subtypes()
		filegdb.process_relations()
		filegdb.process_schemas()
		filegdb.close_files()

		postgis.connect()
		postgis.update_views()
		postgis.create_schemas(filegdb)
		postgis.load_database(filegdb)
		postgis.apply_sql(filegdb)
		postgis.disconnect()

		filegdb.cleanup()
	except Exception as e:
		printError(e)

	logging.debug("***********************************")
	logging.debug("End Program....")
	logging.debug("***********************************")
