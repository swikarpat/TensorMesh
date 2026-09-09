import os
from typing import Any, Dict, List

from neo4j import GraphDatabase

class SupplyChainGraph:
    def __init__(self, user="neo4j", password="password123"):
        # Automatically switch to Docker network if running in Docker, else use localhost
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def initialize_schema(self):
        """Creates constraints to ensure data integrity."""
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")
            for label in ("Deposit", "RockFormation", "RareEarthMineral", "Refinery"):
                session.run(
                    f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.name IS UNIQUE"
                )

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

    def query_hybrid_knowledge_graph(self, deposit_name: str) -> Dict[str, Any]:
        """Return structured deposit traversal plus indexed survey excerpts."""
        query = """
        MATCH (d:Deposit {name: $deposit_name})
        OPTIONAL MATCH (d)-[:HOSTED_IN]->(formation:RockFormation)
        OPTIONAL MATCH (d)-[contains:CONTAINS_MINERAL]->(mineral:RareEarthMineral)
        OPTIONAL MATCH (mineral)-[supplies:SUPPLIES_REFINERY]->(refinery:Refinery)
        RETURN d.name AS deposit_name,
               d.geological_context AS geological_context,
               collect(DISTINCT {
                   name: formation.name,
                   lithology: formation.lithology,
                   confidence: coalesce(formation.confidence, 1.0)
               }) AS host_rocks,
               collect(DISTINCT {
                   name: mineral.name,
                   purity_ppm: contains.purity_ppm,
                   confidence: coalesce(mineral.confidence, 1.0)
               }) AS minerals,
               collect(DISTINCT {
                   name: refinery.name,
                   route: supplies.route,
                   confidence: coalesce(refinery.confidence, 1.0)
               }) AS refinery_paths,
               coalesce(d.survey_excerpts, []) AS survey_excerpts
        """
        with self.driver.session() as session:
            result = session.run(query, deposit_name=deposit_name)
            record = next(iter(result), None)
        if record is None:
            return {
                "deposit_name": deposit_name,
                "geological_context": None,
                "host_rocks": [],
                "minerals": [],
                "refinery_paths": [],
                "survey_excerpts": [],
            }
        data = record.data() if hasattr(record, "data") else dict(record)
        excerpts = data.get("survey_excerpts", []) or []
        data["survey_excerpts"] = [
            excerpt if isinstance(excerpt, dict) else {"text": str(excerpt)}
            for excerpt in excerpts
        ]
        data["survey_synthesis"] = " ".join(
            str(excerpt.get("text", "")).strip()
            for excerpt in data["survey_excerpts"]
            if excerpt.get("text")
        )
        return data