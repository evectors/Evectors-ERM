# Django settings for erm project.
import os

DEBUG = False
DEBUG_JSON = False  #set to true to have json always returned in indented form
DEBUG_API = False   #set to true to have passed parameters returned together with the answer
DEBUG_ERM=False     #set to true to have a trackback of the stack on errors
DEBUG_SQL=False     #set to true to have MYSQL queries returned on do_query errors in connectors 

SANITIZE_CHAR='-'
SLUG_PROGRESSIVE_LENGTH=7

TEMPLATE_DEBUG = DEBUG

PROJECT_PATH = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIRS = (os.path.join(PROJECT_PATH, 'templates/admin'))

DELETED_ENTITIES_DUMP_DIR=os.path.join(PROJECT_PATH, 'deleted_entitites')
PICKLER_DIR=os.path.join(PROJECT_PATH, 'pickled')

try:
    os.makedirs(PICKLER_DIR)
except:
    pass

                         
ADMINS = ()

MANAGERS = ADMINS 

DATABASE_ENGINE = 'mysql'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'erm_db'             # Or path to database file if using sqlite3.
DATABASE_USER = 'erm_user'             # Not used with sqlite3.
DATABASE_PASSWORD = 'erm_pass'         # Not used with sqlite3.
DATABASE_HOST = 'localhost'             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.
DATABASE_OPTIONS = {"init_command": "SET storage_engine=INNODB"}

DM_DATABASE_HOST=DATABASE_HOST
DM_DATABASE_USER=DATABASE_USER
DM_DATABASE_NAME='erm_dm_simpledb' 
DM_DATABASE_PASSWORD=DATABASE_PASSWORD

TIME_ZONE = 'UTC'
# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''


# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '12345678901234567890123456789012'
SECRET_KEY_LENGTH=len(SECRET_KEY)

#facebook connector settings

FACEBOOK_CONNECTOR_API_KEY=""
FACEBOOK_CONNECTOR_SECRET_KEY=""

#twitter connector settings

TWITTER_APP_CONSUMER_KEY=""
TWITTER_APP_CONSUMER_SECRET=""

#searchengine prefs

SEARCH_ENGINE_ACTIVE=False
SEARCH_ENGINE_ENGINE='lucene'

#lucene prefs

LUCENE_INDEX_DIR='/var/lucene/indexes'

#logger prefs

LOG_THRESHOLD='INFO'
LOG_TO_STDOUTLOG = False
LOG_FORMAT ='%(asctime)s %(process)d %(levelname)-8s %(message)s'
LOG_DATE_FORMAT = '%d-%m-%Y %H:%M:%S'
LOG_VERBOSE=False
LOG_DIR="/var/log/pages/"
LOG_FILE_NAME="erm"
LOG_LOGGER = "pages_logger"
LOG_ROTATING = False

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.transaction.TransactionMiddleware',

)

ROOT_URLCONF = 'erm.urls'



INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'erm.core',
    'erm.datamanager',
)

#Import specific installation setting, if present
try:
    from local_settings import *
except ImportError:
    pass
