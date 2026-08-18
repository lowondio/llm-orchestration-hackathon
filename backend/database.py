from sqlalchemy import create_engine, Column, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json

Base = declarative_base()

class GraphModel(Base):
    __tablename__ = 'graphs'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, default='')
    config = Column(Text, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'config': json.loads(self.config)
        }

engine = create_engine('sqlite:///agents.db', echo=False)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Compatibility layer for old code
class DatabaseWrapper:
    def save_graph(self, graph_id: str, graph_data: dict):
        """Save graph data (compatibility method)"""
        db = SessionLocal()
        try:
            existing = db.query(GraphModel).filter_by(id=graph_id).first()
            if existing:
                existing.config = json.dumps(graph_data)
            else:
                graph = GraphModel(
                    id=graph_id,
                    name=graph_data.get('name', 'Deployed Agent'),
                    description='',
                    config=json.dumps(graph_data)
                )
                db.add(graph)
            db.commit()
            return True
        except Exception as e:
            print(f"Error saving graph: {e}")
            return False
        finally:
            db.close()

    def get_graph(self, graph_id: str):
        """Get graph data (compatibility method)"""
        db = SessionLocal()
        try:
            graph = db.query(GraphModel).filter_by(id=graph_id).first()
            if graph:
                return json.loads(graph.config)
            return None
        except Exception as e:
            print(f"Error getting graph: {e}")
            return None
        finally:
            db.close()

db = DatabaseWrapper()
