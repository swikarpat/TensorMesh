import os
from neo4j import GraphDatabase
from typing import List, Dict

class SupplyChainGraph:
    def __init__(self, user="neo4j", password="password123"):
        # Automatically switch to Docker network if running in Docker, else use localhost
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def initialize_schema(self):
        """Creates constraints to ensure data integrity."""
        query = "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE"
        with self.driver.session() as session:
            session.run(query)

    def ingest_trade_route(self, source: str, target: str, material: str, quantity: int):
        """Creates nodes and relationships for a trade route."""
        query = """
        MERGE (s:Entity {name: $source})
        MERGE (t:Entity {name: $target})
        MERGE (s)-[r:EXPORTS_TO {material: $material}]->(t)
        SET r.quantity = $quantity
        """
        with self.driver.session() as session:
            session.run(query, source=source, target=target, material=material, quantity=quantity)

    def trace_origin(self, entity_name: str) -> List[Dict]:
        """GraphRAG query: Finds all upstream suppliers for a given entity."""
        query = """
        MATCH (upstream:Entity)-[r:EXPORTS_TO]->(target:Entity {name: $entity_name})
        RETURN upstream.name AS supplier, r.material AS material, r.quantity AS qty
        """
        with self.driver.session() as session:
            result = session.run(query, entity_name=entity_name)
            return [record.data() for record in result]

    def trace_supply_dependency(self, entity_name: str, mineral: str, max_hops: int = 4) -> Dict:
        """Trace upstream mineral dependencies and calculate concentration risk."""
        query = """
                MATCH path = (source:Entity)-[rels:EXPORTS_TO*1..8]->(target:Entity {name: $entity_name})
                WHERE length(path) <= $max_hops
                    AND any(rel IN rels WHERE toLower(rel.material) CONTAINS toLower($mineral))
        WITH source, path, rels,
             reduce(total = 0, rel IN rels | total + coalesce(rel.quantity, 0)) AS quantity
        RETURN source.name AS source,
               length(path) AS hops,
               quantity,
               [rel IN rels | rel.material] AS materials,
               [node IN nodes(path) | node.name] AS route
        ORDER BY quantity DESC
        """
        with self.driver.session() as session:
            result = session.run(query, entity_name=entity_name, mineral=mineral, max_hops=max_hops)
            dependencies = [record.data() for record in result]

        quantities = [float(item.get("quantity", 0)) for item in dependencies]
        total_quantity = sum(quantities)
        top_share = max(quantities, default=0.0) / total_quantity if total_quantity else 0.0
        bottlenecks = [
            item["source"]
            for item in dependencies
            if item.get("quantity", 0) == max(quantities, default=0.0)
        ]
        return {
            "entity_name": entity_name,
            "mineral": mineral,
            "dependencies": dependencies,
            "bottleneck_entities": bottlenecks,
            "smelter_concentration_risk": round(top_share, 4),
        }