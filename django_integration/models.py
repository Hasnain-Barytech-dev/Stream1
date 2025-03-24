"""
Models for integration with the Django backend.
These models represent entities synced from the Django backend.
"""

from typing import List , Dict, Any
import uuid
from datetime import datetime


class DjangoBaseModel:
    """
    Base class for all Django integration models.
    """
    
    def __init__(self, data: Dict[str, Any]):
        """
        Initialize a model with data from the Django backend.
        
        Args:
            data: Data retrieved from Django API
        """
        for key, value in data.items():
            setattr(self, key, value)
        
        if not hasattr(self, 'id') and 'id' in data:
            self.id = data['id']


class DjangoUser(DjangoBaseModel):
    """
    User model from Django backend.
    """
    
    id: str
    uuid: str
    username: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    profile_picture: str = None
    created_at: datetime = None
    

class DjangoCompany(DjangoBaseModel):
    """
    Company model from Django backend.
    """
    
    id: str
    name: str
    customer_id: str
    status: str
    created_at: datetime = None
    company_industry: str = None
    maximum_users: int = 0
    maximum_extended_users: int = 0


class DjangoCompanyUser(DjangoBaseModel):
    """
    Company User relationship model from Django backend.
    """
    
    id: str
    user: Dict[str, Any]
    company: Dict[str, Any]
    is_active: bool
    suspended: bool
    roles: List[Dict[str, Any]]
    total_storage: int = None
    is_extended_user: bool = False


class DjangoDepartment(DjangoBaseModel):
    """
    Department model from Django backend.
    """
    
    id: str
    name: str
    company: Dict[str, Any]
    is_default_department: bool
    created_at: datetime = None


class DjangoResource(DjangoBaseModel):
    """
    Resource model from Django backend.
    """
    
    id: str
    title: str
    resource_type: str
    file: str = None
    thumbnail: str = None
    size: int = 0
    duration: float = None
    width: int = None
    height: int = None
    status: str = "pending"
    playback_url: str = None
    company_user: Dict[str, Any]
    created_at: datetime = None