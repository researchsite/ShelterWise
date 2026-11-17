import os

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("PROJECT_ID") or "qwiklabs-gcp-04-99fa355171e1"
DATASET = os.environ.get("A4I_DATASET", "a4i_housing")
LOCATION = os.environ.get("A4I_LOCATION", "US")
METRO = os.environ.get("A4I_METRO", "San Francisco")
STATE_CODE = "CA"
STATE_FIPS = "06"
VERTEX_CONNECTION = "us.a4i-vertex"
EMBEDDING_ENDPOINT = "gemini-embedding-2"
FIRESTORE_DATABASE = "(default)"

# Courthouse coordinates (San Francisco Superior Court, 400 McAllister St)
COURTHOUSE_NAME = "San Francisco Superior Court (Civic Center Courthouse)"
COURTHOUSE_ADDRESS = "400 McAllister St, San Francisco, CA 94102"
COURTHOUSE_LAT = 37.78090
COURTHOUSE_LON = -122.41940

SHELTERWISE_MODEL = os.environ.get("SHELTERWISE_MODEL", "gemini-3.8-flash")
