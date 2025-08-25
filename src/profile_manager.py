import json
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import hashlib
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass
from abc import ABC, abstractmethod

ProfileType = Literal['google_drive', 'scraper_bank', 'profit_loss']

@dataclass
class ProfileSchema:
    """Base schema for profile validation"""
    required_fields: List[str]
    optional_fields: List[str] = None
    secure_fields: List[str] = None  # Fields that should be encrypted
    
    def __post_init__(self):
        if self.optional_fields is None:
            self.optional_fields = []
        if self.secure_fields is None:
            self.secure_fields = []

class ProfileTypeHandler(ABC):
    """Abstract base class for profile type handlers"""
    
    @abstractmethod
    def get_schema(self) -> ProfileSchema:
        """Return the schema for this profile type"""
        pass
    
    @abstractmethod
    def validate_profile_data(self, data: Dict) -> bool:
        """Validate profile data against schema"""
        pass
    
    def transform_for_storage(self, data: Dict) -> Dict:
        """Transform data before storage (override if needed)"""
        return data
    
    def transform_from_storage(self, data: Dict) -> Dict:
        """Transform data after loading (override if needed)"""
        return data

class GoogleDriveProfileHandler(ProfileTypeHandler):
    """Handler for Google Drive profiles"""
    
    def get_schema(self) -> ProfileSchema:
        return ProfileSchema(
            required_fields=['gdrive_root', 'gdrive_target'],
            optional_fields=['gdrive_api_id', 'gdrive_api_secret'],
            secure_fields=['gdrive_api_id', 'gdrive_api_secret']
        )
    
    def validate_profile_data(self, data: Dict) -> bool:
        schema = self.get_schema()
        # Check required fields
        for field in schema.required_fields:
            if field not in data or not data[field]:
                return False
        return True

class ScraperBankProfileHandler(ProfileTypeHandler):
    """Handler for Scraper Bank profiles"""
    
    def get_schema(self) -> ProfileSchema:
        return ProfileSchema(
            required_fields=['bank_name', 'username_template_path', 'password_template_path'],
            optional_fields=['submit_template_path', 'account_configs', 'custom_selectors'],
            secure_fields=['username_template_path', 'password_template_path']
        )
    
    def validate_profile_data(self, data: Dict) -> bool:
        schema = self.get_schema()
        for field in schema.required_fields:
            if field not in data or not data[field]:
                return False
        return True

class ProfitLossProfileHandler(ProfileTypeHandler):
    """Handler for Profit Loss profiles"""
    
    def get_schema(self) -> ProfileSchema:
        return ProfileSchema(
            required_fields=['spreadsheet_template', 'output_format'],
            optional_fields=['column_mappings', 'calculation_rules', 'chart_configs'],
            secure_fields=[]
        )
    
    def validate_profile_data(self, data: Dict) -> bool:
        schema = self.get_schema()
        for field in schema.required_fields:
            if field not in data or not data[field]:
                return False
        return True

