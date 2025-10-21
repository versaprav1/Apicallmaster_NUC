"""
Neo4j graph store for WHINT Graph RAG.

Requires environment variables:
  - NEO4J_URI
  - NEO4J_USER
  - NEO4J_PASSWORD

Usage:
    store = Neo4jGraphStore()
    store.ensure_constraints()
    store.bulk_upsert(records)
    nodes = store.k_hop_neighborhood(seed_names=["SAP NetWeaver"], max_hops=2)
    paths = store.shortest_paths("Sender A", "Receiver B", limit=3)
"""

from typing import Any, Dict, List, Optional
import os
from .neo4j_wrapper import create_driver, test_connection, NEO4J_AVAILABLE

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use system environment variables


class Neo4jGraphStore:
    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None, database: str = "neo4j"):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "pass")
        self.database = database
        if not NEO4J_AVAILABLE:
            raise ImportError("Neo4j driver not available. Please install neo4j package.")
        self.driver = create_driver(self.uri, auth=(self.user, self.password))

    def close(self):
        try:
            self.driver.close()
        except Exception:
            pass

    def run_tx(self, cypher: str, **params):
        with self.driver.session(database=self.database) as session:
            return session.run(cypher, **params).data()

    def ensure_constraints(self):
        statements = [
            "CREATE CONSTRAINT interface_id IF NOT EXISTS FOR (n:Interface) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT system_id IF NOT EXISTS FOR (n:System) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT datasource_id IF NOT EXISTS FOR (n:Datasource) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT type_id IF NOT EXISTS FOR (n:Type) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT tag_id IF NOT EXISTS FOR (n:Tag) REQUIRE n.tag_id IS UNIQUE",
            "CREATE CONSTRAINT property_type_id IF NOT EXISTS FOR (n:PropertyType) REQUIRE n.type_id IS UNIQUE",
            "CREATE CONSTRAINT metadata_key_name IF NOT EXISTS FOR (n:MetadataKey) REQUIRE n.name IS UNIQUE",
        ]
        for stmt in statements:
            self.run_tx(stmt)

    def upsert_interface_record(self, rec: Dict[str, Any]):
        """Upsert a single interface/inventory record with its relationships.

        Expected structure (best-effort):
          {
            "id": str|int, "name": str, "type": str|int, "description": str,
            "sender": {"id": ..., "name": ...},
            "receiver": {"id": ..., "name": ...},
            "data_source": {"id": ..., "name": ..., "type": ..., "category": ...},
            "properties": [{"type_id": ..., "value": ..., "type": {"name": ..., "kind": ...}}],
            "tags": [{"tag_id": ..., "value": ..., "tag": {"name": ...}}],
            "metadata": [{"name": ..., "value": ...}]
          }
        """
        # Skip records that have neither id nor name for Interface
        iface_id = rec.get("id")
        iface_name = rec.get("name")
        if iface_id is None and (not isinstance(iface_name, str) or not iface_name.strip()):
            # Nothing stable to merge on; skip
            return
        cypher = """
        // Create Interface node by id or name (simple approach)
        WITH $i AS ii, $sender AS sender, $receiver AS receiver, $ds AS ds, $tags AS tags, $properties AS properties, $metadata AS metadata
        FOREACH (_ IN CASE WHEN ii.id IS NOT NULL THEN [1] ELSE [] END |
            MERGE (i:Interface {id: toString(ii.id)})
            SET i.name = coalesce(ii.name, i.name),
                i.type = coalesce(ii.type, i.type),
                i.description = coalesce(ii.description, i.description)
        )
        FOREACH (_ IN CASE WHEN ii.id IS NULL AND ii.name IS NOT NULL THEN [1] ELSE [] END |
            MERGE (i:Interface {name: ii.name})
            SET i.type = coalesce(ii.type, i.type),
                i.description = coalesce(ii.description, i.description)
        )
        WITH ii, sender, receiver, ds, tags, properties, metadata
        MATCH (i:Interface)
        WHERE (ii.id IS NOT NULL AND i.id = toString(ii.id)) OR (ii.id IS NULL AND ii.name IS NOT NULL AND i.name = ii.name)
        WITH i, sender, receiver, ds, tags, properties, metadata

        // Sender system by id or name
        FOREACH (_ IN CASE WHEN sender IS NOT NULL AND sender.id IS NOT NULL THEN [1] ELSE [] END |
            MERGE (s:System {id: toString(sender.id)})
            SET s.name = coalesce(sender.name, s.name)
            MERGE (i)-[:SENT_BY]->(s)
        )
        FOREACH (_ IN CASE WHEN sender IS NOT NULL AND sender.id IS NULL AND sender.name IS NOT NULL THEN [1] ELSE [] END |
            MERGE (s:System {name: sender.name})
            MERGE (i)-[:SENT_BY]->(s)
        )

        // Receiver system by id or name
        FOREACH (_ IN CASE WHEN receiver IS NOT NULL AND receiver.id IS NOT NULL THEN [1] ELSE [] END |
            MERGE (r:System {id: toString(receiver.id)})
            SET r.name = coalesce(receiver.name, r.name)
            MERGE (i)-[:RECEIVED_BY]->(r)
        )
        FOREACH (_ IN CASE WHEN receiver IS NOT NULL AND receiver.id IS NULL AND receiver.name IS NOT NULL THEN [1] ELSE [] END |
            MERGE (r:System {name: receiver.name})
            MERGE (i)-[:RECEIVED_BY]->(r)
        )

        // Datasource by id or name
        FOREACH (_ IN CASE WHEN ds IS NOT NULL AND ds.id IS NOT NULL THEN [1] ELSE [] END |
            MERGE (d:Datasource {id: toString(ds.id)})
            SET d.name = coalesce(ds.name, d.name), d.type = coalesce(ds.type, d.type), d.category = coalesce(ds.category, d.category)
            MERGE (i)-[:USES_DATASOURCE]->(d)
        )
        FOREACH (_ IN CASE WHEN ds IS NOT NULL AND ds.id IS NULL AND ds.name IS NOT NULL THEN [1] ELSE [] END |
            MERGE (d:Datasource {name: ds.name})
            SET d.type = coalesce(ds.type, d.type), d.category = coalesce(ds.category, d.category)
            MERGE (i)-[:USES_DATASOURCE]->(d)
        )

        // Tags by tag_id or name
        WITH i, tags, properties, metadata
        UNWIND coalesce(tags, []) AS tag
        FOREACH (_ IN CASE WHEN tag.tag_id IS NOT NULL THEN [1] ELSE [] END |
            MERGE (tg:Tag {tag_id: toString(tag.tag_id)})
            SET tg.name = coalesce(tag.tag.name, tg.name)
            MERGE (i)-[:HAS_TAG]->(tg)
        )
        FOREACH (_ IN CASE WHEN tag.tag_id IS NULL AND tag.tag.name IS NOT NULL THEN [1] ELSE [] END |
            MERGE (tg:Tag {name: tag.tag.name})
            MERGE (i)-[:HAS_TAG]->(tg)
        )

        // PropertyType by type_id or type.name
        WITH i, properties, metadata
        UNWIND coalesce(properties, []) AS p
        // When type_id present
        FOREACH (_ IN CASE WHEN p.type_id IS NOT NULL AND p.value IS NOT NULL THEN [1] ELSE [] END |
            MERGE (pt:PropertyType {type_id: toString(p.type_id)})
            SET pt.name = coalesce(p.type.name, pt.name), pt.kind = coalesce(p.type.kind, pt.kind)
            MERGE (i)-[:HAS_PROPERTY {value: p.value}]->(pt)
        )
        FOREACH (_ IN CASE WHEN p.type_id IS NOT NULL AND p.value IS NULL THEN [1] ELSE [] END |
            MERGE (pt:PropertyType {type_id: toString(p.type_id)})
            SET pt.name = coalesce(p.type.name, pt.name), pt.kind = coalesce(p.type.kind, pt.kind)
            MERGE (i)-[:HAS_PROPERTY]->(pt)
        )
        // When only type.name present
        FOREACH (_ IN CASE WHEN p.type_id IS NULL AND p.type.name IS NOT NULL AND p.value IS NOT NULL THEN [1] ELSE [] END |
            MERGE (pt:PropertyType {name: p.type.name})
            SET pt.kind = coalesce(p.type.kind, pt.kind)
            MERGE (i)-[:HAS_PROPERTY {value: p.value}]->(pt)
        )
        FOREACH (_ IN CASE WHEN p.type_id IS NULL AND p.type.name IS NOT NULL AND p.value IS NULL THEN [1] ELSE [] END |
            MERGE (pt:PropertyType {name: p.type.name})
            SET pt.kind = coalesce(p.type.kind, pt.kind)
            MERGE (i)-[:HAS_PROPERTY]->(pt)
        )

        // Metadata by key name
        WITH i, metadata
        UNWIND coalesce(metadata, []) AS m
        // When value present
        FOREACH (_ IN CASE WHEN m.name IS NOT NULL AND m.value IS NOT NULL THEN [1] ELSE [] END |
            MERGE (mk:MetadataKey {name: toString(m.name)})
            MERGE (i)-[:HAS_METADATA {value: m.value}]->(mk)
        )
        // When value missing, create relationship without property
        FOREACH (_ IN CASE WHEN m.name IS NOT NULL AND m.value IS NULL THEN [1] ELSE [] END |
            MERGE (mk:MetadataKey {name: toString(m.name)})
            MERGE (i)-[:HAS_METADATA]->(mk)
        )
        """

        params = {
            "i": {"id": iface_id, "name": iface_name, "type": rec.get("type"), "description": rec.get("description")},
            "sender": rec.get("sender"),
            "receiver": rec.get("receiver"),
            "ds": rec.get("data_source") or rec.get("dataSource") or rec.get("datasource"),
            "properties": rec.get("properties"),
            "tags": rec.get("tags"),
            "metadata": rec.get("metadata"),
        }
        self.run_tx(cypher, **params)

    def bulk_upsert(self, records: List[Dict[str, Any]], batch_size: int = 200):
        success = 0
        errors = 0
        for i in range(0, len(records), batch_size):
            for rec in records[i:i+batch_size]:
                try:
                    self.upsert_interface_record(rec)
                    success += 1
                except Exception as e:
                    # Best-effort ingest; continue on errors
                    errors += 1
                    name = rec.get("name")
                    print(f"Neo4j upsert error: {e} | interface name={name}")
        # summary
        print(f"Neo4j upsert summary: success={success}, errors={errors}")

    def k_hop_neighborhood(self, seed_names: List[str], max_hops: int = 2, limit: int = 200):
        """
        Find nodes within k-hops of seed nodes using standard Cypher (no APOC required).
        This searches for interfaces and systems connected to the seed systems.
        """
        cypher = """
        UNWIND $seeds AS seed
        MATCH (s)
        WHERE s.name = seed OR toLower(s.name) = toLower(seed)
        
        // Find all interfaces connected to this system (sender or receiver)
        OPTIONAL MATCH (i:Interface)-[:SENT_BY]->(s)
        WITH s, collect(DISTINCT i) as sent_interfaces
        
        OPTIONAL MATCH (i2:Interface)-[:RECEIVED_BY]->(s)
        WITH s, sent_interfaces, collect(DISTINCT i2) as received_interfaces
        
        // Combine all interfaces
        WITH s, sent_interfaces + received_interfaces as all_interfaces
        UNWIND all_interfaces as interface
        
        // Get related systems for these interfaces
        OPTIONAL MATCH (interface)-[:SENT_BY]->(sender:System)
        OPTIONAL MATCH (interface)-[:RECEIVED_BY]->(receiver:System)
        
        // Return all related nodes
        WITH interface, sender, receiver
        WHERE interface IS NOT NULL
        
        RETURN DISTINCT 
            labels(interface) AS labels, 
            interface as node,
            sender.name as sender_name,
            receiver.name as receiver_name
        LIMIT $limit
        """
        return self.run_tx(cypher, seeds=seed_names, k=max_hops, limit=limit)

    def shortest_paths(self, sender_name: str, receiver_name: str, limit: int = 5):
        cypher = """
        MATCH (s:System {name: $sender}), (r:System {name: $receiver})
        // Use a direct two-hop pattern through Interface instead of shortestPath
        MATCH p = (s)<-[:SENT_BY]-(:Interface)-[:RECEIVED_BY]->(r)
        RETURN p
        LIMIT $limit
        """
        return self.run_tx(cypher, sender=sender_name, receiver=receiver_name, limit=limit)


