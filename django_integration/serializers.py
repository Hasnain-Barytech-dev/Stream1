"""
Serializers for Django integration models.
These serializers convert between Django models and Python dictionaries.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from .models import DjangoUser, DjangoCompany, DjangoCompanyUser, DjangoDepartment, DjangoResource


class DjangoUserSerializer:
    """Serializer for DjangoUser model."""
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> DjangoUser:
        """
        Create a DjangoUser from a dictionary.
        
        Args:
            data: Dictionary containing user data
            
        Returns:
            DjangoUser instance
        """
        return DjangoUser(data)
    
    @staticmethod
    def to_dict(user: DjangoUser) -> Dict[str, Any]:
        """
        Convert a DjangoUser to a dictionary.
        
        Args:
            user: DjangoUser instance
            
        Returns:
            Dictionary representation of the user
        """
        return {
            'id': user.id,
            'uuid': user.uuid,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'profile_picture': user.profile_picture,
            'created_at': user.created_at.isoformat() if user.created_at else None
        }


class DjangoCompanySerializer:
    """Serializer for DjangoCompany model."""
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> DjangoCompany:
        """
        Create a DjangoCompany from a dictionary.
        
        Args:
            data: Dictionary containing company data
            
        Returns:
            DjangoCompany instance
        """
        return DjangoCompany(data)
    
    @staticmethod
    def to_dict(company: DjangoCompany) -> Dict[str, Any]:
        """
        Convert a DjangoCompany to a dictionary.
        
        Args:
            company: DjangoCompany instance
            
        Returns:
            Dictionary representation of the company
        """
        return {
            'id': company.id,
            'name': company.name,
            'customer_id': company.customer_id,
            'status': company.status,
            'company_industry': company.company_industry,
            'maximum_users': company.maximum_users,
            'maximum_extended_users': company.maximum_extended_users,
            'created_at': company.created_at.isoformat() if company.created_at else None
        }


class DjangoCompanyUserSerializer:
    """Serializer for DjangoCompanyUser model."""
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> DjangoCompanyUser:
        """
        Create a DjangoCompanyUser from a dictionary.
        
        Args:
            data: Dictionary containing company user data
            
        Returns:
            DjangoCompanyUser instance
        """
        return DjangoCompanyUser(data)
    
    @staticmethod
    def to_dict(company_user: DjangoCompanyUser) -> Dict[str, Any]:
        """
        Convert a DjangoCompanyUser to a dictionary.
        
        Args:
            company_user: DjangoCompanyUser instance
            
        Returns:
            Dictionary representation of the company user
        """
        return {
            'id': company_user.id,
            'user': company_user.user,
            'company': company_user.company,
            'is_active': company_user.is_active,
            'suspended': company_user.suspended,
            'roles': company_user.roles,
            'total_storage': company_user.total_storage,
            'is_extended_user': company_user.is_extended_user
        }


class DjangoDepartmentSerializer:
    """Serializer for DjangoDepartment model."""
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> DjangoDepartment:
        """
        Create a DjangoDepartment from a dictionary.
        
        Args:
            data: Dictionary containing department data
            
        Returns:
            DjangoDepartment instance
        """
        return DjangoDepartment(data)
    
    @staticmethod
    def to_dict(department: DjangoDepartment) -> Dict[str, Any]:
        """
        Convert a DjangoDepartment to a dictionary.
        
        Args:
            department: DjangoDepartment instance
            
        Returns:
            Dictionary representation of the department
        """
        return {
            'id': department.id,
            'name': department.name,
            'company': department.company,
            'is_default_department': department.is_default_department,
            'created_at': department.created_at.isoformat() if department.created_at else None
        }


class DjangoResourceSerializer:
    """Serializer for DjangoResource model."""
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> DjangoResource:
        """
        Create a DjangoResource from a dictionary.
        
        Args:
            data: Dictionary containing resource data
            
        Returns:
            DjangoResource instance
        """
        return DjangoResource(data)
    
    @staticmethod
    def to_dict(resource: DjangoResource) -> Dict[str, Any]:
        """
        Convert a DjangoResource to a dictionary.
        
        Args:
            resource: DjangoResource instance
            
        Returns:
            Dictionary representation of the resource
        """
        return {
            'id': resource.id,
            'title': resource.title,
            'resource_type': resource.resource_type,
            'file': resource.file,
            'thumbnail': resource.thumbnail,
            'size': resource.size,
            'duration': resource.duration,
            'width': resource.width,
            'height': resource.height,
            'status': resource.status,
            'playback_url': resource.playback_url,
            'company_user': resource.company_user,
            'created_at': resource.created_at.isoformat() if resource.created_at else None
        }