##
 # __main__.py
 #
 # Description: Export, Transform and load data from ESRI File Geodatabase to PostGIS
 # Author: George Ioannou
 # Copyright: Cartologic 2017
 #
 ##
import getopt, sys, logging , traceback, argparse
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
    

def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


#-------------------------------------------------------------------------------
# Main - Instantiate the required database objects and perform the conversion
#
def main():
	parser = argparse.ArgumentParser(description='Convert a Filegeodatabase to Postgis.')
	parser.add_argument('-v', '--version', action='store_true',help='Program version' )
	parser.add_argument('--fgdb',  nargs='?',  help='Name of the filegeodatabase for conversion')
	parser.add_argument('--database',   nargs='?',  help='Name of the postgis database to be created for conversion')
	parser.add_argument('--host',   nargs='?',  help='Database host')
	parser.add_argument('--port', type=int, nargs='?',  help='Postgresql port')
	parser.add_argument('--user',  nargs='?',  help='database user ')
	parser.add_argument('--password',  nargs='?',  help='database password')
	parser.add_argument('--include_empty', type=str2bool,  nargs='?', default=False , help='Include empty tables and features. Default False')
	parser.add_argument('--lookup_tables_schema',  nargs='?', default='lookup_tables',   help='Name of the schema for lookup tables. Default:lookup_tables')
	parser.add_argument('--a_srs',  nargs='?',  help='Assign an output SRS.')
	parser.add_argument('--t_srs',  nargs='?',  help='Reproject/transform to this SRS on output.')
	args = parser.parse_args()
	#print(args)

	if(args.version):
		show_version()
		return

	logFormat = '%(asctime)-15s %(name)-12s %(levelname)-8s %(message)s'
	logfile = "output.log"
	logging.basicConfig(level=logging.DEBUG, format=logFormat, filename=logfile,  filemode='w' )
	logging.getLogger().addHandler(logging.StreamHandler())
	logging.debug("***********************************")
	logging.debug("Begin Program....")
	logging.debug("***********************************")
	try: 
		logging.debug(args)
		logging.debug("Begin Program....")
		filegdb = FileGDB(args.fgdb, args.include_empty, args.lookup_tables_schema)
		postgis = PostGIS(args.host, args.port, args.user, args.password, args.database, args.a_srs,  args.t_srs)

		filegdb.process()
		postgis.process(filegdb)
		
		filegdb.cleanup()
	except Exception as e:
		printError(e)

	logging.debug("***********************************")
	logging.debug("End Program....")
	logging.debug("***********************************")
