"""
Modelos de base de datos SQLAlchemy
"""
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid


Base = declarative_base()


def generate_uuid():
    """Genera un UUID como string"""
    return str(uuid.uuid4())


class ClientModel(Base):
    """Modelo de cliente en base de datos"""
    __tablename__ = "clients"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    tech_profile = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    def __repr__(self):
        return f"<Client(id={self.id}, name={self.name})>"


class CloudCredentialsModel(Base):
    """Modelo de credenciales de cloud"""
    __tablename__ = "cloud_credentials"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    client_id = Column(String, nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    credentials = Column(JSON, nullable=False)  # Encriptado en producción
    region = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class RepositoryCredentialsModel(Base):
    """Modelo de credenciales de repositorios"""
    __tablename__ = "repository_credentials"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    client_id = Column(String, nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    credentials = Column(JSON, nullable=False)  # Encriptado en producción
    organization = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class DeploymentHistoryModel(Base):
    """Histórico de despliegues"""
    __tablename__ = "deployment_history"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    client_id = Column(String, nullable=False, index=True)
    cloud_provider = Column(String(50), nullable=False)
    region = Column(String(50), nullable=False)
    environment = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)  # pending, running, completed, failed
    deployment_data = Column(JSON, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class ArchitectureGenerationModel(Base):
    """Histórico de generación de arquitecturas"""
    __tablename__ = "architecture_generation"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    client_id = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    requirements = Column(JSON, nullable=True)
    architecture = Column(JSON, nullable=False)
    infrastructure_code = Column(Text, nullable=True)
    estimated_cost = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
