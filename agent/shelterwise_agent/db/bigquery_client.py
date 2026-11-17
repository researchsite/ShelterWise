from google.cloud import bigquery
from shelterwise_agent.config import PROJECT_ID, DATASET

class BQClient:
    def __init__(self):
        self.client = bigquery.Client(project=PROJECT_ID)

    def search_complaints_vector(self, query: str, top_k: int = 25):
        sql = f"""
        SELECT base.request_id, base.block_address, base.property_type, 
               base.inspection_status, base.closed_date, base.complaint_narrative,
               distance
        FROM VECTOR_SEARCH(
          TABLE `{PROJECT_ID}.{DATASET}.complaints_embedded`,
          'embedding',
          (SELECT AI.EMBED('{query}', connection_id => 'us.a4i-vertex', endpoint => 'gemini-embedding-2')),
          top_k => {top_k},
          options => '{{"use_brute_force": true}}'
        )
        """
        return list(self.client.query(sql).result())

    def get_tract_context(self, geoid: str):
        sql = f"""
        SELECT * FROM `{PROJECT_ID}.{DATASET}.v_tract_stability_context`
        WHERE census_tract_geoid = '{geoid}'
        """
        rows = list(self.client.query(sql).result())
        return dict(rows[0].items()) if rows else None
    
    def get_statutes_and_bulletins(self, metro: str):
        statutes = list(self.client.query(f"SELECT * FROM `{PROJECT_ID}.{DATASET}.municipal_housing_ordinance_statutes` WHERE metro_area = '{metro}'").result())
        bulletins = list(self.client.query(f"SELECT * FROM `{PROJECT_ID}.{DATASET}.rental_relief_program_bulletins` WHERE metro_area = '{metro}'").result())
        return statutes, bulletins