class UniversalProfileManager:
    def __init__(self, profiles_dir: str = None):
        if profiles_dir is None:
            # Get the project root directory and set profiles path
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            profiles_dir = os.path.join(current_dir, "src", "google_profiles")
        self.profiles_dir = profiles_dir
        self.profiles_file = os.path.join(profiles_dir, "profiles.enc")
        
        # Create profiles directory if it doesn't exist
        os.makedirs(profiles_dir, exist_ok=True)
        
        # Generate or load encryption key
        self._encryption_key = self._get_or_create_key()
        
        # Initialize profile type handlers
        self._handlers: Dict[ProfileType, ProfileTypeHandler] = {
            'google_drive': GoogleDriveProfileHandler(),
            'scraper_bank': ScraperBankProfileHandler(),
            'profit_loss': ProfitLossProfileHandler()
        }
        
    def _get_or_create_key(self) -> bytes:
        """Generate or retrieve encryption key based on machine-specific data"""
        # Use machine-specific data for key derivation
        machine_id = self._get_machine_id()
        
        # Create a deterministic key from machine ID
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'profile_salt_2024',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
        return key
    
    def _get_machine_id(self) -> str:
        """Get a machine-specific identifier"""
        # Combine multiple machine-specific attributes
        import platform
        machine_data = f"{platform.node()}-{platform.system()}-{os.getenv('USERNAME', 'default')}"
        return hashlib.sha256(machine_data.encode()).hexdigest()
    
    def _encrypt_data(self, data: str) -> bytes:
        """Encrypt data using Fernet encryption"""
        fernet = Fernet(self._encryption_key)
        return fernet.encrypt(data.encode())
    
    def _decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypt data using Fernet encryption"""
        fernet = Fernet(self._encryption_key)
        return fernet.decrypt(encrypted_data).decode()
    
    def load_profiles(self) -> Dict[ProfileType, Dict[str, Dict]]:
        """Load all profiles from encrypted file, organized by type"""
        if not os.path.exists(self.profiles_file):
            return {'google_drive': {}, 'scraper_bank': {}, 'profit_loss': {}}
        
        try:
            with open(self.profiles_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self._decrypt_data(encrypted_data)
            profiles = json.loads(decrypted_data)
            
            # Ensure all profile types exist
            for profile_type in ['google_drive', 'scraper_bank', 'profit_loss']:
                if profile_type not in profiles:
                    profiles[profile_type] = {}
            
            return profiles
        except Exception as e:
            print(f"Error loading profiles: {e}")
            return {'google_drive': {}, 'scraper_bank': {}, 'profit_loss': {}}
    
    def save_profiles(self, profiles: Dict[ProfileType, Dict[str, Dict]]) -> bool:
        """Save all profiles to encrypted file"""
        try:
            json_data = json.dumps(profiles, indent=2)
            encrypted_data = self._encrypt_data(json_data)
            
            with open(self.profiles_file, 'wb') as f:
                f.write(encrypted_data)
            
            return True
        except Exception as e:
            print(f"Error saving profiles: {e}")
            return False
    
    def get_profile_names(self, profile_type: ProfileType) -> List[str]:
        """Get list of profile names for a specific type"""
        profiles = self.load_profiles()
        return list(profiles.get(profile_type, {}).keys())
    
    def get_profile(self, profile_type: ProfileType, profile_name: str) -> Optional[Dict]:
        """Get a specific profile by type and name"""
        profiles = self.load_profiles()
        type_profiles = profiles.get(profile_type, {})
        profile_data = type_profiles.get(profile_name)
        
        if profile_data and profile_type in self._handlers:
            # Transform data from storage format if needed
            return self._handlers[profile_type].transform_from_storage(profile_data)
        return profile_data
    
    def save_profile(self, profile_type: ProfileType, profile_name: str, profile_data: Dict) -> bool:
        """Save a single profile of a specific type"""
        # Validate profile data
        if profile_type in self._handlers:
            handler = self._handlers[profile_type]
            if not handler.validate_profile_data(profile_data):
                print(f"Profile validation failed for type {profile_type}")
                return False
            # Transform data for storage if needed
            profile_data = handler.transform_for_storage(profile_data)
        
        profiles = self.load_profiles()
        if profile_type not in profiles:
            profiles[profile_type] = {}
        
        profiles[profile_type][profile_name] = profile_data
        return self.save_profiles(profiles)
    
    def delete_profile(self, profile_type: ProfileType, profile_name: str) -> bool:
        """Delete a profile of a specific type"""
        profiles = self.load_profiles()
        type_profiles = profiles.get(profile_type, {})
        if profile_name in type_profiles:
            del type_profiles[profile_name]
            profiles[profile_type] = type_profiles
            return self.save_profiles(profiles)
        return False
    
    def profile_exists(self, profile_type: ProfileType, profile_name: str) -> bool:
        """Check if a profile exists for a specific type"""
        profiles = self.load_profiles()
        type_profiles = profiles.get(profile_type, {})
        return profile_name in type_profiles
    
    def get_profile_schema(self, profile_type: ProfileType) -> Optional[ProfileSchema]:
        """Get the schema for a specific profile type"""
        if profile_type in self._handlers:
            return self._handlers[profile_type].get_schema()
        return None
    
    def get_all_profiles_by_type(self, profile_type: ProfileType) -> Dict[str, Dict]:
        """Get all profiles of a specific type"""
        profiles = self.load_profiles()
        return profiles.get(profile_type, {})

# Legacy alias for backwards compatibility and convenience classes
ProfileManager = UniversalProfileManager

class GoogleDriveProfileManager:
    """Convenience class for Google Drive profiles only"""
    def __init__(self, profiles_dir: str = "src/profiles"):
        self._manager = UniversalProfileManager(profiles_dir)
        self._profile_type: ProfileType = 'google_drive'
    
    def get_profile_names(self) -> List[str]:
        return self._manager.get_profile_names(self._profile_type)
    
    def get_profile(self, profile_name: str) -> Optional[Dict]:
        return self._manager.get_profile(self._profile_type, profile_name)
    
    def save_profile(self, profile_name: str, profile_data: Dict) -> bool:
        return self._manager.save_profile(self._profile_type, profile_name, profile_data)
    
    def delete_profile(self, profile_name: str) -> bool:
        return self._manager.delete_profile(self._profile_type, profile_name)
    
    def profile_exists(self, profile_name: str) -> bool:
        return self._manager.profile_exists(self._profile_type, profile_name)
    
    def get_schema(self) -> Optional[ProfileSchema]:
        return self._manager.get_profile_schema(self._profile_type)

class ScraperBankProfileManager:
    """Convenience class for Scraper Bank profiles only"""
    def __init__(self, profiles_dir: str = "src/profiles"):
        self._manager = UniversalProfileManager(profiles_dir)
        self._profile_type: ProfileType = 'scraper_bank'
    
    def get_profile_names(self) -> List[str]:
        return self._manager.get_profile_names(self._profile_type)
    
    def get_profile(self, profile_name: str) -> Optional[Dict]:
        return self._manager.get_profile(self._profile_type, profile_name)
    
    def save_profile(self, profile_name: str, profile_data: Dict) -> bool:
        return self._manager.save_profile(self._profile_type, profile_name, profile_data)
    
    def delete_profile(self, profile_name: str) -> bool:
        return self._manager.delete_profile(self._profile_type, profile_name)
    
    def profile_exists(self, profile_name: str) -> bool:
        return self._manager.profile_exists(self._profile_type, profile_name)
    
    def get_schema(self) -> Optional[ProfileSchema]:
        return self._manager.get_profile_schema(self._profile_type)

class ProfitLossProfileManager:
    """Convenience class for Profit Loss profiles only"""
    def __init__(self, profiles_dir: str = "src/profiles"):
        self._manager = UniversalProfileManager(profiles_dir)
        self._profile_type: ProfileType = 'profit_loss'
    
    def get_profile_names(self) -> List[str]:
        return self._manager.get_profile_names(self._profile_type)
    
    def get_profile(self, profile_name: str) -> Optional[Dict]:
        return self._manager.get_profile(self._profile_type, profile_name)
    
    def save_profile(self, profile_name: str, profile_data: Dict) -> bool:
        return self._manager.save_profile(self._profile_type, profile_name, profile_data)
    
    def delete_profile(self, profile_name: str) -> bool:
        return self._manager.delete_profile(self._profile_type, profile_name)
    
    def profile_exists(self, profile_name: str) -> bool:
        return self._manager.profile_exists(self._profile_type, profile_name)
    
    def get_schema(self) -> Optional[ProfileSchema]:
        return self._manager.get_profile_schema(self._profile_type)