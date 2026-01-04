from typing import List, Dict, Any

class LayerManager:
    @staticmethod
    def resolve_layers(roles: List[str]) -> List[Dict[str, Any]]:
        """
        Resolve Keycloak roles to Knowledge Layers.
        
        Args:
            roles: List of roles from Keycloak JWT (realm_access.roles)
            
        Returns:
            List of layer objects dicts with metadata
        """
        # TODO: Replace with actual Postgres query
        # For now, we map roles to mock layers for Phase 5-1 verification
        
        valid_layers = []
        
        # Always include public system layer
        valid_layers.append({
            "id": "layer_system_public",
            "name": "System Public",
            "type": "SYSTEM",
            "color": "slate",
            "permissions": ["READ"]
        })
        
        # Engineering Layer
        if "group:engineering" in roles or "admin" in roles:
            valid_layers.append({
                "id": "layer_engineering",
                "name": "Engineering",
                "type": "ORG",
                "color": "blue",
                "permissions": ["READ", "WRITE"]
            })
            
        # HR Layer
        if "group:hr" in roles or "admin" in roles:
            valid_layers.append({
                "id": "layer_hr",
                "name": "Human Resources",
                "type": "ORG",
                "color": "rose",
                "permissions": ["READ", "WRITE"]
            })
            
        # User Private Layer (Assume one per user, but here just generic for demo)
        valid_layers.append({
            "id": "layer_user_private",
            "name": "My Workspace",
            "type": "USER",
            "color": "emerald",
            "permissions": ["READ", "WRITE"]
        })

        return valid_layers
