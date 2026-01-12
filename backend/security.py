from qdrant_client import models
from .models import User

def build_qdrant_security_filter(user: User) -> models.Filter:
    must = [
        models.FieldCondition(
            key="tenant_id",
            match=models.MatchValue(value=user.tenant_id),
        ),
        models.FieldCondition(
            key="roles_allowed",
            match=models.MatchAny(any=[user.role]),
        ),
    ]

    must_not = []
    if user.role != "admin":
        must_not.append(
            models.FieldCondition(
                key="sensitive",
                match=models.MatchValue(value=True),
            )
        )

    return models.Filter(must=must, must_not=must_not)